import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from server import make_server
from client_services import platform_admin


class PublicSignupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Store(Path(self.temp.name)/'signup.db')
        self.owner=self.s.auth(self.s.setup('Owner','operator@example.test','owner-test-password','Operator')['token'])
        self.env=patch.dict(os.environ,{'TW_PUBLIC_SIGNUP':'true','TW_PLATFORM_OWNER_EMAIL':'operator@example.test'});self.env.start()

    def tearDown(self):self.env.stop();self.temp.cleanup()

    def signup(self,email='business@example.test',**options):
        return self.s.signup('Business Owner',email,'new-business-password','New Business',**options)

    def test_signup_creates_an_isolated_business_and_no_platform_privileges(self):
        contact=self.s.action(self.owner,'contact.save',{'name':'Private owner contact','phone':'919000000001'})
        result=self.signup();ctx=self.s.auth(result['token']);state=self.s.state(ctx)
        self.assertEqual(ctx['role'],'admin');self.assertNotEqual(ctx['tenant_id'],self.owner['tenant_id'])
        self.assertEqual(ctx['workspace']['name'],'New Business');self.assertEqual(state['contacts'],[])
        self.assertEqual(len(ctx['workspaces']),1);self.assertFalse(platform_admin(ctx))
        with self.assertRaises(Problem):self.s.auth(result['token'],self.owner['tenant_id'])
        with self.s.db() as db:
            with self.assertRaises(Problem):self.s._get(db,ctx['tenant_id'],'contact',contact['id'])
            user=db.execute('SELECT password FROM users WHERE id=?',(ctx['user']['id'],)).fetchone()
            self.assertNotEqual(user['password'],'new-business-password')

    def test_signup_does_not_replace_an_existing_email_or_create_extra_workspaces(self):
        self.signup()
        with self.assertRaises(Problem) as duplicate:self.signup(' BUSINESS@EXAMPLE.TEST ')
        self.assertEqual(duplicate.exception.code,409)
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM tenants').fetchone()[0],2)
        self.s.login('business@example.test','new-business-password')

    def test_unicode_lookalike_email_cannot_gain_platform_operator_privileges(self):
        with patch.dict(os.environ,{'TW_PLATFORM_OWNER_EMAIL':'boss@example.test'}):
            result=self.signup('bo\u00df@example.test');ctx=self.s.auth(result['token'])
            self.assertFalse(platform_admin(ctx))
            with self.assertRaises(Problem):self.s.action(ctx,'clients.create',{'name':'Unauthorized client','email':'target@example.test'})

    def test_unclaimed_operator_email_is_reserved_for_initial_setup(self):
        with patch.dict(os.environ,{'TW_PLATFORM_OWNER_EMAIL':'reserved@example.test'}):
            with self.assertRaises(Problem):self.signup('reserved@example.test')
            customer=self.s.auth(self.signup()['token'])
            with self.assertRaises(Problem):self.s.action(customer,'member.add',{'name':'Reserved','email':'RESERVED@example.test','password':'reserved-test-password','role':'admin'})

    def test_disabled_signup_and_uninitialized_deployments_cannot_be_claimed(self):
        with patch.dict(os.environ,{'TW_PUBLIC_SIGNUP':'false'}),self.assertRaises(Problem):self.signup()
        fresh=Store(Path(self.temp.name)/'fresh.db')
        with self.assertRaises(Problem):fresh.signup('Unknown','unknown@example.test','new-business-password','Unknown')
        self.assertFalse(fresh.initialized())

    def test_failed_validation_rolls_back_both_user_and_workspace(self):
        for email,password,business in [('bad-email','new-business-password','New'),('valid@example.test','short','New'),('valid@example.test','new-business-password','')]:
            with self.assertRaises(Problem):self.s.signup('New',email,password,business)
        with self.s.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM tenants').fetchone()[0],1)

    def test_remembered_session_has_matching_expiry_and_logout_revokes_it(self):
        with patch('store.now',return_value=1000):result=self.signup(remember=True)
        self.assertEqual(result['max_age'],2592000)
        with self.s.db() as db:
            expiry=db.execute('SELECT expires FROM sessions WHERE token=?',(hashlib.sha256(result['token'].encode()).hexdigest(),)).fetchone()[0]
        self.assertEqual(expiry,1000+2592000)
        with patch('store.now',return_value=1001):self.s.auth(result['token'])
        self.s.logout(result['token'])
        with patch('store.now',return_value=1001),self.assertRaises(Problem):self.s.auth(result['token'])

    def test_login_remember_is_explicit_and_password_change_revokes_it(self):
        self.signup()
        normal=self.s.login('business@example.test','new-business-password')
        remembered=self.s.login('business@example.test','new-business-password',remember=True)
        self.assertEqual(normal['max_age'],43200);self.assertEqual(remembered['max_age'],2592000)
        self.s.change_password(self.s.auth(remembered['token']),'new-business-password','replacement-business-password')
        with self.assertRaises(Problem):self.s.auth(remembered['token'])


class PublicSignupHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'http.db'
        Store(self.path).setup('Operator','operator@example.test','owner-test-password','Operator')
        self.env=patch.dict(os.environ,{'TW_DEPLOYMENT':'production','TW_PUBLIC_ORIGIN':'https://chat.example.test','TW_BIND':'127.0.0.1','TW_PUBLIC_SIGNUP':'true','TW_PLATFORM_OWNER_EMAIL':'operator@example.test'});self.env.start()
        self.server=make_server(0,self.path);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.env.stop();self.temp.cleanup()

    def request(self,path,data=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_address[1]);h={'Host':'chat.example.test','Origin':'https://chat.example.test','Content-Type':'application/json'};h.update(headers or {})
        c.request('POST' if data is not None else 'GET',path,json.dumps(data).encode() if data is not None else None,h)
        r=c.getresponse();result=r.status,dict(r.getheaders()),r.read();c.close();return result

    def data(self):return {'name':'Customer','business':'Customer business','email':'customer@example.test','password':'customer-test-password','remember':True,'tenant_id':'forged-owner-workspace','role':'platform_admin'}

    def test_public_signup_accepts_other_emails_and_sets_a_secure_remembered_session(self):
        code,_,body=self.request('/api/bootstrap');self.assertEqual(code,200);self.assertTrue(json.loads(body)['signup_available'])
        code,headers,body=self.request('/api/signup',self.data());self.assertEqual(code,200,body)
        cookie=headers['Set-Cookie'];self.assertIn('Max-Age=2592000',cookie);self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie);self.assertIn('; Secure',cookie)
        self.assertNotIn('token',json.loads(body))
        code,_,body=self.request('/api/state',headers={'Cookie':cookie.split(';')[0]});state=json.loads(body)
        self.assertEqual(code,200);self.assertEqual(state['context']['user']['email'],'customer@example.test')
        self.assertEqual(state['context']['role'],'admin');self.assertFalse(state['services']['platform_admin'])
        self.assertNotEqual(state['context']['tenant_id'],'forged-owner-workspace')
        self.request('/api/logout',{},headers={'Cookie':cookie.split(';')[0]})
        self.assertEqual(self.request('/api/state',headers={'Cookie':cookie.split(';')[0]})[0],401)

    def test_signup_is_origin_checked_gated_and_rate_limited(self):
        self.assertEqual(self.request('/api/signup',self.data(),{'Origin':'https://evil.example'})[0],403)
        with patch.dict(os.environ,{'TW_PUBLIC_SIGNUP':'false'}):self.assertEqual(self.request('/api/signup',self.data())[0],403)
        with patch('server.auth_attempt',return_value=False):self.assertEqual(self.request('/api/signup',self.data())[0],429)

    def test_string_false_does_not_request_a_persistent_login(self):
        data=self.data();data['remember']='false';code,headers,body=self.request('/api/signup',data)
        self.assertEqual(code,200,body);self.assertIn('Max-Age=43200',headers['Set-Cookie'])
