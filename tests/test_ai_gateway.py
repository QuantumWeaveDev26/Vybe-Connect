import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai import ai_status,ask_local,openai_key
from store import Store,Problem
import ai_gateway


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.catalog={'budget':{'label':'Budget AI','base_url':'https://gateway.example.test/v1','models':['approved-model'],'requests_per_day':2}}
        self.env=patch.dict(os.environ,{'TW_DATA_DIR':self.tmp.name,'TW_AI_GATEWAYS':json.dumps(self.catalog),'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_OPENAI_API_KEY':'platform-secret'})
        self.env.start();self.addCleanup(self.env.stop)
        self.s=Store(Path(self.tmp.name)/'test.db');token=self.s.setup('Owner','owner@gateway.test','long-test-password','Acme')['token'];self.ctx=self.s.auth(token);self.t=self.ctx['tenant_id']
        self.network=patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('No live gateway tests'));self.network.start();self.addCleanup(self.network.stop)
    def save(self,enabled=False,**change):return self.s.action(self.ctx,'ai.connection.save',dict({'provider':'gateway','gateway_id':'budget','key':'sk-gateway-private-1234567890','model':'approved-model','enabled':enabled},**change))
    def context(self):return {'_workspace_id':self.t,'_gateway_path':str(self.s.path),'business':'Acme','knowledge_sources':[]}
    def response(self,text='Answer'):
        return io.BytesIO(json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':text}]}],'usage':{'input_tokens':20,'output_tokens':3}}).encode())
    def test_catalog_fail_closed_and_no_tenant_endpoints(self):
        for url in ['http://gateway.test/v1','https://user:secret@gateway.test/v1','https://gateway.test/v1?x=1','https://gateway.test:8443/v1','https://gateway.test/']:
            c={'bad':dict(self.catalog['budget'],base_url=url)}
            with patch.dict(os.environ,{'TW_AI_GATEWAYS':json.dumps(c)}):self.assertEqual(ai_gateway.catalog(),{})
        with self.assertRaises(Problem):self.save(gateway_id='unapproved')
        with self.assertRaises(Problem):self.save(model='other-model')
    def test_saving_paused_is_private_and_does_not_call_any_provider(self):
        a=self.save();self.assertTrue(a['configured']);self.assertFalse(a['enabled']);self.assertEqual(a['provider_id'],'gateway')
        self.assertEqual(openai_key(self.t),'')
        with self.assertRaises(ValueError):ask_local('Hi',self.context(),[])
        state=json.dumps(self.s.state(self.ctx));self.assertNotIn('sk-gateway-private',state);self.assertNotIn('gateway.example.test',state)
        with patch.dict(os.environ,{'TW_AI_GATEWAYS':'{}'}):self.assertFalse(ai_status(self.t)['configured'])
    def test_responses_transport_structured_output_usage_and_daily_cap(self):
        self.save(True)
        with patch('urllib.request.OpenerDirector.open',side_effect=lambda *a,**k:self.response()) as mock:
            self.assertEqual(ask_local('Hi',self.context(),[]),'Answer');self.assertEqual(ask_local('Hi again',dict(self.context(),analysis_contract=True),[]),'Answer')
            with self.assertRaisesRegex(ValueError,'daily'):ask_local('Over cap',self.context(),[])
            self.assertEqual(mock.call_count,2)
            req=mock.call_args.args[0];self.assertEqual(req.full_url,'https://gateway.example.test/v1/responses');payload=json.loads(req.data);self.assertFalse(payload['background']);self.assertFalse(payload['store']);self.assertTrue(payload['text']['format']['strict'])
        usage=self.s.state(self.ctx)['gateway_usage'];self.assertEqual(usage['requests'],2);self.assertEqual(usage['input_tokens'],40)
    def test_uncertain_response_consumes_quota_and_does_not_retry(self):
        self.save(True)
        with patch('urllib.request.OpenerDirector.open',side_effect=TimeoutError('private-key-must-not-leak')) as mock:
            with self.assertRaises(ValueError) as e:ask_local('Hi',self.context(),[])
            self.assertNotIn('private-key',str(e.exception));self.assertEqual(mock.call_count,1)
        with self.s.db() as db:self.assertEqual(db.execute('SELECT status FROM ai_gateway_requests').fetchone()[0],'unknown')
    def test_workspace_quota_isolation(self):
        self.save(True)
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'});other_ctx=dict(self.ctx,tenant_id=other['id'])
        self.assertNotEqual(ai_status(other['id'])['provider_id'],'gateway')
        with self.s.db() as db:self.assertEqual(ai_gateway.usage(self.s,db,other['id'])['requests'],0)
    def test_chat_worker_uses_gateway_without_background_openai_requests(self):
        self.save(True);job=self.s.action(self.ctx,'ai.chat.start',{'question':'Summarize'})
        with patch('urllib.request.OpenerDirector.open',side_effect=lambda *a,**k:self.response(json.dumps({'answer':'No conversations yet.','references':[]}))) as mock,patch('chat_jobs.openai_create',side_effect=AssertionError('No direct OpenAI calls')):
            self.assertTrue(self.s.process_chat_job_once());self.assertEqual(mock.call_count,1)
        state=self.s.state(self.ctx);current=next(j for j in state['aijobs'] if j['id']==job['id']);self.assertEqual(current['status'],'completed')
    def test_provider_switch_needs_new_key_and_inflight_connection_is_preserved(self):
        self.s.action(self.ctx,'ai.connection.save',{'key':'sk-'+'a'*40,'model':'model','enabled':False})
        with self.assertRaises(Problem):self.save(key='')
        self.save(True)
        with self.s.db() as db:self.s._put(db,self.t,'aijob',{'provider':'gateway','status':'running'})
        with self.assertRaises(Problem):self.s.action(self.ctx,'ai.connection.disconnect',{})
        self.s.action(self.ctx,'ai.connection.pause',{});self.assertFalse(ai_status(self.t)['enabled'])


if __name__=='__main__':unittest.main()
