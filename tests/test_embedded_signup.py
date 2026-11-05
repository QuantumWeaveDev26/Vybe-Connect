import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import embedded_signup as es
import meta
from store import Store


class EmbeddedSignupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'TW_DATA_DIR':self.temp.name,'TW_META_PLATFORM_ENABLED':'true','TW_META_PLATFORM_APP_ID':'123','TW_META_PLATFORM_CONFIG_ID':'456','TW_META_PLATFORM_APP_SECRET':'a'*32,'TW_META_PLATFORM_VERIFY_TOKEN':'v'*40,'TW_META_PLATFORM_VERSION':'v25.0','TW_PUBLIC_ORIGIN':'https://example.test','TW_BILLING_ENFORCE':'false','TW_PUBLIC_SIGNUP':'true'})
        self.env.start();self.store=Store(Path(self.temp.name)/'app.db')
        result=self.store.setup('Owner','owner@example.test','a-long-enough-password','Business')
        self.ctx=self.store.auth(result['token']);self.calls=[]
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def fake(self,c,edge,token='',payload=None,query=None):
        self.calls.append((edge,payload))
        if edge=='oauth/access_token':return {'access_token':'private-test-token-'+'x'*30}
        if edge=='debug_token':return {'data':{'is_valid':True,'app_id':'123','scopes':['whatsapp_business_management','whatsapp_business_messaging'],'expires_at':int(time.time())+86400}}
        if edge=='789/phone_numbers':return {'data':[{'id':'101','display_phone_number':'+1 555 0100','verified_name':'Business'}]}
        if edge=='789/subscribed_apps':
            if payload is not None:return {'success':True}
            return {'data':[{'whatsapp_business_api_data':{'id':'123'},'override_callback_uri':'https://example.test/webhook/'+self.ctx['tenant_id']}]}
        raise AssertionError(edge)
    def payload(self,ctx=None):
        started=es.begin(self.store,ctx or self.ctx)
        return {'state':started['state'],'code':'private-code','waba_id':'789','phone_number_id':'101'}
    def finish(self):
        data=self.payload()
        with patch.object(es,'graph',self.fake):return es.finish(self.store,self.ctx,data)
    def test_begin_is_session_bound_and_does_not_expose_secrets(self):
        result=es.begin(self.store,self.ctx)
        self.assertEqual(result['config_id'],'456');self.assertNotIn('APP_SECRET',json.dumps(result))
        with self.store.db() as db:
            row=db.execute('SELECT * FROM whatsapp_auth_attempts').fetchone()
            self.assertNotEqual(row['state'],result['state']);self.assertEqual(row['session'],self.ctx['_session_hash'])
    def test_non_admin_and_revoked_sessions_cannot_start(self):
        with self.assertRaises(es.ConnectionError):es.begin(self.store,dict(self.ctx,role='agent'))
        with self.store.db() as db:db.execute('DELETE FROM sessions')
        with self.assertRaises(es.ConnectionError):es.begin(self.store,self.ctx)
    def test_connect_stores_token_privately_and_pauses_sending(self):
        result=self.finish();self.assertEqual(result['status'],'connected');self.assertFalse(result['sending_enabled'])
        values=meta.settings(self.ctx['tenant_id']);self.assertEqual(values['PHONE_ID'],'101');self.assertEqual(values['LIVE'],'false')
        self.assertNotIn('private-test-token',json.dumps(self.store.state(self.ctx)))
        self.assertNotIn('private-test-token',Path(self.store.path).read_bytes().decode(errors='ignore'))
        self.assertTrue(all('/messages' not in edge and '/register' not in edge for edge,_ in self.calls))
    def test_replay_and_wrong_session_rejected_before_provider(self):
        data=self.payload()
        with patch.object(es,'graph',self.fake):es.finish(self.store,self.ctx,data)
        with patch.object(es,'graph') as transport:
            with self.assertRaises(es.ConnectionError):es.finish(self.store,self.ctx,data)
            transport.assert_not_called()
        data=self.payload();other=dict(self.ctx,_session_hash='other')
        with self.assertRaises(es.ConnectionError):es.finish(self.store,other,data)
    def test_expired_attempt_rejected_before_exchange(self):
        data=self.payload()
        with self.store.db() as db:db.execute('UPDATE whatsapp_auth_attempts SET expires=1')
        with patch.object(es,'graph') as transport:
            with self.assertRaises(es.ConnectionError):es.finish(self.store,self.ctx,data)
            transport.assert_not_called()
    def test_phone_from_another_account_never_activated(self):
        data=self.payload();data['phone_number_id']='999'
        with patch.object(es,'graph',self.fake):
            with self.assertRaises(es.ConnectionError):es.finish(self.store,self.ctx,data)
        self.assertIsNone(es.read_credentials(self.ctx['tenant_id']))
        self.assertFalse(any(payload is not None for edge,payload in self.calls if edge.endswith('/subscribed_apps')))
    def test_wrong_app_or_missing_scope_never_activated(self):
        for debug in [{'is_valid':True,'app_id':'999','scopes':['whatsapp_business_management','whatsapp_business_messaging']},{'is_valid':True,'app_id':'123','scopes':['whatsapp_business_management']}]:
            data=self.payload()
            def fake(c,edge,**kwargs):return {'data':debug} if edge=='debug_token' else self.fake(c,edge,**kwargs)
            with patch.object(es,'graph',fake):
                with self.assertRaises(es.ConnectionError):es.finish(self.store,self.ctx,data)
            self.assertIsNone(es.read_credentials(self.ctx['tenant_id']))
    def test_other_workspace_cannot_claim_same_number_or_retarget_webhook(self):
        self.finish();second=self.store.signup('Second','second@example.test','another-long-password','Other');ctx=self.store.auth(second['token']);data=self.payload(ctx);self.calls=[]
        with patch.object(es,'graph',self.fake):
            with self.assertRaises(es.ConnectionError) as caught:es.finish(self.store,ctx,data)
        self.assertEqual(caught.exception.code,409)
        self.assertFalse(any(edge.endswith('/subscribed_apps') for edge,payload in self.calls))
    def test_sending_requires_explicit_boolean_and_connection(self):
        self.finish();es.action(self.store,self.ctx,'whatsapp.sending',{'enabled':True})
        self.assertEqual(meta.settings(self.ctx['tenant_id'])['LIVE'],'true')
        with self.assertRaises(es.ConnectionError):es.action(self.store,self.ctx,'whatsapp.sending',{'enabled':'true'})
    def test_disconnect_stops_credentials_and_does_not_restore_environment(self):
        self.finish();prefix='TW_META_'+self.ctx['tenant_id'].upper()+'_TOKEN'
        with patch.dict(os.environ,{prefix:'old-operator-token'}):
            result=es.action(self.store,self.ctx,'whatsapp.disconnect',{})
            self.assertEqual(result['status'],'disconnected');self.assertEqual(meta.settings(self.ctx['tenant_id'])['TOKEN'],'')
        with self.assertRaises(es.ConnectionError):es.action(self.store,self.ctx,'whatsapp.sending',{'enabled':True})
    def test_unsafe_secret_file_permissions_fail_closed(self):
        if os.name=='nt':self.skipTest('POSIX file modes are verified in Linux deployment.')
        self.finish();es.credential_path(self.ctx['tenant_id']).chmod(0o644)
        with self.assertRaises(es.ConnectionError):meta.settings(self.ctx['tenant_id'])
    def test_disconnect_during_provider_work_prevents_activation(self):
        data=self.payload()
        def fake(c,edge,**kwargs):
            result=self.fake(c,edge,**kwargs)
            if edge=='789/subscribed_apps' and kwargs.get('payload'):
                es.action(self.store,self.ctx,'whatsapp.disconnect',{})
            return result
        with patch.object(es,'graph',fake):
            with self.assertRaises(es.ConnectionError):es.finish(self.store,self.ctx,data)
        self.assertEqual(meta.settings(self.ctx['tenant_id'])['TOKEN'],'')
        self.assertEqual(es.state(self.store,self.ctx)['status'],'disconnected')
    def test_subscription_failure_is_reconnectable_not_connected(self):
        data=self.payload()
        def fake(c,edge,**kwargs):
            if edge.endswith('/subscribed_apps'):raise es.ConnectionError('Provider unavailable.',502)
            return self.fake(c,edge,**kwargs)
        with patch.object(es,'graph',fake):
            with self.assertRaises(es.ConnectionError):es.finish(self.store,self.ctx,data)
        self.assertEqual(es.state(self.store,self.ctx)['status'],'needs_reconnect')
        self.assertIsNone(es.read_credentials(self.ctx['tenant_id']))
    def test_expiry_pauses_sending_and_marks_reconnect(self):
        self.finish();es.action(self.store,self.ctx,'whatsapp.sending',{'enabled':True})
        saved=es.read_credentials(self.ctx['tenant_id']);saved['expires_at']=1;es.write_credentials(self.ctx['tenant_id'],saved)
        with self.store.db() as db:db.execute('UPDATE whatsapp_connections SET expires=1')
        self.assertEqual(meta.settings(self.ctx['tenant_id'])['LIVE'],'false')
        self.assertEqual(es.state(self.store,self.ctx)['status'],'expired')

    def test_expired_credentials_override_stale_connection_expiry(self):
        self.finish();es.action(self.store,self.ctx,'whatsapp.sending',{'enabled':True})
        saved=es.read_credentials(self.ctx['tenant_id']);saved['expires_at']=1;es.write_credentials(self.ctx['tenant_id'],saved)
        result=es.state(self.store,self.ctx)
        self.assertEqual(result['status'],'expired');self.assertFalse(result['sending_enabled'])
        with self.assertRaises(es.ConnectionError):es.action(self.store,self.ctx,'whatsapp.sending',{'enabled':True})
    def test_missing_credential_file_requires_reconnect(self):
        self.finish();es.credential_path(self.ctx['tenant_id']).unlink()
        result=es.state(self.store,self.ctx)
        self.assertEqual(result['status'],'needs_reconnect');self.assertFalse(result['sending_enabled'])
    def test_disconnect_remains_disconnected_after_old_authorization_expires(self):
        self.finish();es.action(self.store,self.ctx,'whatsapp.disconnect',{})
        with self.store.db() as db:db.execute('UPDATE whatsapp_connections SET expires=1')
        self.assertEqual(es.state(self.store,self.ctx)['status'],'disconnected')
