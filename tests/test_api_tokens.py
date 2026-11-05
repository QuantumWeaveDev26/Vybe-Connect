import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store
import api_tokens as tokens


class APITokenTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.s=Store(Path(self.tmp.name)/'api.db')
        self.session=self.s.setup('Owner','api-owner@example.test','a-long-enough-password','API workspace')['token']
        self.ctx=self.s.auth(self.session)
        self.contact=self.s.action(self.ctx,'contact.save',{'name':'Contact','phone':'919000000001','optin':True})['id']
    def key(self,scopes=None):return tokens.create(self.s,self.ctx,{'name':'CRM','days':30,'scopes':scopes or ['contacts:read']})
    def read(self,key,path='/api/v1/contacts',query=None,workspace=None):return tokens.read(self.s,'Bearer '+key['token'],path,query or {},workspace)
    def test_show_once_hash_only_and_no_secret_in_state(self):
        k=self.key();self.assertEqual(self.read(k)['data'][0]['id'],self.contact)
        self.assertTrue(self.read(k)['data'][0]['optin'])
        self.assertNotIn(k['token'],json.dumps(tokens.listing(self.s,self.ctx)))
        self.assertNotIn(k['token'],json.dumps(self.s.state(self.ctx)))
        self.assertNotIn(k['token'].encode(),self.s.path.read_bytes())
        with self.s.db() as db:self.assertEqual(db.execute('SELECT token_hash FROM api_tokens').fetchone()[0],hashlib.sha256(k['token'].encode()).hexdigest())
    def test_cookie_session_is_not_a_bearer_token(self):
        with self.assertRaises(tokens.APIError) as e:tokens.authenticate(self.s,'Bearer '+self.session,'contacts:read')
        self.assertEqual(e.exception.code,401)
    def test_wrong_secret_expiry_and_revocation(self):
        k=self.key();bad=dict(k,token=k['token'][:-1]+('A' if k['token'][-1]!='A' else 'B'))
        with self.assertRaises(tokens.APIError):self.read(bad)
        tokens.revoke(self.s,self.ctx,{'id':k['id']})
        with self.assertRaises(tokens.APIError):self.read(k)
        k=self.key()
        with patch.object(tokens.time,'time',return_value=k['expires']):
            with self.assertRaises(tokens.APIError):self.read(k)
    def test_scope_cannot_escalate_to_other_resource_or_workspace(self):
        k=self.key()
        with self.assertRaises(tokens.APIError) as e:self.read(k,'/api/v1/messages')
        self.assertEqual(e.exception.code,403)
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'];ctx2=self.s.auth(self.session,other)
        self.s.action(ctx2,'contact.save',{'name':'Hidden','phone':'919000000002'})
        self.assertEqual(len(self.read(k)['data']),1)
        for query,header in [({'workspace':[other]},None),({},other)]:
            with self.assertRaises(tokens.APIError):self.read(k,query=query,workspace=header)
        with self.assertRaises(tokens.APIError):tokens.revoke(self.s,ctx2,{'id':k['id']})
    def test_pagination_and_validation(self):
        self.s.action(self.ctx,'contact.save',{'name':'Second','phone':'919000000002'})
        k=self.key();first=self.read(k,query={'limit':['1']})
        second=self.read(k,query={'limit':['1'],'after':[first['next_after']]})
        self.assertNotEqual(first['data'][0]['id'],second['data'][0]['id']);self.assertIsNone(second['next_after'])
        for q in [{'limit':['101']},{'after':['-1']},{'after':['9'*20]},{'limit':['1','2']}]:
            with self.assertRaises(tokens.APIError):self.read(k,query=q)
    def test_messages_exclude_notes_drafts_and_other_workspaces(self):
        with self.s.db() as db:
            for i,direction,status in [('in','in','received'),('draft','out','draft'),('note','note','internal'),('sent','out','sent')]:
                self.s._message(db,self.ctx['tenant_id'],self.contact,i,direction,status)
        k=self.key(['messages:read']);rows=self.read(k,'/api/v1/messages')['data']
        self.assertEqual({r['body'] for r in rows},{'in','sent'})
        self.assertEqual(len(self.read(k,'/api/v1/messages',{'contact_id':['0'*16]})['data']),0)
    def test_analytics_uses_recorded_report_and_validates_dates(self):
        k=self.key(['analytics:read'])
        r=self.read(k,'/api/v1/analytics',{'from':['2026-11-01'],'to':['2026-11-05']})
        self.assertEqual(r['totals']['inbound'],0)
        with self.assertRaises(Exception):self.read(k,'/api/v1/analytics',{'from':['bad'],'to':['2026-11-05']})
    def test_rate_budget_persists_and_resets_next_minute(self):
        k=self.key();stamp=int(time.time())
        with patch.object(tokens.time,'time',return_value=stamp):
            for _ in range(60):self.read(k)
            with self.assertRaises(tokens.APIError) as e:self.read(k)
            self.assertEqual(e.exception.code,429)
        with patch.object(tokens.time,'time',return_value=stamp+60):self.read(k)
    def test_password_change_permanently_revokes_keys(self):
        k=self.key();self.s.change_password(self.ctx,'a-long-enough-password','another-long-password')
        with self.assertRaises(tokens.APIError):self.read(k)
    def test_demote_and_repromote_does_not_revive_key(self):
        k=self.key()
        with self.s.db() as db:
            user=self.s._new_user(db,'Second admin','second-admin@example.test','a-long-enough-password')
            db.execute('INSERT INTO members VALUES(?,?,?)',(self.ctx['tenant_id'],user,'admin'))
        token=self.s.login('second-admin@example.test','a-long-enough-password')['token'];other=self.s.auth(token,self.ctx['tenant_id'])
        self.s.action(other,'member.role',{'id':self.ctx['user']['id'],'role':'agent'})
        self.s.action(other,'member.role',{'id':self.ctx['user']['id'],'role':'admin'})
        with self.assertRaises(tokens.APIError):self.read(k)
    def test_invalid_creation_and_stale_admin_session(self):
        for d in [{'name':'','days':30,'scopes':['contacts:read']},{'name':'x','days':True,'scopes':['contacts:read']},{'name':'x','days':30,'scopes':['messages:send']},{'name':'x','days':30,'scopes':['contacts:read']*2}]:
            with self.assertRaises(tokens.APIError):tokens.create(self.s,self.ctx,d)
        self.s.logout(self.session)
        with self.assertRaises(tokens.APIError):self.key()

    def test_mfa_enrollment_revokes_existing_token(self):
        from account_mfa import totp
        k=self.key();stamp=int(time.time())
        with patch('account_mfa.time.time',return_value=stamp):
            setup=self.s.account_mfa(self.ctx,'begin',{'current_password':'a-long-enough-password'})
            self.s.account_mfa(self.ctx,'confirm',{'current_password':'a-long-enough-password','code':totp(setup['secret'],stamp)})
        with self.assertRaises(tokens.APIError):self.read(k)
