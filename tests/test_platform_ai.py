import json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from ai import ai_status,openai_key,ask_local
import platform_ai

class PlatformAITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'test.db'
        self.env=patch.dict(os.environ,{'TW_PLATFORM_AI_MANAGED':'false','TW_DATA_DIR':self.tmp.name,'TW_PLATFORM_AI_DB':str(self.path),'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'platform-private-key','TW_PLATFORM_OWNER_EMAIL':'operator@example.test','TW_BILLING_PLANS':json.dumps({'starter':{'name':'Starter','plan_id':'plan_actual','amount_minor':49900,'currency':'INR','interval':'monthly','ai_requests':1}})})
        self.env.start();self.addCleanup(self.env.stop);self.s=Store(self.path);self.ctx=self.s.auth(self.s.setup('Customer','customer@example.test','long-test-password','Business')['token']);self.t=self.ctx['tenant_id'];os.environ['TW_PLATFORM_AI_MANAGED']='true'
    def subscription(self,**change):
        with self.s.db() as db:return self.s._put(db,self.t,'servicejob',{'kind':'billing.subscription','reference':'workspace-0','created':1,'status':'created','payload':{'plan_id':'plan_actual','notes':{'plan_key':'starter'}},'result':dict({'provider_id':'sub_actual','provider_status':'active','current_end':int(time.time())+3600},**change)})
    def test_customer_needs_subscription_but_never_own_key(self):
        a=ai_status(self.t);self.assertTrue(a['configured']);self.assertFalse(a['enabled']);self.assertTrue(a['platform_managed'])
        with self.assertRaises(Problem):self.s.action(self.ctx,'contact.save',{'name':'Blocked','phone':'919000000001'})
        self.subscription();self.assertTrue(ai_status(self.t)['enabled']);self.assertEqual(openai_key(self.t),'platform-private-key')
        self.s.action(self.ctx,'contact.save',{'name':'Allowed','phone':'919000000001'})
        with self.assertRaises(Problem):self.s.action(self.ctx,'ai.connection.save',{'key':'sk-'+'x'*40,'model':'gpt-6-luna','enabled':True})
        state=self.s.state(self.ctx);self.assertNotIn('platform-private-key',json.dumps(state));self.assertNotIn('prefix',state['services']['connections']['billing'])

    def test_customer_ai_errors_request_subscription_or_support_never_a_provider_key(self):
        context={'_workspace_id':self.t,'_gateway_path':str(self.path)}
        with patch('ai.request_openai') as provider:
            with self.assertRaisesRegex(ValueError,'active subscription'):ask_local('Hello',context,[])
            self.subscription()
            with patch.dict(os.environ,{'TW_AI_ENABLED':'false'}):
                with self.assertRaisesRegex(ValueError,'platform support'):ask_local('Hello',context,[])
            provider.assert_not_called()
    def test_cycle_allowance_is_reserved_before_provider_and_last_answer_is_usable(self):
        self.subscription();context={'_workspace_id':self.t,'_gateway_path':str(self.path),'business':'Synthetic'}
        with patch('ai.request_openai',return_value='Synthetic answer') as call:
            self.assertEqual(ask_local('Hello',context,[]),'Synthetic answer');self.assertTrue(ai_status(self.t)['enabled'])
            with self.assertRaisesRegex(ValueError,'used up'):ask_local('Again',context,[])
            self.assertEqual(call.call_count,1)
        self.assertEqual(ai_status(self.t)['allowance']['remaining'],0)
    def test_expiry_cancellation_and_unconfigured_plan_fail_closed(self):
        for data in [{'provider_status':'cancelled'},{'current_end':1}]:
            self.subscription(**data);self.assertFalse(ai_status(self.t)['enabled'])
        self.subscription()
        with patch.dict(os.environ,{'TW_BILLING_PLANS':'{}'}):self.assertFalse(ai_status(self.t)['enabled'])
    def test_failed_provider_request_consumes_reserved_allowance(self):
        self.subscription()
        with patch('ai.request_openai',side_effect=ValueError('uncertain')):
            with self.assertRaises(ValueError):ask_local('Hello',{'_workspace_id':self.t,'_gateway_path':str(self.path)},[])
        self.assertEqual(platform_ai.entitlement(self.t)['remaining'],0)
    def test_large_request_and_foreign_storage_do_not_reserve(self):
        self.subscription()
        for path,text in [(str(self.path),'x'*30001),('foreign.db','small')]:
            with self.assertRaises(ValueError):platform_ai.reserve(self.t,path,text,'',[])
        self.assertEqual(platform_ai.entitlement(self.t)['remaining'],1)
    def test_parallel_requests_cannot_exceed_allowance(self):
        from concurrent.futures import ThreadPoolExecutor
        self.subscription()
        def attempt(_):
            try:platform_ai.reserve(self.t,str(self.path),'small','question',[]);return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=5) as pool:self.assertEqual(sum(pool.map(attempt,range(5))),1)
        self.assertEqual(platform_ai.entitlement(self.t)['remaining'],0)
    def test_unconfigured_paid_plan_does_not_unlock_crm(self):
        self.subscription()
        with patch.dict(os.environ,{'TW_BILLING_PLANS':'{}'}):
            self.assertFalse(self.s.state(self.ctx)['services']['subscription_active'])
            with self.assertRaises(Problem):self.s.action(self.ctx,'contact.save',{'name':'Blocked','phone':'919000000001'})

    def test_billing_only_mode_requires_current_plan_and_provider_identity(self):
        self.subscription()
        with patch.dict(os.environ,{'TW_PLATFORM_AI_MANAGED':'false','TW_BILLING_ENFORCE':'true'}):
            self.assertTrue(self.s.state(self.ctx)['services']['subscription_active'])
            with patch.dict(os.environ,{'TW_BILLING_PLANS':'{}'}):
                self.assertFalse(self.s.state(self.ctx)['services']['subscription_active'])
                with self.assertRaises(Problem):self.s.action(self.ctx,'contact.save',{'name':'Blocked','phone':'919000000001'})
            self.subscription(provider_id='')
            self.assertFalse(self.s.state(self.ctx)['services']['subscription_active'])

    def test_provider_pause_status_is_private_and_does_not_consume_allowance(self):
        import io,urllib.error,openai_errors
        self.subscription()
        error=urllib.error.HTTPError('https://api.openai.com/v1/responses',429,'PRIVATE',{},io.BytesIO(b'{"error":{"code":"insufficient_quota","message":"PRIVATE"}}'))
        try:
            openai_errors.http_failure(error,'platform-private-key')
            status=ai_status(self.t)
            self.assertEqual(status['provider_pause']['reason'],'quota_exhausted')
            self.assertEqual(status['allowance']['remaining'],1)
            self.assertNotIn('PRIVATE',json.dumps(status));self.assertNotIn('platform-private-key',json.dumps(status))
            with patch('openai_errors.time.monotonic',return_value=10**15):
                self.assertIsNone(ai_status(self.t)['provider_pause'])
        finally:
            with openai_errors._lock:openai_errors._blocked.clear()

    def test_known_provider_cooldown_preserves_remaining_subscription_allowance(self):
        import io,urllib.error,openai_errors
        self.subscription()
        plan=json.loads(os.environ['TW_BILLING_PLANS']);plan['starter']['ai_requests']=2
        context={'_workspace_id':self.t,'_gateway_path':str(self.path)}
        def reject(*args,**kwargs):
            error=urllib.error.HTTPError('https://api.openai.com/v1/responses',429,'quota',{},io.BytesIO(b'{"error":{"code":"insufficient_quota"}}'))
            raise openai_errors.http_failure(error,'platform-private-key')
        try:
            with patch.dict(os.environ,{'TW_BILLING_PLANS':json.dumps(plan)}),patch('ai.request_openai',side_effect=reject) as provider:
                for _ in range(2):
                    with self.assertRaises(openai_errors.OpenAIRequestError):ask_local('Hello',context,[])
                self.assertEqual(provider.call_count,1)
                self.assertEqual(platform_ai.entitlement(self.t)['remaining'],1)
        finally:
            with openai_errors._lock:openai_errors._blocked.clear()
