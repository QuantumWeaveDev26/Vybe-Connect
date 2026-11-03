import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class AgentBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'builder.db')
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.env=patch.dict(os.environ,{'TW_AI_PROVIDER':'openai','TW_AI_ENABLED':'true','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'test-only','TW_AI_'+self.ctx['tenant_id'].upper()+'_ALLOW_PAID':'true'});self.env.start()
        self.proposal={'summary':'Identify unresolved questions for human review.','name':'Question Watcher','instructions':'Review supplied conversations for unanswered questions. Propose follow-up tasks for human review.','cadence':'daily'}

    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def start(self,**data):return self.s.action(self.ctx,'ai.chat.start',dict(question='Create an agent that finds unanswered questions daily',purpose='agent_builder',**data))
    def response(self,proposal=None):return {'id':'resp_builder','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(self.proposal if proposal is None else proposal)}]}]}
    def generate(self):
        job=self.start()
        with patch('chat_jobs.openai_create_agent',return_value=self.response()):self.s.process_chat_job_once()
        state=self.s.state(self.ctx);message=state['aichats'][0]['messages'][-1];return job,message
    def install(self,job,message,**changes):return self.s.action(self.ctx,'ai.chat.install-agent',dict(chat_id=job['chat_id'],message_id=message['id'],name='Reviewed Watcher',instructions=self.proposal['instructions'],cadence='weekly',**changes))

    def test_generation_uses_real_transport_contract_and_does_not_install(self):
        job,message=self.generate();self.assertEqual(message['agent_draft'],self.proposal)
        self.assertEqual(self.s.state(self.ctx)['aiagents'],[]);self.assertEqual(self.s.state(self.ctx)['aijobs'][0]['status'],'completed')
        self.assertEqual(self.s.state(self.ctx)['aichats'][0]['purpose'],'agent_builder')

    def test_follow_up_refinement_receives_previous_proposal_without_private_metadata(self):
        job,message=self.generate()
        self.s.action(self.ctx,'ai.chat.start',{'question':'Make it weekly instead','chat_id':job['chat_id'],'purpose':'agent_builder'})
        with patch('chat_jobs.openai_create_agent',return_value=self.response(dict(self.proposal,cadence='weekly'))) as provider:self.s.process_chat_job_once()
        history=provider.call_args.args[-1];self.assertIn(self.proposal['instructions'],history[-1]['content'])
        self.assertTrue(all(set(m)=={'role','content'} for m in history))

    def test_review_install_is_paused_idempotent_and_does_not_call_ai(self):
        job,message=self.generate()
        with patch('chat_jobs.openai_create_agent') as provider:
            agent=self.install(job,message);again=self.install(job,message);provider.assert_not_called()
        self.assertEqual(agent['id'],again['id']);self.assertEqual(agent['name'],'Reviewed Watcher')
        self.assertEqual(agent['mode'],'review_first');self.assertFalse(agent['schedule_enabled']);self.assertEqual(agent['interval'],604800)
        self.assertEqual(len(self.s.state(self.ctx)['aiagents']),1)

    def test_invalid_output_and_unknown_tools_are_not_publishable(self):
        for proposal in [dict(self.proposal,cadence='each_second'),dict(self.proposal,tools=['send_whatsapp'])]:
            job=self.start()
            with patch('chat_jobs.openai_create_agent',return_value=self.response(proposal)):self.s.process_chat_job_once()
            state=self.s.state(self.ctx);self.assertEqual(next(j for j in state['aijobs'] if j['id']==job['id'])['status'],'failed')
        self.assertFalse(self.s.state(self.ctx)['aiagents']);self.assertTrue(all(not c['messages'] for c in self.s.state(self.ctx)['aichats']))

    def test_builder_chat_purpose_and_agent_identity_cannot_change(self):
        job=self.start()
        with self.assertRaises(Problem):self.s.action(self.ctx,'ai.chat.start',{'question':'Summarize','chat_id':job['chat_id']})
        with self.assertRaises(Problem):self.start(agent_id='unrelated-agent')

    def test_private_proposal_cannot_be_installed_from_another_workspace(self):
        job,message=self.generate();other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        with self.assertRaises(Problem):self.s.action(other,'ai.chat.install-agent',{'chat_id':job['chat_id'],'message_id':message['id'],**self.proposal})
        self.assertFalse(self.s.state(self.ctx)['aiagents'])

    def test_another_administrator_cannot_apply_private_proposal(self):
        job,message=self.generate()
        self.s.action(self.ctx,'member.add',{'name':'Other Admin','email':'other@example.test','password':'another-long-password','role':'admin'})
        other=self.s.auth(self.s.login('other@example.test','another-long-password')['token'])
        with self.assertRaises(Problem):self.s.action(other,'ai.chat.install-agent',{'chat_id':job['chat_id'],'message_id':message['id'],**self.proposal})
        self.assertFalse(self.s.state(other)['aichats']);self.assertFalse(self.s.state(self.ctx)['aiagents'])

    def test_concurrent_install_creates_one_agent(self):
        from concurrent.futures import ThreadPoolExecutor
        job,message=self.generate()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.install(job,message),range(2)))
        self.assertEqual(results[0]['id'],results[1]['id']);self.assertEqual(len(self.s.state(self.ctx)['aiagents']),1)

    def test_builder_obeys_paid_gate_and_supports_structured_local_output(self):
        with patch.dict(os.environ,{'TW_AI_'+self.ctx['tenant_id'].upper()+'_ALLOW_PAID':'false'}):
            with self.assertRaises(Problem):self.start()
        with patch.dict(os.environ,{'TW_AI_PROVIDER':'ollama'}):
            job=self.start()
            with patch('chat_jobs.ask_local',return_value=json.dumps(self.proposal)) as local:self.s.process_chat_job_once()
            self.assertTrue(local.call_args.args[1]['_agent_builder'])
        message=self.s.state(self.ctx)['aichats'][0]['messages'][-1];self.assertEqual(message['agent_draft'],self.proposal)

    def test_membership_demotion_prevents_queued_builder_execution_and_install(self):
        job,message=self.generate();queued=self.start()
        with self.s.db() as db:db.execute("UPDATE members SET role='agent' WHERE tenant=? AND user=?",(self.ctx['tenant_id'],self.ctx['user']['id']))
        demoted=self.s.auth(self.token)
        with self.assertRaises(Problem):self.s.action(demoted,'ai.chat.start',{'question':'Create agent','purpose':'agent_builder'})
        with self.assertRaises(Problem):self.s.action(demoted,'ai.chat.install-agent',{'chat_id':job['chat_id'],'message_id':message['id'],**self.proposal})
        with patch('chat_jobs.openai_create_agent') as provider:self.s.process_chat_job_once();provider.assert_not_called()
        self.assertEqual(next(j for j in self.s.state(demoted)['aijobs'] if j['id']==queued['id'])['status'],'failed')

    def test_openai_builder_uses_strict_schema_and_has_no_tools(self):
        from openai_background import openai_create_agent
        with patch('openai_background.urllib.request.urlopen',return_value=io.BytesIO(b'{"id":"resp_builder","status":"queued"}')) as call:
            openai_create_agent('test-only','gpt-6-luna','Business: Acme','Create watcher',[])
        payload=json.loads(call.call_args.args[0].data);self.assertTrue(payload['background']);self.assertFalse(payload['store']);self.assertNotIn('tools',payload)
        schema=payload['text']['format']['schema'];self.assertFalse(schema['additionalProperties']);self.assertEqual(set(schema['required']),set(self.proposal))
