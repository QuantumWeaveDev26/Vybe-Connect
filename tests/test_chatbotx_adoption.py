import base64
import hashlib
import json
import os
import tempfile
import time
import unittest
from datetime import datetime,date,timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
from zoneinfo import ZoneInfo
from store import Store,Problem
import business_hours as hours
import google_connections as google
import semantic_knowledge as semantic
import embedded_signup as vault
import reply_tracking
from knowledge_documents import retrieve


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.env=patch.dict(os.environ,{'TW_DATA_DIR':self.tmp.name,'TW_GOOGLE_ENABLED':'true','TW_GOOGLE_CLIENT_ID':'test.apps.googleusercontent.com','TW_GOOGLE_CLIENT_SECRET':'private-client-secret','TW_PUBLIC_ORIGIN':'https://example.test','TW_CREDENTIAL_KEYS':json.dumps({'test':base64.b64encode(b'a'*32).decode()}),'TW_CREDENTIAL_ACTIVE_KEY':'test'})
        self.env.start();self.addCleanup(self.env.stop)
        self.s=Store(Path(self.tmp.name)/'test.db');token=self.s.setup('Owner','owner@adoption.test','long-test-password','Business')['token'];self.ctx=self.s.auth(token);self.t=self.ctx['tenant_id']
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'});self.other=self.s.auth(token,other['id'])
        self.contact=self.s.action(self.ctx,'contact.save',{'name':'Customer','phone':'919000000001','optin':True})
        self.network=patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('No live provider requests in tests'));self.network.start();self.addCleanup(self.network.stop)

    def connected(self,kind='google_sheets'):
        vault.write_credentials(self.t,{'refresh_token':'private-refresh','access_token':'private-access','expires':int(time.time())+3600,'email':'owner@example.test','account':'account-id','generation':'connection-generation'},kind)

    def test_hours_weekend_holidays_and_end_exclusive(self):
        schedule=hours.validate({'enabled':True,'timezone':'Asia/Kolkata','response_minutes':60,'intervals':[{'weekday':d,'start':540,'end':1020} for d in range(1,6)],'overrides':{'2026-11-09':[]}})
        start=datetime(2026,11,6,16,30,tzinfo=ZoneInfo('Asia/Kolkata')).timestamp();due=hours.deadline(schedule,start,3600)
        self.assertEqual(datetime.fromtimestamp(due,ZoneInfo('Asia/Kolkata')).isoformat(),'2026-11-10T09:30:00+05:30')
        self.assertEqual(hours.seconds_between(schedule,start,due),3600)
        self.assertEqual(hours.seconds_between(schedule,due,due),0)
        with self.assertRaises(Problem):hours.validate(dict(schedule,intervals=[{'weekday':1,'start':500,'end':600},{'weekday':1,'start':599,'end':700}]))

    def test_dst_ambiguous_and_nonexistent_wall_minutes(self):
        zone=ZoneInfo('America/New_York')
        self.assertEqual(datetime.fromtimestamp(hours.wall_instant(date(2026,11,1),90,zone),timezone.utc).isoformat(),'2026-11-01T05:30:00+00:00')
        self.assertEqual(datetime.fromtimestamp(hours.wall_instant(date(2026,3,8),150,zone),timezone.utc).isoformat(),'2026-03-08T07:00:00+00:00')

    def test_sla_real_inbound_accepted_reply_and_snapshot(self):
        config={'enabled':True,'timezone':'UTC','response_minutes':60,'intervals':[{'weekday':d,'start':0,'end':1440} for d in range(7)],'overrides':{}}
        self.s.action(self.ctx,'growth.hours.save',config)
        event={'id':'incoming-real','from':self.contact['phone'],'type':'text','text':{'body':'Help'},'timestamp':int(time.time())-120}
        self.s.inbound(self.t,dict(event,id='simulation'),True);self.assertEqual(self.s.state(self.ctx)['business_hours']['waiting'],[])
        self.s.inbound(self.t,event,False);state=self.s.state(self.ctx)['business_hours'];self.assertEqual(len(state['waiting']),1)
        self.s.action(self.ctx,'growth.hours.save',dict(config,response_minutes=10))
        with self.s.db() as db:
            self.s._message(db,self.t,self.contact['id'],'Draft','out','draft')
            c=self.s._get(db,self.t,'contact',self.contact['id']);self.s._put(db,self.t,'contact',dict(c,automation_hold=True),c['id'])
            self.s._message(db,self.t,self.contact['id'],'Real accepted response','out','accepted')
        state=self.s.state(self.ctx)['business_hours'];self.assertEqual(state['answered'],1);self.assertEqual(state['met'],1);self.assertEqual(state['history'][0]['schedule']['response_minutes'],60)
        self.assertEqual(self.s.state(self.other)['business_hours']['history'],[])

    def test_google_missing_setup_and_oauth_state_cookie_replay(self):
        with patch.dict(os.environ,{'TW_GOOGLE_ENABLED':'false'}):
            with self.assertRaises(Problem):google.start(self.s,self.ctx,'google_sheets')
        started=google.start(self.s,self.ctx,'google_sheets');q=parse_qs(urlsplit(started['authorize_url']).query);cookie=started['_flow_cookie'].split('=',1)[1].split(';')[0]
        self.assertIn('code_challenge',q);self.assertIn('SameSite=Lax',started['_flow_cookie']);self.assertIn('Secure',started['_flow_cookie'])
        with self.assertRaises(Problem):google.callback(self.s,{'state':q['state'],'code':['code']},'wrong-cookie')
        def provider(url,*args,**kwargs):
            if url.endswith('/token'):return {'access_token':'access','refresh_token':'refresh','expires_in':3600,'scope':' '.join(google.SCOPES['google_sheets'])}
            return {'sub':'stable-account','email':'owner@example.test','email_verified':True}
        with patch.object(google,'request',side_effect=provider):self.assertTrue(google.callback(self.s,{'state':q['state'],'code':['code']},cookie)['connected'])
        with self.assertRaises(Problem):google.callback(self.s,{'state':q['state'],'code':['code']},cookie)
        raw=vault.credential_path(self.t,'google_sheets').read_text();self.assertNotIn('refresh',raw);self.assertNotIn('stable-account',raw)
        state=json.dumps(self.s.state(self.ctx));self.assertNotIn('private-client-secret',state);self.assertNotIn('refresh_token',state)

    def test_google_sheet_import_atomic_consent_and_duplicate_preservation(self):
        self.connected();data={'kind':'google_sheets','spreadsheet_id':'spreadsheet','range':'A1:C201','import':True,'confirm':True}
        with patch.object(google,'request',return_value={'values':[['name','phone'],['New','919000000002'],['Changed',self.contact['phone']],['Duplicate','919000000002']]}):
            result=self.s.action(self.ctx,'google.sheet.read',data)
        self.assertEqual(result,{'created':1,'skipped':2});contacts=self.s.state(self.ctx)['contacts'];self.assertTrue(next(c for c in contacts if c['id']==self.contact['id'])['optin']);self.assertFalse(next(c for c in contacts if c['phone']=='919000000002')['optin'])
        with patch.object(google,'request',return_value={'values':[['name','phone'],['Would import','919000000004'],['Invalid','not-phone']]}),self.assertRaises(Problem):self.s.action(self.ctx,'google.sheet.read',data)
        self.assertEqual(len(self.s.state(self.ctx)['contacts']),2)

    def test_uncertain_sheet_append_does_not_resend_and_cross_tenant_contact_blocked(self):
        self.connected();data={'kind':'google_sheets','spreadsheet_id':'spreadsheet','range':'A:C','contact_id':self.contact['id'],'nonce':'unique-append-12345','confirm':True}
        with patch.object(google,'request',side_effect=Problem('Timeout',502)) as mock:
            with self.assertRaises(Problem):self.s.action(self.ctx,'google.sheet.append',data)
            result=self.s.action(self.ctx,'google.sheet.append',data);self.assertEqual(result['status'],'unknown');self.assertEqual(mock.call_count,1)
        self.assertEqual(self.s.state(self.other)['google_connections']['jobs'],[])

    def test_calendar_booking_overlap_and_reconciliation(self):
        self.connected('google_calendar');a=datetime.fromtimestamp(time.time()+3600,timezone.utc).isoformat();b=datetime.fromtimestamp(time.time()+7200,timezone.utc).isoformat()
        data={'kind':'google_calendar','calendar_id':'primary','start':a,'end':b,'contact_id':self.contact['id'],'nonce':'unique-booking-12345','confirm':True}
        def provider(url,token='',data=None,**kwargs):
            if 'freeBusy' in url:return {'calendars':{'primary':{'busy':[]}}}
            return {'id':data['id']}
        with patch.object(google,'request',side_effect=provider) as mock:
            job=self.s.action(self.ctx,'google.calendar.create',data);self.assertEqual(job['status'],'confirmed')
            self.assertEqual(self.s.action(self.ctx,'google.calendar.create',data)['id'],job['id'])
            with self.assertRaises(Problem):self.s.action(self.ctx,'google.calendar.create',dict(data,nonce='different-booking-12345'))
            self.assertEqual(sum('/events?' in c.args[0] for c in mock.call_args_list),1)
        with patch.object(google,'request',return_value={'id':'b'+job['identity']}):self.assertEqual(self.s.action(self.ctx,'google.calendar.reconcile',{'kind':'google_calendar','id':job['id']})['status'],'confirmed')

    def document(self):return self.s.upload_knowledge_document(self.ctx,'refunds.txt',b'Refunds can be requested within fourteen days.')

    def test_semantic_gates_no_implicit_calls_and_disabled_source_isolation(self):
        d=self.document()
        with patch.object(semantic,'embed',side_effect=AssertionError('No paid call')):
            self.s.state(self.ctx)
            with self.s.db() as db:self.assertTrue(retrieve(self.s,db,self.t,'refunds'))
            self.assertFalse(semantic.prepare_query(self.s,self.t,'refunds'))
        with patch.object(semantic,'allowed',return_value=True):
            with self.assertRaises(Problem):self.s.action(self.ctx,'semantic.configure',{'enabled':True})
            self.s.action(self.ctx,'semantic.configure',{'enabled':True,'confirm_paid':True})
            vector=[1.0]+[0.0]*255
            with patch.object(semantic,'embed',return_value=[vector]) as mock:
                self.s.action(self.ctx,'semantic.index',{'document_id':d['id'],'confirm_paid':True});semantic.prepare_query(self.s,self.t,'money back',self.ctx)
                semantic.prepare_query(self.s,self.t,'money back',self.ctx);self.assertEqual(mock.call_count,2)
            with self.s.db() as db:
                self.assertEqual(retrieve(self.s,db,self.t,'money back')[0]['document_id'],d['id'])
                self.assertEqual(retrieve(self.s,db,self.t,'money back',[]),[])
                self.assertEqual(retrieve(self.s,db,self.other['tenant_id'],'money back'),[])
                self.s._put(db,self.t,'knowledgedocument',dict(d,enabled=False),d['id'])
            with self.s.db() as db:self.assertEqual(retrieve(self.s,db,self.t,'money back'),[])
        self.assertNotIn('vector',json.dumps(self.s.state(self.ctx)))

    def test_stale_document_cannot_save_vectors_after_network(self):
        d=self.document();vector=[1.0]+[0.0]*255
        with patch.object(semantic,'allowed',return_value=True):
            self.s.action(self.ctx,'semantic.configure',{'enabled':True,'confirm_paid':True})
            def stale(*args):
                with self.s.db() as db:self.s._put(db,self.t,'knowledgedocument',dict(d,digest='new-digest'),d['id'])
                return [vector]
            with patch.object(semantic,'embed',side_effect=stale),self.assertRaises(Problem):self.s.action(self.ctx,'semantic.index',{'document_id':d['id'],'confirm_paid':True})
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM knowledge_vectors').fetchone()[0],0)


if __name__=='__main__':unittest.main()
