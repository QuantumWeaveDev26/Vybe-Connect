import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from store import Store
import provider_checks

class MetaReadinessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'test.db')
  self.ctx=self.store.auth(self.store.setup('Owner','audit@example.test','long-audit-password','Audit')['token']);self.tenant=self.ctx['tenant_id']
  p='TW_META_'+self.tenant.upper()+'_'
  self.env=patch.dict(os.environ,{'TW_PROVIDER_READS':'true',p+'TOKEN':'private-token',p+'PHONE_ID':'123',p+'WABA_ID':'456',p+'APP_SECRET':'private-secret',p+'VERSION':'v25.0'});self.env.start()
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def run_check(self,responses):
  with patch('provider_checks.request',side_effect=responses) as remote:
   result=provider_checks.check(self.store,self.ctx,'meta')
  return result,remote
 def test_mismatched_waba_cannot_pass(self):
  result,remote=self.run_check([{'id':'123'},{'data':[{'id':'999'}]}])
  self.assertEqual(result['outcome'],'failed_or_unconfirmed');self.assertEqual(result['reason'],'phone_waba_membership');self.assertIn('same selected number',result['hint']);self.assertEqual(remote.call_count,2)
 def test_valid_phone_membership_and_templates_are_required(self):
  result,remote=self.run_check([{'id':'123'},{'data':[{'id':'123'}]},{'data':[]}])
  self.assertEqual(result['outcome'],'passed');self.assertEqual(result['reason'],'');self.assertEqual(result['hint'],'');self.assertEqual(remote.call_count,3)
  self.assertIn('/456/phone_numbers?',remote.call_args_list[1].args[0]);self.assertIn('/456/message_templates?',remote.call_args_list[2].args[0])
  for call in remote.call_args_list:self.assertIn('appsecret_proof=',call.args[0]);self.assertNotIn('private-secret',call.args[0]);self.assertNotIn('private-token',call.args[0])
 def test_membership_checks_follow_cursor_without_fetching_provider_next_url(self):
  result,remote=self.run_check([{'id':'123'},{'data':[], 'paging':{'next':'https://untrusted.example/steal','cursors':{'after':'cursor1'}}},{'data':[{'id':'123'}]},{'data':[]}])
  self.assertEqual(result['outcome'],'passed');self.assertIn('after=cursor1',remote.call_args_list[2].args[0]);self.assertTrue(all(c.args[0].startswith('https://graph.facebook.com/') for c in remote.call_args_list))
 def test_template_permission_failure_does_not_pass(self):
  from provider_transport import RemoteError
  result,_=self.run_check([{'id':'123'},{'data':[{'id':'123'}]},RemoteError('denied',True)])
  self.assertEqual(result['outcome'],'failed_or_unconfirmed')

 def test_phone_access_failure_has_safe_actionable_reason(self):
  from provider_transport import RemoteError
  import json
  result,_=self.run_check([RemoteError('Provider returned HTTP 401.',True)])
  self.assertEqual(result['reason'],'phone_access');self.assertEqual(result['http_status'],401)
  self.assertIn('token',result['hint']);self.assertNotIn('private-token',json.dumps(result))
  saved=self.store.state(self.ctx)['provider_checks'][0];self.assertEqual(saved['reason'],'phone_access');self.assertEqual(saved['http_status'],401)
 def test_waba_access_and_template_access_are_distinct(self):
  from provider_transport import RemoteError
  result,_=self.run_check([{'id':'123'},RemoteError('Provider returned HTTP 400.',True)])
  self.assertEqual(result['reason'],'waba_access')
  result,_=self.run_check([{'id':'123'},{'data':[{'id':'123'}]},RemoteError('Provider returned HTTP 403.',True)])
  self.assertEqual(result['reason'],'template_access');self.assertEqual(result['http_status'],403)

 def test_meta_token_error_is_reported_without_credential_data(self):
  from provider_transport import RemoteError
  failure=RemoteError('Provider returned HTTP 400.',True);failure.provider_code=190;failure.http_status=400
  result,_=self.run_check([failure]);self.assertEqual(result['reason'],'meta_token_access');self.assertEqual(result['provider_code'],190);self.assertIn('Replace it privately',result['hint'])
