import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from server import make_server


class DeploymentTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'deploy.db';self.server=None
    def tearDown(self):
        if self.server:self.server.shutdown();self.server.server_close();self.thread.join()
        self.tmp.cleanup()
    def start(self,**changes):
        values={'TW_DEPLOYMENT':'production','TW_PUBLIC_ORIGIN':'https://chat.example.test','TW_SETUP_TOKEN':'test-only-setup-token-32-characters','TW_BIND':'127.0.0.1'};values.update(changes)
        with patch.dict(os.environ,values):self.server=make_server(0,self.path)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def request(self,path,method='GET',data=None,**headers):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_address[1]);values={'Host':'chat.example.test','Origin':'https://chat.example.test','Content-Type':'application/json'};values.update(headers)
        connection.request(method,path,body=json.dumps(data).encode() if data is not None else None,headers=values);r=connection.getresponse();body=r.read();result=(r.status,dict(r.getheaders()),body);connection.close();return result
    def setup_data(self):return {'name':'Owner','email':'owner@example.test','business':'Acme','password':'long-enough-password','setup_token':'test-only-setup-token-32-characters'}
    def test_all_entrypoint_assets_are_served_with_expected_content_types(self):
        import re
        self.start()
        status,_,html=self.request('/')
        self.assertEqual(status,200)
        urls=re.findall(rb'(?:src|href)="(/[^"?#]+\.(?:js|css))"',html)
        self.assertIn(b'/interactions.js',urls)
        for url in urls:
            status,headers,body=self.request(url.decode())
            self.assertEqual(status,200,url)
            self.assertTrue(body,url)
            self.assertNotIn(b'<html',body[:100].lower(),url)
            self.assertIn('javascript' if url.endswith(b'.js') else 'text/css',headers['Content-Type'],url)
    def test_production_https_origin_sets_secure_cookie_and_headers(self):
        self.start();status,headers,_=self.request('/api/setup','POST',self.setup_data());self.assertEqual(status,200);self.assertIn('; Secure',headers['Set-Cookie']);self.assertIn('Strict-Transport-Security',headers)
    def test_first_owner_email_is_bound_without_disclosing_it_in_bootstrap(self):
        self.start(TW_PLATFORM_OWNER_EMAIL='owner@example.test')
        wrong=dict(self.setup_data(),email='other@example.test')
        self.assertEqual(self.request('/api/setup','POST',wrong)[0],403)
        self.assertFalse(self.server.store.initialized())
        self.assertNotIn(b'owner@example.test',self.request('/api/bootstrap')[2])
        self.assertEqual(self.request('/api/setup','POST',self.setup_data())[0],200)
    def test_unconfigured_host_and_wrong_origin_are_rejected(self):
        self.start();self.assertEqual(self.request('/',Host='evil.example')[0],403);self.assertEqual(self.request('/api/setup','POST',self.setup_data(),Origin='http://chat.example.test')[0],403)
    def test_platform_owner_email_uses_the_same_identity_comparison_as_login(self):
        self.start(TW_PLATFORM_OWNER_EMAIL='boss@example.test')
        payload=dict(self.setup_data(),email='bo\u00df@example.test')
        self.assertEqual(self.request('/api/setup','POST',payload)[0],403)
        self.assertFalse(self.server.store.initialized())
        payload['email']='BOSS@EXAMPLE.TEST'
        self.assertEqual(self.request('/api/setup','POST',payload)[0],200)
    def test_forwarded_headers_cannot_override_configured_origin(self):
        self.start();self.assertEqual(self.request('/api/setup','POST',self.setup_data(),Origin='https://evil.example',**{'X-Forwarded-Host':'chat.example.test','X-Forwarded-Proto':'https'})[0],403)
    def test_production_setup_requires_constant_server_token(self):
        self.start();payload=self.setup_data();payload.pop('setup_token');self.assertEqual(self.request('/api/setup','POST',payload)[0],403);self.assertFalse(self.server.store.initialized())
        status,_,body=self.request('/api/bootstrap');self.assertTrue(json.loads(body)['setup_token_required'])
    def test_health_is_coarse_and_readiness_verifies_database(self):
        self.start()
        for path in ['/healthz','/readyz']:
            status,_,body=self.request(path);self.assertEqual(status,200);self.assertNotIn(str(self.path).encode(),body);self.assertNotIn(b'token',body)
    def test_invalid_production_configuration_fails_before_listening(self):
        for origin in ['http://chat.example.test','https://user:pass@chat.example.test','https://@chat.example.test','https://chat.example.test/path','https://chat.example.test?x=y','https://chat.example.test#','']:
            with patch.dict(os.environ,{'TW_DEPLOYMENT':'production','TW_PUBLIC_ORIGIN':origin,'TW_SETUP_TOKEN':'test-only-setup-token-32-characters'}):
                with self.assertRaises(ValueError):make_server(0,self.path)
    def test_fresh_production_requires_setup_secret(self):
        for secret in ['', 'REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_32_CHARACTERS']:
            with patch.dict(os.environ,{'TW_DEPLOYMENT':'production','TW_PUBLIC_ORIGIN':'https://chat.example.test','TW_SETUP_TOKEN':secret}):
                with self.assertRaises(ValueError):make_server(0,self.path)
    def test_default_https_port_is_canonicalized_and_unicode_setup_is_rejected(self):
        self.start(TW_PUBLIC_ORIGIN='https://chat.example.test:443');payload=self.setup_data();payload['setup_token']='अ'*32
        self.assertEqual(self.request('/api/setup','POST',payload)[0],403)
        self.assertEqual(self.request('/api/setup','POST',self.setup_data())[0],200)
