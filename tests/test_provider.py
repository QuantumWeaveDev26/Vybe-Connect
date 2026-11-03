import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'provider.db')
        token=self.s.setup('Owner','owner@example.test','long-enough-password','Real business')['token'];self.ctx=self.s.auth(token);self.t=self.ctx['tenant_id']
        self.prefix='TW_META_'+self.t.upper()+'_'
        self.env=patch.dict(os.environ,{self.prefix+'TOKEN':'test-only-not-a-real-token',self.prefix+'PHONE_ID':'123',self.prefix+'WABA_ID':'456',self.prefix+'VERSION':'v99.0',self.prefix+'LIVE':'false'})
        self.env.start()

    def tearDown(self): self.env.stop();self.tmp.cleanup()
    def act(self,a,**d): return self.s.action(self.ctx,a,d)

    def test_sync_records_provider_status_without_local_approval(self):
        with patch('store.list_templates',return_value={'data':[{'id':'t123','name':'welcome','language':'en','category':'UTILITY','status':'APPROVED','components':[{'type':'BODY','text':'Hi {{1}}'}]}]}):
            self.act('templates.sync')
        t=self.s.state(self.ctx)['templates'][0]
        self.assertEqual(t['status'],'APPROVED');self.assertEqual(t['meta_id'],'t123')

    def test_launch_requires_provider_approval_and_live_gate(self):
        c=self.act('contact.save',name='Client',phone='919000000001',optin=True)
        t=self.act('template.save',name='welcome',body='Hello',language='en',category='UTILITY')
        campaign=self.act('campaign.save',name='Campaign',template_id=t['id'])
        with self.assertRaisesRegex(Problem,'Meta-approved'):self.act('campaign.launch',id=campaign['id'])

    def test_durable_queue_rechecks_consent_and_records_provider_ids(self):
        with patch('store.list_templates',return_value={'data':[{'id':'t123','name':'welcome','language':'en','status':'APPROVED','category':'UTILITY','components':[{'type':'BODY','text':'Hello'}]}]}): self.act('templates.sync')
        t=self.s.state(self.ctx)['templates'][0]
        c=self.act('contact.save',name='Client',phone='919000000001',optin=True)
        campaign=self.act('campaign.save',name='Campaign',template_id=t['id'])
        with patch.dict(os.environ,{self.prefix+'LIVE':'true'}):
            self.act('campaign.launch',id=campaign['id'])
            with patch('store.send_template',return_value='wamid.accepted'):
                self.s.process_queue_once()
        state=self.s.state(self.ctx)
        self.assertEqual(state['messages'][0]['status'],'accepted')
        self.assertEqual(state['messages'][0]['external_id'],'wamid.accepted')
        self.assertEqual(state['contacts'][0]['outgoing_watch']['message_id'],state['messages'][0]['id'])
        self.assertEqual(state['campaigns'][0]['status'],'submitted')

    def test_uncertain_send_is_never_automatically_retried(self):
        with patch('store.list_templates',return_value={'data':[{'id':'t1','name':'hello','language':'en','status':'APPROVED','category':'UTILITY','components':[{'type':'BODY','text':'Hello'}]}]}):self.act('templates.sync')
        t=self.s.state(self.ctx)['templates'][0];self.act('contact.save',name='A',phone='919000000001',optin=True)
        c=self.act('campaign.save',name='C',template_id=t['id'])
        with patch.dict(os.environ,{self.prefix+'LIVE':'true'}):
            self.act('campaign.launch',id=c['id'])
            with patch('store.send_template',side_effect=TimeoutError('uncertain')) as provider:
                self.s.process_queue_once();self.s.process_queue_once();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.s.state(self.ctx)['queue'][0]['status'],'unknown')

    def test_optout_after_launch_is_rechecked_before_send(self):
        with patch('store.list_templates',return_value={'data':[{'id':'t1','name':'hello','language':'en','status':'APPROVED','category':'UTILITY','components':[{'type':'BODY','text':'Hello'}]}]}):self.act('templates.sync')
        t=self.s.state(self.ctx)['templates'][0];contact=self.act('contact.save',name='A',phone='919000000001',optin=True)
        c=self.act('campaign.save',name='C',template_id=t['id'])
        with patch.dict(os.environ,{self.prefix+'LIVE':'true'}):
            self.act('campaign.launch',id=c['id'])
            self.act('contact.save',id=contact['id'],name='A',phone='919000000001',optin=False)
            with patch('store.send_template',side_effect=AssertionError('Must not send after opt-out')):self.s.process_queue_once()
        self.assertEqual(self.s.state(self.ctx)['queue'][0]['status'],'skipped')


if __name__=='__main__':unittest.main()
