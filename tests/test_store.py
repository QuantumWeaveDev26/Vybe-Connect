import csv
import io
import os
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store, Problem
from meta import signature_ok


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sandbox=patch.dict(os.environ,{'TW_SANDBOX':'true'});self.sandbox.start()
        self.path = Path(self.tmp.name) / 'workspace.db'
        self.s = Store(self.path)
        self.token = self.s.setup('Owner', 'owner@example.test', 'a-long-test-password', 'Acme')['token']
        self.ctx = self.s.auth(self.token)

    def tearDown(self):
        self.sandbox.stop()
        self.tmp.cleanup()

    def act(self, action, **data):
        return self.s.action(self.ctx, action, data)

    def contact(self, **kw):
        return self.act('contact.save', name='Asha', phone='+91 90000 00001', **kw)

    def test_password_authentication_and_session_revocation(self):
        with self.assertRaises(Problem): self.s.login('owner@example.test', 'wrong-password')
        token = self.s.login('owner@example.test', 'a-long-test-password')['token']
        self.assertEqual(self.s.auth(token)['tenant_id'], self.ctx['tenant_id'])
        self.s.logout(token)
        with self.assertRaises(Problem): self.s.auth(token)
        with self.assertRaises(Problem): self.s.setup('Bad', 'bad@example.test', 'abcdefghijk', 'Other')

    def test_tenant_isolation_including_guessed_record_ids(self):
        contact = self.contact()
        w = self.act('workspace.create', name='Second business')
        other = self.s.auth(self.token, w['id'])
        self.assertEqual(self.s.state(other)['contacts'], [])
        with self.assertRaises(Problem): self.s.action(other, 'message.send', {'contact_id':contact['id'],'body':'Leak'})
        with self.assertRaises(Problem): self.s.auth(self.token, 'not-a-member')

    def test_agent_cannot_change_team_or_automation(self):
        self.act('member.add', name='Agent', email='agent@example.test', password='agent-long-password', role='agent')
        agent = self.s.auth(self.s.login('agent@example.test','agent-long-password')['token'])
        with self.assertRaises(Problem): self.s.action(agent,'rule.save',{'keyword':'Hi','reply':'Hi'})
        self.s.action(agent,'contact.save',{'name':'Client','phone':'919000000002'})

    def test_csv_quotes_and_invalid_and_duplicate_numbers(self):
        result=self.act('contacts.import',csv='name,phone,tags,optin\n"Asha, Rao",919000000001,"Lead,VIP",true\nAgain,919000000001,,true\nBad,invalid,,true\n')
        self.assertEqual(result['imported'],1)
        self.assertEqual(len(result['errors']),2)
        self.assertEqual(self.s.state(self.ctx)['contacts'][0]['name'],'Asha, Rao')

    def test_campaign_requires_template_and_consent(self):
        self.contact(optin=True)
        self.act('contact.save',name='No consent',phone='919000000002',optin=False)
        t=self.act('template.save',name='hello_world',body='Hi {{name}}',language='en',category='UTILITY')
        c=self.act('campaign.save',name='Welcome',template_id=t['id'],tag='')
        result=self.act('campaign.run',id=c['id'])
        self.assertEqual(result['audience'],1)
        self.assertEqual(result['status'],'demo_complete')
        self.assertEqual(self.s.state(self.ctx)['messages'][0]['status'],'simulated')
        with self.assertRaises(Problem): self.act('campaign.run',id=c['id'])

    def test_stop_optout_excludes_future_campaign(self):
        c=self.contact(optin=True)
        self.s.inbound(self.ctx['tenant_id'],{'id':'stop1','from':c['phone'],'text':{'body':'STOP'},'timestamp':str(int(time.time()))})
        self.assertFalse(self.s.state(self.ctx)['contacts'][0]['optin'])

    def test_duplicate_webhook_does_not_duplicate_keyword_draft(self):
        self.act('rule.save',name='Greeting',keyword='hello',reply='Welcome',enabled=True)
        e={'id':'wamid.test','from':'919000000001','text':{'body':'hello'},'timestamp':str(int(time.time()))}
        self.s.inbound(self.ctx['tenant_id'],e)
        self.s.inbound(self.ctx['tenant_id'],e)
        m=self.s.state(self.ctx)['messages']
        self.assertEqual(len(m),2)
        self.assertEqual(m[-1]['status'],'draft')

    def test_window_blocks_live_send_before_provider_call(self):
        c=self.contact()
        with patch('store.send_text',side_effect=AssertionError('Network must not run')):
            with self.assertRaisesRegex(Problem,'24-hour'):
                self.act('message.send',contact_id=c['id'],body='Hello',live=True)

    def test_notes_and_chat_assignment_survive_restart(self):
        c=self.contact()
        self.act('chat.update',id=c['id'],status='pending',assignee=self.ctx['user']['id'])
        self.act('message.send',contact_id=c['id'],body='Internal note',note=True)
        state=Store(self.path).state(self.ctx)
        self.assertEqual(state['contacts'][0]['status'],'pending')
        self.assertEqual(state['messages'][0]['direction'],'note')

    def test_flow_creates_keyword_draft_without_external_execution(self):
        self.act('flow.save',name='Support',keyword='help',reply='Our team will help.',enabled=True)
        self.s.inbound(self.ctx['tenant_id'],{'id':'flow1','from':'919000000001','text':{'body':'help'},'timestamp':str(int(time.time()))})
        self.assertEqual(self.s.state(self.ctx)['messages'][-1]['body'],'Our team will help.')

    def test_csv_export_neutralizes_spreadsheet_formulas(self):
        self.act('contact.save',name='=1+1',phone='919000000001')
        rows=list(csv.reader(io.StringIO(self.s.export_contacts(self.ctx))))
        self.assertEqual(rows[1][0],"'=1+1")

    def test_signature_rejects_missing_secret(self):
        import hmac,hashlib
        raw=b'{"entry":[]}'
        signature='sha256='+hmac.new(b'abc',raw,hashlib.sha256).hexdigest()
        self.assertTrue(signature_ok(raw,signature,'abc'))
        self.assertFalse(signature_ok(raw,signature,''))
        self.assertFalse(signature_ok(raw+b' ',signature,'abc'))

    def test_graph_question_resumes_and_branches_on_saved_answer(self):
        graph={'start':'ask','nodes':[
            {'id':'ask','type':'question','text':'Which service?','variable':'service','next':'check'},
            {'id':'check','type':'condition','field':'service','value':'design','yes':'tag','no':'other'},
            {'id':'tag','type':'tag','tag':'Design lead','next':'answer'},
            {'id':'answer','type':'message','text':'We can help with {{service}}.','next':'human'},
            {'id':'other','type':'message','text':'Our team will contact you.','next':'human'},
            {'id':'human','type':'handoff'}]}
        self.act('flow.save',name='Services',keyword='services',reply='Hello',enabled=True,graph=graph)
        for id,text in [('g1','services'),('g2','design')]:
            self.s.inbound(self.ctx['tenant_id'],{'id':id,'from':'919000000001','text':{'body':text},'timestamp':str(int(time.time()))})
        state=self.s.state(self.ctx)
        self.assertEqual(state['contacts'][0]['attributes']['service'],'design')
        self.assertIn('Design lead',state['contacts'][0]['tags'])
        self.assertEqual(state['contacts'][0]['status'],'pending')
        self.assertIn('We can help with design.',[m['body'] for m in state['messages']])

    def test_flow_rejects_cycles_and_missing_target_nodes(self):
        for graph in [{'start':'a','nodes':[{'id':'a','type':'message','text':'Loop','next':'a'}]}, {'start':'a','nodes':[{'id':'a','type':'message','text':'Broken','next':'absent'}]}]:
            with self.assertRaises(Problem): self.act('flow.save',name='Bad',keyword='hello',reply='Hi',graph=graph)

    def test_template_rejects_unsafe_button_url(self):
        with self.assertRaises(Problem):self.act('template.save',name='bad_button',body='Hello',language='en',category='MARKETING',buttons=[{'type':'URL','text':'Visit','url':'javascript:alert(1)'}])

    def test_template_rich_fields_persist(self):
        template=self.act('template.save',name='rich',body='Hello',header='Welcome',footer='Reply STOP',buttons=[{'type':'QUICK_REPLY','text':'More'}],language='en',category='UTILITY')
        self.assertEqual(template['header'],'Welcome')
        self.assertEqual(self.s.state(self.ctx)['templates'][0]['buttons'][0]['text'],'More')


if __name__=='__main__': unittest.main()
