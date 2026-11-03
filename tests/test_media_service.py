import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from meta import ProviderError


class MediaServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'data/app.db');self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.c=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001'})
        with patch('media_service.upload_media',return_value='123456'):self.asset=self.s.upload_media_asset(self.ctx,'photo.png','image/png',b'unit-test-image')

    def tearDown(self):self.tmp.cleanup()
    def send(self,nonce='request_nonce_123456',**kw):return self.s.action(self.ctx,'media.send',dict({'contact_id':self.c['id'],'asset_id':self.asset['id'],'caption':'Photo','nonce':nonce},**kw))
    def window(self):
        import time
        with self.s.db() as db:
            c=self.s._get(db,self.ctx['tenant_id'],'contact',self.c['id']);self.s._put(db,self.ctx['tenant_id'],'contact',dict(c,last_real_inbound=int(time.time())),c['id'])

    def test_upload_is_private_and_send_requires_real_window(self):
        data,mime,name=self.s.read_media_asset(self.ctx,self.asset['id']);self.assertEqual(data,b'unit-test-image');self.assertEqual(name,'photo.png')
        with patch('media_service.meta_status',return_value={'live':True}),patch('media_service.send_media') as provider:
            with self.assertRaises(Problem):self.send()
            provider.assert_not_called()
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        with self.assertRaises(Problem):self.s.read_media_asset(other,self.asset['id'])

    def test_nonce_prevents_duplicate_provider_send_and_changed_payload(self):
        self.window()
        with patch('media_service.meta_status',return_value={'live':True}),patch('media_service.send_media',return_value='wamid_media') as provider:
            self.assertEqual(self.send()['status'],'accepted');self.assertEqual(self.send()['status'],'accepted');self.assertEqual(provider.call_count,1)
            with self.assertRaises(Problem):self.send(caption='Changed')
        state=self.s.state(self.ctx);self.assertEqual(state['messages'][0]['status'],'accepted')
        self.assertEqual(state['contacts'][0]['outgoing_watch']['message_id'],state['messages'][0]['id'])

    def test_uncertain_send_is_unknown_and_identical_retry_cannot_duplicate(self):
        self.window()
        with patch('media_service.meta_status',return_value={'live':True}),patch('media_service.send_media',side_effect=ProviderError('Uncertain',False)) as provider:
            self.assertEqual(self.send()['status'],'unknown')
            self.assertEqual(self.send()['status'],'unknown')
            with self.assertRaises(Problem):self.send(nonce='another_nonce_123456')
            self.assertEqual(provider.call_count,1)
