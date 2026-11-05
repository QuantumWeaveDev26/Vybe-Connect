import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from server import make_server


class PublicAPIHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=make_server(0,Path(self.tmp.name)/'http.db')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        result=self.server.store.setup('Owner','api-http@example.test','a-long-enough-password','API review')
        self.cookie='tw_session='+result['token'];self.ctx=self.server.store.auth(result['token'])
        self.server.store.action(self.ctx,'contact.save',{'name':'Private API contact','phone':'919000000001'})
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,method='GET',data=None,headers=None):
        port=self.server.server_address[1];connection=http.client.HTTPConnection('127.0.0.1',port)
        h={'Origin':'http://127.0.0.1:'+str(port),'Content-Type':'application/json',**(headers or {})}
        connection.request(method,path,json.dumps(data) if data is not None else None,h)
        response=connection.getresponse();body=response.read();result=response.status,dict(response.getheaders()),json.loads(body);connection.close();return result
    def create(self):
        code,_,result=self.request('/api/developer/tokens','POST',{'name':'Read integration','scopes':['contacts:read'],'days':7},{'Cookie':self.cookie})
        self.assertEqual(code,200);return result
    def test_cookie_management_and_bearer_only_resource(self):
        self.assertEqual(self.request('/api/developer/tokens')[0],401)
        token=self.create()
        self.assertEqual(self.request('/api/v1/contacts',headers={'Cookie':self.cookie})[0],401)
        code,headers,body=self.request('/api/v1/contacts',headers={'Authorization':'Bearer '+token['token']})
        self.assertEqual(code,200);self.assertEqual(body['data'][0]['name'],'Private API contact')
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertNotIn(token['token'],json.dumps(self.request('/api/developer/tokens',headers={'Cookie':self.cookie})[2]))
        self.assertNotIn(token['token'],json.dumps(self.request('/api/state',headers={'Cookie':self.cookie})[2]))
        self.assertEqual(self.request('/api/developer/tokens/revoke','POST',{'id':token['id']},{'Cookie':self.cookie})[0],200)
        self.assertEqual(self.request('/api/v1/contacts',headers={'Authorization':'Bearer '+token['token']})[0],401)
    def test_csrf_scope_workspace_and_input_guards(self):
        self.assertEqual(self.request('/api/developer/tokens','POST',{}, {'Cookie':self.cookie,'Origin':'https://other.example'})[0],403)
        self.assertEqual(self.request('/api/developer/tokens','POST',[], {'Cookie':self.cookie})[0],400)
        token=self.create();bearer={'Authorization':'Bearer '+token['token']}
        self.assertEqual(self.request('/api/v1/messages',headers=bearer)[0],403)
        self.assertEqual(self.request('/api/v1/contacts?limit=0',headers=bearer)[0],400)
        self.assertEqual(self.request('/api/v1/contacts?workspace=other',headers=bearer)[0],403)
        self.assertEqual(self.request('/api/v1/send',headers=bearer)[0],404)
        self.assertEqual(self.request('/api/v1/contacts?token='+token['token'])[0],401)
