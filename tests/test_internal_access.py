import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from ai import ai_status
import platform_ai

class InternalAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'app.db'
        env={'TW_PLATFORM_AI_MANAGED':'false','TW_DATA_DIR':self.tmp.name,'TW_PLATFORM_AI_DB':str(self.path),'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'unit-test-key'}
        self.env=patch.dict(os.environ,env,clear=True);self.env.start();self.addCleanup(self.env.stop)
        self.s=Store(self.path);self.ctx=self.s.auth(self.s.setup('Team','team@example.test','long-test-password','Internal Team')['token']);self.t=self.ctx['tenant_id']
        self.member=self.s.action(self.ctx,'member.add',{'name':'Teammate','email':'member@example.test','password':'long-agent-password','role':'agent'})
        self.agent=self.s.auth(self.s.login('member@example.test','long-agent-password')['token'])
        self.customer=self.s.action(self.ctx,'workspace.create',{'name':'Customer workspace'})
        self.customer_ctx=dict(self.ctx,tenant_id=self.customer['id'])
        os.environ.update(TW_PLATFORM_AI_MANAGED='true',TW_INTERNAL_WORKSPACES=self.t)

    def test_internal_team_uses_crm_without_subscription_but_customers_do_not(self):
        self.s.action(self.ctx,'contact.save',{'name':'Real internal record','phone':'919000000001'})
        self.s.action(self.agent,'contact.save',{'name':'Team record','phone':'919000000002'})
        state=self.s.state(self.ctx)['services'];self.assertTrue(state['internal_use']);self.assertFalse(state['subscription_active']);self.assertTrue(state['crm_access'])
        with self.assertRaises(Problem):self.s.action(self.customer_ctx,'contact.save',{'name':'Blocked customer','phone':'919000000003','internal_use':True})
        self.assertFalse(self.s.state(self.customer_ctx)['services']['internal_use'])

    def test_no_checkout_or_automatic_paid_ai_for_internal_team(self):
        with patch('payment_services.razorpay') as provider:
            with self.assertRaisesRegex(Problem,'Internal team'):self.s.action(self.ctx,'billing.subscribe',{'plan':'starter'})
            provider.assert_not_called()
        self.assertFalse(ai_status(self.t)['enabled'])
        with self.assertRaises(ValueError):platform_ai.reserve(self.t,str(self.path),'facts','hello',[])

    def test_internal_ai_requires_explicit_enable_and_honours_atomic_monthly_limit(self):
        with patch.dict(os.environ,{'TW_INTERNAL_AI_ENABLED':'true','TW_INTERNAL_AI_REQUESTS_PER_MONTH':'2'}):
            self.assertTrue(ai_status(self.t)['enabled'])
            platform_ai.reserve(self.t,str(self.path),'facts','hello',[])
            platform_ai.reserve(self.t,str(self.path),'facts','hello',[])
            self.assertEqual(platform_ai.entitlement(self.t)['remaining'],0)
            with self.assertRaises(ValueError):platform_ai.reserve(self.t,str(self.path),'facts','hello',[])
        self.assertFalse(ai_status(self.t)['enabled'])

    def test_invalid_configuration_fails_closed_and_membership_still_applies(self):
        import internal_access
        for value in ('*','QuantumWeave AI',self.t+',*','["'+self.t+'"]'):
            with patch.dict(os.environ,{'TW_INTERNAL_WORKSPACES':value}):self.assertFalse(internal_access.is_internal(self.t))
        self.s.action(self.ctx,'member.remove',{'id':self.member['id']})
        with self.assertRaises(Problem):self.s.action(self.agent,'contact.save',{'name':'Removed','phone':'919000000004'})

    def test_internal_allowance_is_atomic_and_legacy_paid_flag_cannot_enable_it(self):
        from concurrent.futures import ThreadPoolExecutor
        with patch.dict(os.environ,{'TW_AI_'+self.t.upper()+'_ALLOW_PAID':'true'}):self.assertFalse(ai_status(self.t)['enabled'])
        def reserve(_):
            try:platform_ai.reserve(self.t,str(self.path),'facts','hello',[]);return True
            except ValueError:return False
        with patch.dict(os.environ,{'TW_INTERNAL_AI_ENABLED':'true','TW_INTERNAL_AI_REQUESTS_PER_MONTH':'1'}):
            with ThreadPoolExecutor(max_workers=4) as pool:self.assertEqual(sum(pool.map(reserve,range(4))),1)
        for invalid in ('0','-1','1001','unlimited','True'):
            with patch.dict(os.environ,{'TW_INTERNAL_AI_ENABLED':'true','TW_INTERNAL_AI_REQUESTS_PER_MONTH':invalid}):self.assertFalse(ai_status(self.t)['enabled'])
