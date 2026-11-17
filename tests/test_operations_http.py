import http.client,json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from server import make_server


class OperationsHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=make_server(0,Path(self.tmp.name)/'http.db')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        store=self.server.store;owner=store.setup('Owner','owner@example.test','long-owner-password','Operations');self.owner=store.auth(owner['token']);self.owner_cookie='tw_session='+owner['token']
        self.agent=store.action(self.owner,'member.add',{'name':'Agent','email':'agent@example.test','password':'long-agent-password','role':'agent'})
        self.cookie='tw_session='+store.login('agent@example.test','long-agent-password')['token']
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,method='GET',data=None,cookie=None):
        port=self.server.server_address[1];c=http.client.HTTPConnection('127.0.0.1',port)
        headers={'Origin':'http://127.0.0.1:'+str(port),'Content-Type':'application/json','Cookie':cookie or self.cookie}
        c.request(method,path,json.dumps(data) if data is not None else None,headers)
        r=c.getresponse();raw=r.read();body=json.loads(raw) if 'application/json' in r.getheader('Content-Type','') else raw.decode();result=r.status,body;c.close();return result
    def save(self,**changes):
        store=self.server.store;p=next(m['permissions'] for m in store.state(self.owner)['members'] if m['id']==self.agent['id'])
        return self.request('/api/action','POST',{'action':'member.permissions','data':{'id':self.agent['id'],'version':p['version'],'permissions':{key:changes.get(key,True) for key in ('calling','reports','exports')}}},self.owner_cookie)
    def test_report_and_csv_recheck_current_permissions_with_same_cookie(self):
        path='/api/analytics?from=2026-11-01&to=2026-11-17'
        self.assertEqual(self.request(path)[0],200)
        code,body=self.request(path+'&export=csv');self.assertEqual(code,200);self.assertIn('section,date_or_operator',body['csv'])
        self.assertEqual(self.save(exports=False)[0],200)
        self.assertEqual(self.request(path)[0],200);self.assertEqual(self.request(path+'&export=csv')[0],403)
        self.assertEqual(self.save(reports=False)[0],200);self.assertEqual(self.request(path)[0],403)
        self.assertEqual(self.request('/api/export')[0],200) # export is separately controlled
    def test_call_permission_blocks_actions_and_redacts_history_without_provider(self):
        self.assertEqual(self.save(calling=False)[0],200)
        with patch('outbound_calls.remote') as provider:
            code,_=self.request('/api/action','POST',{'action':'calls.start','data':{'contact_id':'missing'}})
        self.assertEqual(code,403);provider.assert_not_called()
        code,body=self.request('/api/state');self.assertEqual(code,200);self.assertFalse(body['permissions']['calling']);self.assertEqual(body['calling']['calls'],[])
    def test_agent_cannot_change_own_permissions_or_forge_admin_role(self):
        code,_=self.request('/api/action','POST',{'action':'member.permissions','data':{'id':self.agent['id'],'role':'admin','version':0,'permissions':dict(calling=True,reports=True,exports=True)}})
        self.assertEqual(code,403)
