import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai
import api_tokens
from store import Store, Problem


class ServiceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name)/'test.db')
        setup = self.store.setup('Owner','owner@example.test','test-strong-password-123','QA')
        self.ctx = self.store.auth(setup['token'])
        self.tenant = self.ctx['tenant_id']

    def test_widget_cannot_impersonate_whatsapp_contact_or_grant_consent(self):
        contact = self.store.action(self.ctx,'contact.save',{'name':'Real customer','phone':'12025550123','optin':False})
        with self.store.db() as db:
            self.store._message(db,self.tenant,contact['id'],'Private WhatsApp history','in','received')
        a = self.store.widget_message(self.tenant,{'name':'Visitor','phone':'12025550123','message':'Hello'})
        b = self.store.widget_message(self.tenant,{'name':'Other visitor','phone':'12025550123','message':'Other'})
        self.assertNotEqual(a['contact_id'],contact['id'])
        self.assertNotEqual(a['contact_id'],b['contact_id'])
        self.assertNotIn('Private WhatsApp history',str(a))
        with self.assertRaises(Problem):self.store.widget_history(self.tenant,contact['id'],a['visitor_token'])
        with self.assertRaises(Problem):self.store.widget_history(self.tenant,a['contact_id'])
        with self.assertRaises(Problem):self.store.widget_message('',{'message':'Hello'})
        self.store.action(self.ctx,'message.send',{'contact_id':a['contact_id'],'body':'Real website response','live':True})
        history=self.store.widget_history(self.tenant,a['contact_id'],a['visitor_token'])
        self.assertEqual([m['body'] for m in history['messages']],['Hello','Real website response'])
        with self.store.db() as db:
            c=self.store._get(db,self.tenant,'contact',a['contact_id'])
        self.assertFalse(c['optin'])
        self.assertEqual(c['phone'],'')

    def test_read_only_token_cannot_send(self):
        token=api_tokens.create(self.store,self.ctx,{'name':'Read only','days':7,'scopes':['messages:read']})['token']
        with self.assertRaises(api_tokens.APIError) as caught:
            api_tokens.authenticate(self.store,'Bearer '+token,'messages:write')
        self.assertEqual(caught.exception.code,403)

    def test_api_send_uses_real_window_and_does_not_create_fake_contacts(self):
        with self.assertRaises(Problem):self.store.api_send_message(self.ctx,{'phone':'12025550123','body':'hello'})
        c=self.store.action(self.ctx,'contact.save',{'name':'Test','phone':'12025550123'})
        with self.assertRaises(Problem):self.store.api_send_message(self.ctx,{'phone':c['phone'],'body':'hello'})
        self.assertEqual(self.store.state(self.ctx)['messages'],[])

    def test_production_solve_does_not_simulate_survey_delivery(self):
        c=self.store.action(self.ctx,'contact.save',{'name':'Test','phone':'12025550123'})
        with patch.dict(os.environ,{'TW_SANDBOX':'false'}):
            self.store.action(self.ctx,'chat.update',{'id':c['id'],'status':'solved'})
        self.assertEqual(self.store.state(self.ctx)['messages'],[])

    def test_production_rejects_simulator_actions(self):
        with patch.dict(os.environ,{'TW_SANDBOX':'false'}):
            for action in ['sandbox.simulate_inbound','sandbox.simulate_status']:
                with self.subTest(action=action), self.assertRaises(Problem):
                    self.store.action(self.ctx,action,{'phone':'12025550123','message':'Test','status':'read'})

    def test_ollama_failure_does_not_fall_back_to_canned_reply(self):
        with patch.dict(os.environ,{'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'ollama','TW_AI_MODEL':'test-local','TW_AI_ALLOWED_MODELS':'test-local','TW_PLATFORM_AI_MANAGED':'false'}):
            with patch('ai.urllib.request.urlopen',side_effect=TimeoutError):
                with self.assertRaisesRegex(ValueError,'No response was generated'):
                    ai.ask_local('Hello',{},[])

    def test_builtin_cannot_masquerade_as_customer_model(self):
        with patch.dict(os.environ,{'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'builtin','TW_PLATFORM_AI_MANAGED':'false'}):
            self.assertIn('no language model',ai.ai_status()['provider'])
            with self.assertRaises(ValueError):ai.ask_local('Help',{'_customer_reply':True},[])
            with self.assertRaises(ValueError):ai.ask_local('Build an agent',{'_agent_builder':True,'business':{}},[])

    def test_managed_ai_missing_key_stays_platform_managed(self):
        with patch.dict(os.environ,{'TW_AI_ENABLED':'true','TW_PLATFORM_AI_MANAGED':'true','TW_AI_PROVIDER':'builtin','TW_OPENAI_API_KEY':''}):
            with patch('platform_ai.entitlement',return_value={'active':True}):
                status=ai.ai_status('1234567890abcdef')
        self.assertTrue(status['platform_managed'])
        self.assertFalse(status['enabled'])
