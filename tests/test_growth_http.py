import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode
from server import make_server


class GrowthHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=make_server(0,Path(self.tmp.name)/'http.db')
        token=self.server.store.setup('Owner','http@growth.test','long-test-password','Growth HTTP')['token'];self.ctx=self.server.store.auth(token)
        self.cookie='tw_session='+token;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.port=self.server.server_address[1]
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port)
        opts={'Origin':'http://127.0.0.1:'+str(self.port),'Content-Type':'application/json'};opts.update(headers or {})
        conn.request(method,path,body,opts);r=conn.getresponse();result=r.status,dict(r.getheaders()),r.read();conn.close();return result
    def test_growth_actions_require_session_and_same_origin(self):
        raw=json.dumps({'action':'growth.branch.save','data':{'name':'Branch','members':[]}})
        self.assertEqual(self.request('POST','/api/action',raw)[0],401)
        self.assertEqual(self.request('POST','/api/action',raw,{'Cookie':self.cookie,'Origin':'https://wrong.test'})[0],403)
        self.assertEqual(self.request('POST','/api/action',raw,{'Cookie':self.cookie})[0],200)
    def test_recipe_bearer_ingress_without_browser_cookie_and_no_source_exposure(self):
        r=self.server.store.action(self.ctx,'growth.recipe.save',{'name':'HTTP','mode':'contact','mapping':{'phone':'phone'},'enabled':True})
        raw=json.dumps({'phone':'919000000004','name':'HTTP customer'})
        path='/recipe-hook/'+r['id'];headers={'Origin':'https://automation.test','Authorization':'Bearer '+r['secret'],'X-Event-ID':'evt-1'}
        self.assertEqual(self.request('POST',path,raw,headers)[0],200)
        self.assertTrue(json.loads(self.request('POST',path,raw,headers)[2])['duplicate'])
        self.assertEqual(self.request('POST',path,raw,{'X-Event-ID':'evt-2'})[0],403)
        for p in ['/growth_services.py','/whatsapp_forms.py']:
            self.assertEqual(self.request('GET',p)[0],404)
        for p in ['/growth.js','/growth.css']:self.assertEqual(self.request('GET',p)[0],200)
    def test_public_help_and_survey_work_without_login(self):
        s=self.server.store;t=self.ctx['tenant_id']
        article=s.action(self.ctx,'growth.article.save',{'title':'Public help','slug':'help','body':'Safe answer','published':True,'confirm_public':True})
        code,headers,body=self.request('GET','/help/'+t+'/help');self.assertEqual(code,200);self.assertIn(b'Safe answer',body);self.assertIn('no-store',headers['Cache-Control'])
        c=s.action(self.ctx,'contact.save',{'name':'Customer','phone':'919000000005'})
        survey=s.action(self.ctx,'growth.survey.create',{'contact_id':c['id']});path='/survey/'+survey['token']
        self.assertEqual(self.request('GET',path)[0],200)
        raw=urlencode({'rating':'4','comment':'Helpful'})
        self.assertEqual(self.request('POST',path,raw,{'Content-Type':'application/x-www-form-urlencoded'})[0],200)
        self.assertEqual(self.request('POST',path,raw,{'Content-Type':'application/x-www-form-urlencoded'})[0],409)
        self.assertEqual(self.request('GET','/help/'+t+'/private')[0],404)
