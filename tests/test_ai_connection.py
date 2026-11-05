import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from ai import ai_status,openai_key,ask_local
import ai_connection


class AIConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'TW_DATA_DIR':self.tmp.name,'TW_AI_PROVIDER':'openai','TW_AI_ENABLED':'true','TW_PUBLIC_SIGNUP':'true','TW_BILLING_ENFORCE':'false','TW_OPENAI_API_KEY':'old-platform-key'})
        self.env.start();self.store=Store(Path(self.tmp.name)/'app.db')
        self.ctx=self.store.auth(self.store.setup('Owner','owner@example.test','test-long-password','Business')['token'])
        self.key='sk-'+('a'*40)
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def save(self,enabled=False,key=None):
        return self.store.action(self.ctx,'ai.connection.save',{'key':self.key if key is None else key,'model':'test-model','enabled':enabled})
    def test_save_is_paused_private_and_never_calls_provider(self):
        with patch('ai.request_openai') as provider:
            state=self.save();self.assertTrue(state['configured']);self.assertFalse(state['enabled'])
            with self.assertRaises(ValueError):ask_local('hi',{'business':'Test','_workspace_id':self.ctx['tenant_id']},[])
            provider.assert_not_called()
        self.assertEqual(openai_key(self.ctx['tenant_id']),self.key)
        self.assertNotIn(self.key,json.dumps(self.store.state(self.ctx)))
        self.assertNotIn(self.key,Path(self.store.path).read_bytes().decode(errors='ignore'))
    def test_real_usage_requires_explicit_enable_and_platform_switch(self):
        self.save(True);self.assertTrue(ai_status(self.ctx['tenant_id'])['enabled'])
        with patch('ai.request_openai',return_value='mock response') as provider:
            self.assertEqual(ask_local('hi',{'business':'Test','_workspace_id':self.ctx['tenant_id']},[]),'mock response')
            self.assertEqual(provider.call_args.args[0],self.key)
        with patch.dict(os.environ,{'TW_AI_ENABLED':'false'}):self.assertFalse(ai_status(self.ctx['tenant_id'])['enabled'])
    def test_pause_and_disconnect_fail_closed_even_with_environment_key(self):
        self.save(True);self.store.action(self.ctx,'ai.connection.pause',{})
        self.assertFalse(ai_status(self.ctx['tenant_id'])['enabled'])
        self.store.action(self.ctx,'ai.connection.disconnect',{})
        self.assertEqual(openai_key(self.ctx['tenant_id']),'')
        self.assertFalse(ai_status(self.ctx['tenant_id'])['configured'])
    def test_preserve_key_on_edit_and_do_not_preserve_enable_implicitly(self):
        self.save(True);self.save(False,key='')
        self.assertEqual(openai_key(self.ctx['tenant_id']),self.key)
        self.assertFalse(ai_status(self.ctx['tenant_id'])['enabled'])
    def test_key_is_isolated_between_workspaces(self):
        self.save();other=self.store.signup('Other','other@example.test','other-long-password','Other')
        ctx=self.store.auth(other['token']);self.assertNotEqual(openai_key(ctx['tenant_id']),self.key)
        self.assertNotIn(self.key,json.dumps(self.store.state(ctx)))
    def test_non_admin_or_revoked_session_cannot_modify(self):
        with self.assertRaises(Problem):self.store.action(dict(self.ctx,role='agent'),'ai.connection.save',{'key':self.key,'model':'test','enabled':True})
        with self.store.db() as db:db.execute('DELETE FROM sessions')
        with self.assertRaises(Problem):self.save(True)
    def test_invalid_key_model_and_enable_values_rejected_without_leaking_input(self):
        for data in [{'key':'secret-not-a-key','model':'test','enabled':False},{'key':self.key,'model':'https://evil.test','enabled':False},{'key':self.key,'model':'test','enabled':'true'}]:
            with self.assertRaises(Problem) as failure:self.store.action(self.ctx,'ai.connection.save',data)
            self.assertNotIn(self.key,str(failure.exception));self.assertIsNone(ai_connection.settings(self.ctx['tenant_id']))
    def test_inflight_response_keeps_key_available_for_cancellation(self):
        self.save(True)
        with self.store.db() as db:
            job=self.store._put(db,self.ctx['tenant_id'],'aijob',{'provider':'openai','status':'waiting','provider_id':'response-test'})
        with self.assertRaises(Problem) as failure:self.save(True,key='sk-'+('b'*40))
        self.assertEqual(failure.exception.code,409)
        with self.assertRaises(Problem):self.store.action(self.ctx,'ai.connection.disconnect',{})
        self.store.action(self.ctx,'ai.connection.pause',{});self.assertEqual(openai_key(self.ctx['tenant_id']),self.key)
        with self.store.db() as db:self.store._put(db,self.ctx['tenant_id'],'aijob',dict(job,status='cancelled'),job['id'])
        self.store.action(self.ctx,'ai.connection.disconnect',{});self.assertEqual(openai_key(self.ctx['tenant_id']),'')
