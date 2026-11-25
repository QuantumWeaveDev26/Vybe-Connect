import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from ai import ai_status
import platform_ai

class InternalAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'app.db'
        env={'TW_PLATFORM_AI_MANAGED':'false','TW_DATA_DIR':self.tmp.name,'TW_PLATFORM_AI_DB':str(self.path),'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'unit-test-key','TW_INTERNAL_AI_BUDGET_PAISE':'29900'}
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

    def test_rupee_budget_reserves_atomically_and_blocks_before_provider(self):
        from concurrent.futures import ThreadPoolExecutor
        def reserve(_):
            try:platform_ai.reserve(self.t,str(self.path),'facts','hello',[]);return True
            except ValueError:return False
        # Each minimal request reserves 339 paise. Exactly one fits 500 paise.
        with patch.dict(os.environ,{'TW_INTERNAL_AI_ENABLED':'true','TW_INTERNAL_AI_REQUESTS_PER_MONTH':'1000','TW_INTERNAL_AI_BUDGET_PAISE':'500'}):
            with ThreadPoolExecutor(max_workers=5) as pool:self.assertEqual(sum(pool.map(reserve,range(5))),1)
            allowance=platform_ai.entitlement(self.t)
            self.assertEqual(allowance['reserved_paise'],339)
            self.assertEqual(allowance['remaining'],0)
            with self.s.db() as db:
                self.assertEqual(db.execute('SELECT requests FROM platform_ai_usage WHERE tenant=?',(self.t,)).fetchone()[0],1)
        for invalid in ('','-1','0','299.00','unlimited'):
            with patch.dict(os.environ,{'TW_INTERNAL_AI_ENABLED':'true','TW_INTERNAL_AI_BUDGET_PAISE':invalid}):self.assertFalse(ai_status(self.t)['enabled'])

    def test_large_request_budget_failure_does_not_consume_request_or_cross_cap(self):
        with patch.dict(os.environ,{'TW_INTERNAL_AI_ENABLED':'true','TW_INTERNAL_AI_BUDGET_PAISE':'500'}):
            with self.assertRaisesRegex(ValueError,'spending limit'):platform_ai.reserve(self.t,str(self.path),'x'*29000,'hello',[])
            self.assertEqual(platform_ai.entitlement(self.t)['used'],0)
            self.assertEqual(platform_ai.entitlement(self.t)['reserved_paise'],0)

    def test_two_internal_workspaces_share_one_atomic_rupee_ceiling(self):
        from concurrent.futures import ThreadPoolExecutor
        other=self.customer['id']
        with patch.dict(os.environ,{'TW_INTERNAL_WORKSPACES':self.t+','+other,'TW_INTERNAL_AI_ENABLED':'true','TW_INTERNAL_AI_REQUESTS_PER_MONTH':'1000','TW_INTERNAL_AI_BUDGET_PAISE':'500'}):
            def reserve(tenant):
                try:platform_ai.reserve(tenant,str(self.path),'facts','hello',[]);return True
                except ValueError:return False
            with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(reserve,[self.t,other,self.t,other]))
            self.assertEqual(sum(results),1,'Concurrent workspaces must not each obtain a separate budget')
            a,b=platform_ai.entitlement(self.t),platform_ai.entitlement(other)
            self.assertEqual(a['reserved_paise'],b['reserved_paise'])
            self.assertLessEqual(a['reserved_paise'],500)
            self.assertEqual(a['used'],b['used'])
            with self.s.db() as db:
                cycle=a['cycle'];db.execute('INSERT INTO internal_ai_budget VALUES(?,?,?)',('removed-workspace',cycle,20))
            self.assertEqual(platform_ai.entitlement(self.t)['reserved_paise'],a['reserved_paise']+20)

    def test_two_internal_workspaces_share_request_limit_and_keep_customer_gate(self):
        other=self.customer['id']
        with patch.dict(os.environ,{'TW_INTERNAL_WORKSPACES':self.t+','+other,'TW_INTERNAL_AI_ENABLED':'true','TW_INTERNAL_AI_REQUESTS_PER_MONTH':'1'}):
            platform_ai.reserve(self.t,str(self.path),'facts','hello',[])
            self.assertEqual(platform_ai.entitlement(other)['remaining'],0)
            with self.assertRaises(ValueError):platform_ai.reserve(other,str(self.path),'facts','hello',[])
            self.assertFalse(ai_status('1234567890abcdef')['paid_allowed'])
