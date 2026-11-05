import unittest
from unittest.mock import patch
from deploy.meta_setup_once import MetaSetup,SetupError

class MetaSetupTests(unittest.TestCase):
 def setup_operator(self):
  p='TW_META_EAA91C5FE6F20007_'
  env={p+'TOKEN':'private-token',p+'APP_SECRET':'private-secret',p+'VERIFY_TOKEN':'private-verify',p+'VERSION':'v25.0',p+'WABA_ID':'456','TW_PUBLIC_ORIGIN':'https://chat.example.test'}
  op=MetaSetup('eaa91c5fe6f20007','123',env);op.callback_check=lambda:None;return op
 def responder(self,op,existing=None,debug=None,ids=None):
  calls=[];ids=ids or ['789'];debug=debug or {'is_valid':True,'app_id':'123','scopes':['whatsapp_business_management','whatsapp_business_messaging'],'expires_at':0}
  def graph(edge,stage,method='GET',data=None,query=None,app=False):
   calls.append((edge,stage,method,data,app))
   if stage=='token_debug':return {'data':debug}
   if stage=='app_subscription_read':return {'data':[existing] if existing else []}
   if stage=='waba_subscription_read':return {'data':[{'whatsapp_business_api_data':{'id':i}} for i in ids]}
   if method=='POST':return {'success':True}
   if stage=='app_subscription_readback':return {'data':[{'object':'whatsapp_business_account','callback_url':op.callback,'active':True,'fields':[{'name':'messages'},{'name':'message_template_status_update'}]}]}
   if stage=='waba_subscription_readback':return {'data':[{'whatsapp_business_api_data':{'id':i}} for i in ids+['123']]}
   raise AssertionError(stage)
  op.graph=graph;return calls
 def test_read_only_default_never_subscribes(self):
  op=self.setup_operator();calls=self.responder(op);result=op.run();self.assertFalse(result['applied']);self.assertFalse(any(c[2]=='POST' for c in calls))
 def test_apply_preserves_other_apps_and_fields(self):
  op=self.setup_operator();existing={'object':'whatsapp_business_account','active':True,'callback_url':op.callback,'fields':[{'name':'message_template_status_update'}]};calls=self.responder(op,existing)
  result=op.run(True);self.assertTrue(result['messages_subscribed']);self.assertTrue(result['other_subscriptions_preserved']);posts=[c for c in calls if c[2]=='POST'];self.assertEqual(len(posts),2);self.assertEqual(posts[0][3]['fields'],'message_template_status_update,messages')
 def test_other_callback_is_not_overwritten(self):
  op=self.setup_operator();calls=self.responder(op,{'object':'whatsapp_business_account','callback_url':'https://other.example/webhook'})
  with self.assertRaises(SetupError) as e:op.run(True)
  self.assertEqual(e.exception.stage,'existing_callback_conflict');self.assertFalse(any(c[2]=='POST' for c in calls))
 def test_token_must_belong_to_selected_app(self):
  op=self.setup_operator();calls=self.responder(op,debug={'is_valid':True,'app_id':'999'})
  with self.assertRaises(SetupError) as e:op.run(True)
  self.assertEqual(e.exception.stage,'token_app_mismatch');self.assertEqual(len(calls),1)
 def test_missing_messaging_permission_does_not_apply(self):
  op=self.setup_operator();calls=self.responder(op,debug={'is_valid':True,'app_id':'123','scopes':['whatsapp_business_management']})
  with self.assertRaises(SetupError) as e:op.run(True)
  self.assertEqual(e.exception.stage,'token_permissions');self.assertFalse(any(c[2]=='POST' for c in calls))
 def test_bad_challenge_prevents_any_write(self):
  op=self.setup_operator();calls=self.responder(op);op.callback_check=lambda:(_ for _ in ()).throw(SetupError('callback_challenge'))
  with self.assertRaises(SetupError):op.run(True)
  self.assertFalse(any(c[2]=='POST' for c in calls))
