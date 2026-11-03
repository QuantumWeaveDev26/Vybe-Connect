import json
import os
import time
from unittest.mock import patch
import unittest
from tests import test_customer_assistant as fixtures
from store import Problem


class CustomerOrderTests(unittest.TestCase):
    save=fixtures.CustomerAssistantTests.save
    incoming=fixtures.CustomerAssistantTests.incoming
    output=fixtures.CustomerAssistantTests.output
    work_once=fixtures.CustomerAssistantTests.work_once
    def setUp(self):
        fixtures.CustomerAssistantTests.setUp(self)
        self.shop='example.myshopify.com'
        self.shop_env=patch.dict(os.environ,{'TW_SHOPIFY_'+self.ctx['tenant_id'].upper()+'_SHOP':self.shop});self.shop_env.start()
        self.incoming()
        self.contact=self.s.state(self.ctx)['contacts'][0]
        with self.s.db() as db:
            self.order=self.s._put(db,self.ctx['tenant_id'],'shopifyorder',{'provider_id':'gid://shopify/Order/1','shop':self.shop,'name':'#1001','synced':int(time.time()),'source':'shopify_api','financial_status':'PAID','fulfillment_status':'UNFULFILLED','total_price':{'amount':'10.00','currency_code':'INR'},'private_note':'SECRET'})
    def tearDown(self):self.shop_env.stop();fixtures.CustomerAssistantTests.tearDown(self)
    def link(self,**extra):return self.s.action(self.ctx,'shopify.order.link',dict(order_id=self.order['id'],contact_id=self.contact['id'],ownership_confirmed=True,**extra))

    def test_order_link_requires_admin_confirmation_and_workspace_scope(self):
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,role='agent'),'shopify.order.link',{'order_id':self.order['id'],'contact_id':self.contact['id'],'ownership_confirmed':True})
        with self.assertRaises(Problem):self.s.action(self.ctx,'shopify.order.link',{'order_id':self.order['id'],'contact_id':self.contact['id']})
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,tenant_id=other['id']),'shopify.order.link',{'order_id':self.order['id'],'contact_id':self.contact['id'],'ownership_confirmed':True})
        self.link();self.link()
        self.assertEqual(len(self.s.state(self.ctx)['commerce']['order_links']),1)

    def test_linked_orders_are_denied_until_assistant_opt_in(self):
        self.link();model,_=self.work_once()
        self.assertEqual(model.call_args.args[1].get('customer_orders',[]),[])

    def test_only_linked_fresh_current_shop_projected_orders_reach_model(self):
        self.link();self.save(order_access=True);self.incoming('order_question','Where is my order?')
        with self.s.db() as db:
            self.s._put(db,self.ctx['tenant_id'],'shopifyorder',dict(self.order,name='OTHER CUSTOMER'),None)
        model,_=self.work_once();facts=model.call_args.args[1]['customer_orders']
        self.assertEqual(len(facts),1);self.assertEqual(facts[0]['name'],'#1001');self.assertIn('synced',facts[0])
        self.assertNotIn('SECRET',json.dumps(facts));self.assertNotIn('provider_id',facts[0]);self.assertNotIn('shop',facts[0])

    def test_stale_orders_cannot_support_model_without_knowledge(self):
        self.link();self.save(order_access=True,source_ids=[])
        with self.s.db() as db:self.s._put(db,self.ctx['tenant_id'],'shopifyorder',dict(self.order,synced=int(time.time())-86401),self.order['id'])
        self.incoming('stale_order','Order update?');model,_=self.work_once();model.assert_not_called()

    def test_unlink_during_generation_discards_late_answer(self):
        link=self.link();self.save(order_access=True);self.incoming('order_update','Order update?')
        def changed(*args):
            self.s.action(self.ctx,'shopify.order.unlink',{'id':link['id']});return self.output()
        self.work_once(side_effect=changed)
        self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))

    def test_fresh_order_can_support_reply_without_manual_knowledge(self):
        self.link();self.save(order_access=True,source_ids=[]);self.incoming('order_only','Order update?')
        model,send=self.work_once();model.assert_called_once();send.assert_not_called()

    def test_order_cannot_be_silently_reassigned(self):
        self.link();self.incoming('other_person',phone='919000000002')
        other=next(c for c in self.s.state(self.ctx)['contacts'] if c['id']!=self.contact['id'])
        with self.assertRaises(Problem):self.s.action(self.ctx,'shopify.order.link',{'order_id':self.order['id'],'contact_id':other['id'],'ownership_confirmed':True})

    def test_current_shop_change_suppresses_previous_shop_orders(self):
        self.link();self.save(order_access=True,source_ids=[]);self.incoming('changed_shop','Order?')
        with patch.dict(os.environ,{'TW_SHOPIFY_'+self.ctx['tenant_id'].upper()+'_SHOP':'different.myshopify.com'}):
            model,_=self.work_once();model.assert_not_called()

    def test_order_sync_change_during_generation_discards_answer(self):
        self.link();self.save(order_access=True);self.incoming('new_sync','Order update?')
        def changed(*args):
            with self.s.db() as db:self.s._put(db,self.ctx['tenant_id'],'shopifyorder',dict(self.order,fulfillment_status='FULFILLED'),self.order['id'])
            return self.output()
        self.work_once(side_effect=changed)
        self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))

    def test_context_has_at_most_five_verified_orders(self):
        self.link()
        for n in range(8):
            with self.s.db() as db:order=self.s._put(db,self.ctx['tenant_id'],'shopifyorder',dict(self.order,name='#'+str(2000+n)),None)
            self.s.action(self.ctx,'shopify.order.link',{'order_id':order['id'],'contact_id':self.contact['id'],'ownership_confirmed':True})
        self.save(order_access=True);self.incoming('many_orders','Orders?');model,_=self.work_once()
        self.assertEqual(len(model.call_args.args[1]['customer_orders']),5)
