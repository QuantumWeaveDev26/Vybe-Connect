"""Unpaid end-to-end agent checks; only the HTTP transport is simulated."""
import io,json,os,subprocess,tempfile,time,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class AgentAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'agents.db'
        self.env=patch.dict(os.environ,{'TW_PLATFORM_AI_MANAGED':'false','TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'unit-test-no-provider-key','TW_SEMANTIC_ENABLED':'false'})
        self.env.start();self.addCleanup(self.env.stop)
        self.s=Store(self.path);self.ctx=self.s.auth(self.s.setup('Owner','qa@example.test','isolated-qa-password','Synthetic QA')['token']);self.t=self.ctx['tenant_id']
        self.gate='TW_AI_'+self.t.upper()+'_ALLOW_PAID';self.approval=patch.dict(os.environ,{self.gate:'true'});self.approval.start();self.addCleanup(self.approval.stop)
        self.c=self.s.action(self.ctx,'contact.save',{'name':'Synthetic buyer','phone':'12025550146'})
        with self.s.db() as db:self.msg=self.s._message(db,self.t,self.c['id'],'Please share your opening hours.','in','received')
        self.agent=self.s.action(self.ctx,'aiagent.save',{'name':'Daily Digest','instructions':'Summarize recorded facts.','allowed_actions':['note']})

    def answer(self):
        return json.dumps({'summary':'Synthetic buyer asked for opening hours.','findings':[{'title':'Hours inquiry','details':'A customer asked for opening hours.','contact_id':self.c['id'],'evidence_ids':[self.msg['id']],'action':{'type':'note','body':'Review the hours inquiry.'}}]})

    def response(self):
        return io.BytesIO(json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':self.answer()}]}]}).encode())

    def test_every_preset_uses_real_adapter_schema_and_persists_review_only_findings(self):
        script="const fs=require('fs'),vm=require('vm');let c=vm.createContext({setInterval(){}});vm.runInContext(fs.readFileSync('static/assistant.js','utf8'),c);process.stdout.write(vm.runInContext('JSON.stringify(AGENT_PRESETS)',c))"
        presets=json.loads(subprocess.check_output(['node','-e',script],cwd=Path(__file__).resolve().parents[1],text=True));self.assertEqual(len(presets),12)
        for name,instructions in presets:
            with self.subTest(preset=name):
                agent=self.s.action(self.ctx,'aiagent.save',{'name':name,'instructions':instructions})
                with patch('openai_adapter.urllib.request.urlopen',return_value=self.response()) as http:
                    run=self.s.action(self.ctx,'ai.run',{'agent_id':agent['id']})
                request=http.call_args.args[0];payload=json.loads(request.data)
                self.assertEqual(request.full_url,'https://api.openai.com/v1/responses');self.assertEqual(http.call_count,1)
                self.assertEqual(payload['model'],'gpt-6-luna');self.assertFalse(payload['store'])
                self.assertTrue(payload['text']['format']['strict']);self.assertNotIn('tools',payload)
                self.assertIn(instructions,json.loads(payload['instructions'].split('Workspace facts: ',1)[1].split(' For business policy questions,',1)[0])['agent']['instructions'])
                self.assertEqual(run['status'],'completed');self.assertEqual(run['finding_count'],1)
                job=self.s.action(self.ctx,'ai.chat.start',{'question':'Summarize the latest inquiry.','agent_id':agent['id']})
                answer={'id':'resp_preset','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'answer':'A customer asked for opening hours.','references':[{'label':'Hours inquiry','contact_id':self.c['id'],'message_ids':[self.msg['id']]}],'knowledge_references':[]})}]}]}
                with patch('openai_background.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(answer).encode())) as http:
                    self.assertTrue(self.s.process_chat_job_once())
                payload=json.loads(http.call_args.args[0].data);self.assertTrue(payload['background']);self.assertEqual(http.call_count,1)
                with self.s.db() as db:self.assertEqual(self.s._get(db,self.t,'aijob',job['id'])['status'],'completed')
        state=self.s.state(self.ctx);self.assertEqual(len(state['findings']),12)
        self.assertTrue(all(f['status']=='pending' for f in state['findings']));self.assertEqual(len(state['messages']),1);self.assertEqual(state['queue'],[])
        self.assertEqual(len(state['aichats']),12);self.assertTrue(all(len(c['messages'])==2 for c in state['aichats']))

    def test_analysis_excludes_unsent_failed_and_simulated_evidence(self):
        with self.s.db() as db:
            for direction,status in [('out','draft'),('out','failed'),('out','unknown'),('in','simulated'),('note','note')]:self.s._message(db,self.t,self.c['id'],'UNSENT_PRIVATE_MARKER',direction,status)
        _,context=self.s._ai_context(self.ctx,{'agent_id':self.agent['id']})
        self.assertNotIn('UNSENT_PRIVATE_MARKER',json.dumps(context));self.assertEqual(context['recent_conversations'][0]['messages'][0]['id'],self.msg['id'])

    def test_scheduler_preserves_due_run_while_paused_or_allowance_empty(self):
        self.s.action(self.ctx,'aiagent.schedule',{'id':self.agent['id'],'enabled':True,'interval':3600})
        with self.s.db() as db:self.s._put(db,self.t,'aiagent',dict(self.agent,schedule_enabled=True,interval=3600,next_run=1,schedule_owner=self.ctx['user']['id']),self.agent['id'])
        for extra in ({'provider_pause':{'reason':'rate_limited','retry_after':60}},{'platform_managed':True,'allowance':{'active':True,'remaining':0}}):
            with patch('store.ai_status',return_value=dict(enabled=True,configured=True,requested_enabled=True,**extra)),patch('store.ask_local') as model:
                self.assertFalse(self.s.process_agent_schedule_once());model.assert_not_called()
        state=self.s.state(self.ctx);self.assertEqual(state['airuns'],[]);self.assertEqual(state['aiagents'][0]['next_run'],1)
        with patch('store.now',return_value=2000000000),patch('store.ask_local',return_value=self.answer()) as model:
            self.assertTrue(self.s.process_agent_schedule_once());self.assertEqual(model.call_count,1)

    def test_removed_runner_cannot_publish_late_findings(self):
        member=self.s.action(self.ctx,'member.add',{'name':'Runner','email':'runner@example.test','password':'isolated-runner-password','role':'agent'})
        runner=self.s.auth(self.s.login('runner@example.test','isolated-runner-password')['token'])
        def revoke(*args):
            self.s.action(self.ctx,'member.remove',{'id':member['id']});return self.answer()
        with patch('store.ask_local',side_effect=revoke):
            with self.assertRaises(Problem):self.s.action(runner,'ai.run',{'agent_id':self.agent['id']})
        state=self.s.state(self.ctx);self.assertEqual(state['findings'],[]);self.assertEqual(state['airuns'][-1]['status'],'interrupted')

    def test_large_workspace_agent_fits_subscription_input_before_reserving(self):
        for i in range(20):
            c=self.s.action(self.ctx,'contact.save',{'name':'Synthetic '+str(i),'phone':str(12025550200+i)})
            with self.s.db() as db:
                for j in range(3):self.s._message(db,self.t,c['id'],'Customer inquiry '+('x'*490),'in','received',ts=100+i*3+j)
        with self.s.db() as db:
            for i in range(8):self.s._put(db,self.t,'knowledge',{'title':'Policy '+str(i),'body':'Approved reference. '*300,'enabled':True})
            self.s._put(db,self.t,'servicejob',{'kind':'billing.subscription','created':1,'payload':{'plan_id':'plan_test','notes':{'plan_key':'qa'}},'result':{'provider_id':'sub_test','provider_status':'active','current_end':int(time.time())+3600}})
        config={self.gate:'false','TW_PLATFORM_AI_MANAGED':'true','TW_PLATFORM_AI_DB':str(self.path),'TW_BILLING_PLANS':json.dumps({'qa':{'name':'QA','plan_id':'plan_test','amount_minor':49900,'currency':'INR','interval':'monthly','ai_requests':5}})}
        with patch.dict(os.environ,config),patch('openai_adapter.urllib.request.urlopen',return_value=self.response()) as http:
            run=self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
        self.assertEqual(run['status'],'completed');self.assertEqual(http.call_count,1)
        self.assertLess(run['sample_contacts'],21);self.assertGreater(run['sample_contacts'],0)
        self.assertIn('input-size limits',run['scope'].lower())

    def test_provider_failures_do_not_retry_or_publish_dummy_findings(self):
        for result in ({'status':'incomplete','output':[]},{'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'Declined'}]}]},{'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'not json'}]}]}):
            with self.subTest(result=result['status']),patch('openai_adapter.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(result).encode())) as http:
                with self.assertRaises(Problem):self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
                self.assertEqual(http.call_count,1)
        with patch('openai_adapter.urllib.request.urlopen',side_effect=urllib.error.URLError('unavailable')) as http:
            with self.assertRaises(Problem):self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
            self.assertEqual(http.call_count,1)
        state=self.s.state(self.ctx);self.assertTrue(all(r['status']=='failed' for r in state['airuns']));self.assertEqual(state['findings'],[]);self.assertEqual(state['queue'],[])

    def test_removed_runner_cannot_start_using_old_context(self):
        member=self.s.action(self.ctx,'member.add',{'name':'Runner','email':'runner@example.test','password':'isolated-runner-password','role':'agent'})
        runner=self.s.auth(self.s.login('runner@example.test','isolated-runner-password')['token']);self.s.action(self.ctx,'member.remove',{'id':member['id']})
        with patch('store.ask_local') as model:
            with self.assertRaises(Problem):self.s.action(runner,'ai.run',{'agent_id':self.agent['id']})
            model.assert_not_called()

    def test_removed_chat_owner_cannot_publish_a_late_answer(self):
        member=self.s.action(self.ctx,'member.add',{'name':'Runner','email':'runner@example.test','password':'isolated-runner-password','role':'agent'})
        runner=self.s.auth(self.s.login('runner@example.test','isolated-runner-password')['token'])
        job=self.s.action(runner,'ai.chat.start',{'question':'Summarize the inquiry.'})
        def revoke(*args):
            self.s.action(self.ctx,'member.remove',{'id':member['id']})
            return {'id':'resp_revoked','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'answer':'Late answer','references':[],'knowledge_references':[]})}]}]}
        with patch('chat_jobs.openai_create',side_effect=revoke):self.assertTrue(self.s.process_chat_job_once())
        with self.s.db() as db:
            self.assertEqual(self.s._get(db,self.t,'aijob',job['id'])['status'],'failed')
            self.assertEqual(self.s._get(db,self.t,'aichat',job['chat_id'])['messages'],[])
