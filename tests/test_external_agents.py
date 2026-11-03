import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class ExternalAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'agents.db')
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.agent=self.s.action(self.ctx,'external-agent.save',{'name':'My agent','url':'https://agents.example.test/inbound','events':['message.received','message.status'],'enabled':True})
        self.prefix='TW_WEBHOOK_'+self.ctx['tenant_id'].upper()+'_'
        self.env=patch.dict(os.environ,{self.prefix+'ENABLED':'true',self.prefix+'ALLOWED_ORIGINS':'https://agents.example.test',self.prefix+self.agent['id'].upper()+'_SECRET':'local-test-secret'});self.env.start()
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def inbound(self,id='in_1'):return self.s.inbound(self.ctx['tenant_id'],{'id':id,'from':'919000000001','text':{'body':'What are your hours?'},'timestamp':str(int(time.time()))})
    def callback(self,event,reply_id='reply_1',body='Our hours are 9–5.'):
        payload=json.dumps({'event_id':event['id'],'reply_id':reply_id,'body':body}).encode();stamp=str(int(time.time()));signature='sha256='+hmac.new(b'local-test-secret',stamp.encode()+b'.'+payload,hashlib.sha256).hexdigest()
        return self.s.external_agent_callback(self.ctx['tenant_id'],self.agent['id'],payload,{'X-TeamWave-Timestamp':stamp,'X-TeamWave-Signature':signature})

    def test_inbound_outbox_is_deduplicated_and_not_created_while_disabled(self):
        self.inbound();self.inbound();events=self.s.state(self.ctx)['webhook_events'];self.assertEqual(len(events),1)
        with patch.dict(os.environ,{self.prefix+'ENABLED':'false'}):self.inbound('in_disabled')
        self.assertEqual(len(self.s.state(self.ctx)['webhook_events']),1)

    def test_worker_signs_payload_and_records_only_real_http_result(self):
        self.inbound()
        with patch('external_agents.send_webhook',return_value=204) as transport:self.assertTrue(self.s.process_webhook_once())
        url,raw,headers=transport.call_args.args;payload=json.loads(raw)
        expected='sha256='+hmac.new(b'local-test-secret',headers['X-TeamWave-Timestamp'].encode()+b'.'+raw,hashlib.sha256).hexdigest()
        self.assertEqual(headers['X-TeamWave-Signature'],expected);self.assertEqual(payload['type'],'message.received')
        self.assertEqual(self.s.state(self.ctx)['webhook_events'][0]['status'],'delivered')
        self.assertNotIn('local-test-secret',json.dumps(self.s.state(self.ctx)))

    def test_uncertain_delivery_is_not_retried_automatically(self):
        self.inbound()
        with patch('external_agents.send_webhook',side_effect=TimeoutError('secret request body')) as transport:self.s.process_webhook_once();self.s.process_webhook_once();self.assertEqual(transport.call_count,1)
        event=self.s.state(self.ctx)['webhook_events'][0];self.assertEqual(event['status'],'unknown');self.assertNotIn('secret request body',json.dumps(event))
        self.s.action(self.ctx,'external-agent.retry',{'id':event['id']})
        with patch('external_agents.send_webhook',return_value=200) as transport:self.s.process_webhook_once()
        self.assertEqual(json.loads(transport.call_args.args[1])['id'],event['id'])

    def test_callback_creates_one_unsent_draft_and_rejects_changed_replay(self):
        self.inbound();event=self.s.state(self.ctx)['webhook_events'][0]
        first=self.callback(event);again=self.callback(event);self.assertEqual(first['message_id'],again['message_id'])
        messages=self.s.state(self.ctx)['messages'];self.assertEqual(len(messages),2);self.assertEqual(messages[-1]['status'],'draft')
        with self.assertRaises(Problem):self.callback(event,body='Changed reply')

    def test_callback_rejects_old_signature_and_cross_workspace_event(self):
        self.inbound();event=self.s.state(self.ctx)['webhook_events'][0]
        with self.assertRaises(Problem):self.s.external_agent_callback(self.ctx['tenant_id'],self.agent['id'],b'{}',{'X-TeamWave-Timestamp':'1','X-TeamWave-Signature':'sha256=bad'})
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        self.assertFalse(self.s.state(other)['external_agents']);self.assertFalse(self.s.state(other)['webhook_events'])
        with self.assertRaises(Problem):self.s.action(other,'external-agent.retry',{'id':event['id']})

    def test_endpoint_rejects_local_addresses_and_credentials(self):
        from external_agents import send_webhook
        for url in ['http://example.test','https://user:pass@example.test/hook','https://127.0.0.1/hook','https://example.test:444/hook','https://example.test/hook?secret=value']:
            with self.subTest(url=url),self.assertRaises(ValueError):send_webhook(url,b'{}',{})
        with patch('external_agents.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]),patch('external_agents.socket.create_connection') as connect:
            with self.assertRaises(ValueError):send_webhook('https://example.test/hook',b'{}',{})
            connect.assert_not_called()

    def test_removed_subscription_cancels_pending_delivery(self):
        self.inbound();self.s.action(self.ctx,'external-agent.save',dict(self.agent,events=['message.status']))
        with patch('external_agents.send_webhook') as transport:self.assertFalse(self.s.process_webhook_once());transport.assert_not_called()
        self.assertEqual(self.s.state(self.ctx)['webhook_events'][0]['status'],'cancelled')

    def test_url_change_cancels_queued_event_and_rejects_old_callbacks(self):
        self.inbound();event=self.s.state(self.ctx)['webhook_events'][0]
        self.s.action(self.ctx,'external-agent.save',dict(self.agent,url='https://agents.example.test/new'))
        self.assertEqual(self.s.state(self.ctx)['webhook_events'][0]['status'],'cancelled')
        with self.assertRaises(Problem):self.callback(event)

    def test_human_takeover_prevents_callback_drafts(self):
        self.inbound();event=self.s.state(self.ctx)['webhook_events'][0];contact=self.s.state(self.ctx)['contacts'][0]
        self.s.action(self.ctx,'chat.takeover',{'id':contact['id']})
        with self.assertRaises(Problem):self.callback(event)
        self.inbound('in_human');self.assertEqual(len(self.s.state(self.ctx)['webhook_events']),1)

    def test_status_events_are_deduplicated_and_ignore_unknown_provider_ids(self):
        self.inbound();contact=self.s.state(self.ctx)['contacts'][0]
        with self.s.db() as db:self.s._message(db,self.ctx['tenant_id'],contact['id'],'Reply','out','accepted','wamid_test')
        self.s.delivery(self.ctx['tenant_id'],'wamid_test','delivered');self.s.delivery(self.ctx['tenant_id'],'wamid_test','delivered');self.s.delivery(self.ctx['tenant_id'],'missing','read')
        events=self.s.state(self.ctx)['webhook_events'];self.assertEqual(sum(e['type']=='message.status' for e in events),1)

    def test_tls_transport_pins_public_dns_and_does_not_follow_redirect(self):
        from external_agents import send_webhook
        with patch('external_agents.socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]),patch('external_agents.PinnedConnection') as connection:
            connection.return_value.getresponse.return_value.status=302
            self.assertEqual(send_webhook('https://example.test/hook',b'{}',{}),302)
            connection.assert_called_once_with('example.test','8.8.8.8');connection.return_value.request.assert_called_once()

    def test_agent_role_cannot_modify_connections(self):
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'another-long-password','role':'agent'})
        agent=self.s.auth(self.s.login('agent@example.test','another-long-password')['token'])
        with self.assertRaises(Problem):self.s.action(agent,'external-agent.save',dict(self.agent,enabled=False))
