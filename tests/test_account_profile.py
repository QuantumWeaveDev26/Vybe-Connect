import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from server import make_server
from store import Store,Problem


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'profile.db';self.store=Store(self.path)
        self.token=self.store.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.store.auth(self.token)

    def tearDown(self):self.tmp.cleanup()

    def test_name_persists_across_login_and_preserves_credentials_and_memberships(self):
        tenant=self.store.action(self.ctx,'workspace.create',{'name':'Other'})['id']
        result=self.store.update_profile(self.ctx,{'name':'  New Display Name  '})
        self.assertEqual(result['name'],'New Display Name')
        self.assertEqual(self.store.auth(self.token,tenant)['user']['name'],'New Display Name')
        login=self.store.login('owner@example.test','long-enough-password')
        self.assertEqual(self.store.auth(login['token'])['user']['email'],'owner@example.test')
        self.assertEqual(self.store.auth(self.token)['role'],'admin')
        self.assertEqual(Store(self.path).auth(self.token)['user']['name'],'New Display Name')

    def test_invalid_names_and_unrelated_fields_do_not_mutate_account(self):
        for data in [{'name':''},{'name':'x'*101},{'name':'Bad\nName'},{'name':'Valid','email':'other@example.test'},{'name':'Valid','id':'other'}]:
            with self.subTest(data=data),self.assertRaises(Problem):self.store.update_profile(self.ctx,data)
        self.assertEqual(self.store.auth(self.token)['user']['name'],'Owner')

    def test_update_cannot_modify_another_user(self):
        member=self.store.action(self.ctx,'member.add',{'name':'Teammate','email':'team@example.test','password':'another-long-password','role':'agent'})
        self.store.update_profile(self.ctx,{'name':'Changed'})
        other=self.store.auth(self.store.login('team@example.test','another-long-password')['token'])
        self.assertEqual(other['user']['name'],'Teammate')


class ProfileHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=make_server(0,Path(self.tmp.name)/'http.db');self.port=self.server.server_address[1]
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.token=self.server.store.setup('Owner','owner@example.test','long-enough-password','Acme')['token']

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()

    def request(self,data,cookie=True,origin=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.port)
        headers={'Content-Type':'application/json','Origin':origin or 'http://127.0.0.1:'+str(self.port)}
        if cookie:headers['Cookie']='tw_session='+self.token
        connection.request('POST','/api/account/profile',json.dumps(data),headers);response=connection.getresponse();body=json.loads(response.read());code=response.status;connection.close();return code,body

    def test_profile_requires_session_and_same_origin(self):
        self.assertEqual(self.request({'name':'Updated'},cookie=False)[0],401)
        self.assertEqual(self.request({'name':'Updated'},origin='https://evil.example')[0],403)
        self.assertEqual(self.request({'name':'Updated','role':'admin'})[0],400)

    def test_authenticated_update_returns_only_public_profile(self):
        code,result=self.request({'name':'Updated'})
        self.assertEqual(code,200);self.assertEqual(set(result),{'id','name','email'})
        self.assertEqual(result['name'],'Updated')
