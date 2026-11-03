import base64
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class CommerceServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'commerce.db');self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        prefix='TW_SHOPIFY_'+self.ctx['tenant_id'].upper()+'_'
        self.env=patch.dict(os.environ,{prefix+'SHOP':'example.myshopify.com',prefix+'TOKEN':'test-only',prefix+'API_VERSION':'2026-10',prefix+'WEBHOOK_SECRET':'test-webhook-secret'});self.env.start()

    def tearDown(self):self.env.stop();self.tmp.cleanup()

    def test_sync_upserts_pages_and_retains_actual_provider_pagination(self):
        page={'ok':True,'items':[{'id':'gid://shopify/Product/1','title':'Product','handle':'product','status':'ACTIVE','updated_at':'2026-10-29T00:00:00Z'}],'shop':'example.myshopify.com','api_version':'2026-10','page_info':{'has_next_page':True,'end_cursor':'cursor1'}}
        with patch('commerce_service.fetch_products',return_value=page) as provider:
            self.s.action(self.ctx,'shopify.sync',{'kind':'products'})
            self.s.action(self.ctx,'shopify.sync',{'kind':'products','cursor':'cursor1'})
        state=self.s.state(self.ctx)['commerce']
        self.assertEqual(len(state['products']),1)
        self.assertEqual(state['products'][0]['provider_id'],'gid://shopify/Product/1')
        self.assertTrue(state['connection']['products_page_info']['has_next_page'])
        self.assertEqual(provider.call_args.kwargs['cursor'],'cursor1')
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        self.assertEqual(self.s.state(other)['commerce']['products'],[])

    def test_webhook_is_deduplicated_and_never_applies_unverified_payload_to_catalog(self):
        raw=json.dumps({'id':1,'title':'Signed product update'}).encode()
        signature=base64.b64encode(hmac.new(b'test-webhook-secret',raw,hashlib.sha256).digest()).decode()
        headers={'X-Shopify-Shop-Domain':'example.myshopify.com','X-Shopify-Topic':'products/update','X-Shopify-Hmac-Sha256':signature,'X-Shopify-Webhook-Id':'webhook-test-1'}
        self.assertTrue(self.s.shopify_webhook(self.ctx['tenant_id'],raw,headers)['received'])
        self.assertTrue(self.s.shopify_webhook(self.ctx['tenant_id'],raw,headers)['duplicate'])
        self.assertEqual(self.s.state(self.ctx)['commerce']['products'],[])
        changed=dict(headers,**{'X-Shopify-Topic':'products/delete'})
        with self.assertRaises(Problem):self.s.shopify_webhook(self.ctx['tenant_id'],raw,changed)
        self.assertEqual(len(self.s.state(self.ctx)['commerce']['events']),1)

    def test_failed_sync_never_generates_sample_products(self):
        with patch('commerce_service.fetch_products',return_value={'ok':False,'error':{'code':'not_configured'}}):
            with self.assertRaises(Problem):self.s.action(self.ctx,'shopify.sync',{'kind':'products'})
        self.assertEqual(self.s.state(self.ctx)['commerce']['products'],[])
