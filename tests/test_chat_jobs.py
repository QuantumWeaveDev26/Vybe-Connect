import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store, Problem


class ChatJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'jobs.db';self.s=Store(self.path)
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.env=patch.dict(os.environ,{'TW_AI_PROVIDER':'openai','TW_AI_ENABLED':'true','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'unit-test-placeholder','TW_AI_'+self.ctx['tenant_id'].upper()+'_ALLOW_PAID':'true'});self.env.start()
        self.clock=patch('chat_jobs.now',return_value=2000000000);self.clock.start()
        self.c=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001'})
        with self.s.db() as db:self.m=self.s._message(db,self.ctx['tenant_id'],self.c['id'],'Pricing please','in','received')

    def tearDown(self):self.clock.stop();self.env.stop();self.tmp.cleanup()

    def start(self,**kw):return self.s.action(self.ctx,'ai.chat.start',dict({'question':'Summarize the inbox'},**kw))
    def response(self,answer='Buyer asks for pricing.',references=None):
        return {'id':'resp_test1','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'answer':answer,'references':references if references is not None else [{'label':'Pricing inquiry','contact_id':self.c['id'],'message_ids':[self.m['id']]}]})}]}]}
    def advance(self):self.clock.stop();self.clock=patch('chat_jobs.now',return_value=2000000010);self.clock.start()

    def test_known_openai_rejection_is_failed_without_resubmission(self):
        from openai_errors import OpenAIRequestError
        job=self.start()
        with patch('chat_jobs.openai_create',side_effect=OpenAIRequestError('Quota exhausted',429,'quota_exhausted')) as provider:
            self.assertTrue(self.s.process_chat_job_once())
            self.assertFalse(self.s.process_chat_job_once())
        with self.s.db() as db:result=self.s._get(db,self.ctx['tenant_id'],'aijob',job['id'])
        self.assertEqual(result['status'],'failed');self.assertEqual(provider.call_count,1)

    def test_cooldown_is_not_recorded_as_a_submitted_unknown_request(self):
        from openai_errors import OpenAIRequestError
        job=self.start()
        with patch('openai_errors.ensure_available',side_effect=OpenAIRequestError('Paused',429,'rate_limited')),patch('chat_jobs.openai_create') as provider:
            self.assertTrue(self.s.process_chat_job_once())
        with self.s.db() as db:result=self.s._get(db,self.ctx['tenant_id'],'aijob',job['id'])
        self.assertEqual(result['status'],'failed');self.assertFalse(result.get('submitted'));provider.assert_not_called()

    def test_queued_cancel_does_not_call_provider(self):
        job=self.start();self.s.action(self.ctx,'ai.chat.cancel',{'chat_id':job['chat_id']})
        with patch('chat_jobs.openai_create') as provider:self.assertFalse(self.s.process_chat_job_once());provider.assert_not_called()
        self.assertEqual(self.s.state(self.ctx)['aijobs'][0]['status'],'cancelled')

    def test_prompt_accepts_observed_eight_thousand_character_limit(self):
        job=self.start(question='a'*8000)
        self.assertEqual(job['status'],'queued')
        with self.assertRaises(Problem):self.start(question='a'*8001)

    def test_provider_id_survives_restart_and_completion_has_validated_references(self):
        job=self.start()
        with patch('chat_jobs.openai_create',return_value={'id':'resp_test1','status':'in_progress'}) as create:self.assertTrue(self.s.process_chat_job_once())
        self.advance();restarted=Store(self.path)
        with patch('chat_jobs.openai_create') as no_create,patch('chat_jobs.openai_retrieve',return_value=self.response()):self.assertTrue(restarted.process_chat_job_once());no_create.assert_not_called()
        state=restarted.state(self.ctx);self.assertEqual(create.call_count,1)
        self.assertEqual(state['aijobs'][0]['status'],'completed')
        message=state['aichats'][0]['messages'][-1]
        self.assertEqual(message['references'][0]['contact_id'],self.c['id']);self.assertTrue(message['id'])
        self.assertEqual(state['queue'],[])

    def test_stop_after_submission_calls_real_cancel_contract(self):
        job=self.start()
        with patch('chat_jobs.openai_create',return_value={'id':'resp_test1','status':'in_progress'}):self.s.process_chat_job_once()
        self.s.action(self.ctx,'ai.chat.cancel',{'chat_id':job['chat_id']})
        with patch('chat_jobs.openai_cancel',return_value={'id':'resp_test1','status':'cancelled'}) as cancel:self.assertTrue(self.s.process_chat_job_once())
        self.assertEqual(cancel.call_args.args[-1],'resp_test1')
        self.assertEqual(self.s.state(self.ctx)['aijobs'][0]['cancel_outcome'],'provider_cancelled')
        self.assertEqual(self.s.state(self.ctx)['aichats'][0]['messages'],[])

    def test_append_waits_for_prior_chat_job_and_uses_completed_history(self):
        first=self.start();self.start(chat_id=first['chat_id'],question='What next?')
        with patch('chat_jobs.openai_create',return_value={'id':'resp_test1','status':'in_progress'}) as create:
            self.s.process_chat_job_once();self.assertFalse(self.s.process_chat_job_once());self.assertEqual(create.call_count,1)
        self.advance()
        with patch('chat_jobs.openai_retrieve',return_value=self.response()):self.s.process_chat_job_once()
        with patch('chat_jobs.openai_create',return_value=self.response('Next step.',[])) as create:self.s.process_chat_job_once()
        self.assertEqual(len(create.call_args.args[4]),2)
        self.assertEqual(len(self.s.state(self.ctx)['aichats'][0]['messages']),4)

    def test_private_jobs_and_feedback_cannot_cross_user_or_workspace(self):
        job=self.start()
        with patch('chat_jobs.openai_create',return_value=self.response()):self.s.process_chat_job_once()
        message=self.s.state(self.ctx)['aichats'][0]['messages'][-1]
        self.s.action(self.ctx,'ai.chat.feedback',{'chat_id':job['chat_id'],'message_id':message['id'],'rating':'helpful'})
        self.assertEqual(self.s.state(self.ctx)['aichats'][0]['messages'][-1]['rating'],'helpful')
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'another-long-password','role':'agent'})
        agent=self.s.auth(self.s.login('agent@example.test','another-long-password')['token'])
        self.assertEqual(self.s.state(agent)['aijobs'],[])
        for action,data in [('ai.chat.cancel',{'chat_id':job['chat_id']}),('ai.chat.feedback',{'chat_id':job['chat_id'],'message_id':message['id'],'rating':'helpful'})]:
            with self.assertRaises(Problem):self.s.action(agent,action,data)
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        with self.assertRaises(Problem):self.s.action(other,'ai.chat.cancel',{'chat_id':job['chat_id']})

    def test_uncertain_create_is_not_automatically_retried(self):
        self.start()
        with patch('chat_jobs.openai_create',side_effect=ValueError('Provider create outcome uncertain')) as create:
            self.s.process_chat_job_once();self.assertFalse(self.s.process_chat_job_once());self.assertEqual(create.call_count,1)
        self.assertEqual(self.s.state(self.ctx)['aijobs'][0]['status'],'unknown')

    def test_invalid_citations_or_changed_history_do_not_publish_answer(self):
        self.start()
        with patch('chat_jobs.openai_create',return_value=self.response(references=[{'label':'Wrong','contact_id':'foreign','message_ids':[]}])):self.s.process_chat_job_once()
        self.assertEqual(self.s.state(self.ctx)['aijobs'][0]['status'],'failed')
        self.assertEqual(self.s.state(self.ctx)['aichats'][0]['messages'],[])
        job=self.start()
        with patch('chat_jobs.openai_create',return_value={'id':'resp_test1','status':'in_progress'}):self.s.process_chat_job_once()
        with patch('store.ask_local',return_value='A newer answer'):self.s.action(self.ctx,'ai.ask',{'id':job['chat_id'],'question':'Concurrent request'})
        self.advance()
        with patch('chat_jobs.openai_retrieve',return_value=self.response()):self.s.process_chat_job_once()
        self.assertEqual(self.s.state(self.ctx)['aijobs'][-1]['status'],'failed')
        self.assertEqual(self.s.state(self.ctx)['aichats'][-1]['messages'][-1]['content'],'A newer answer')

    def test_local_cancellation_is_labelled_as_discard_not_provider_stop(self):
        with patch.dict(os.environ,{'TW_AI_PROVIDER':'ollama'}):
            job=self.start()
            def finish_after_cancel(*args):
                self.s.action(self.ctx,'ai.chat.cancel',{'chat_id':job['chat_id']})
                return 'A late local answer'
            with patch('chat_jobs.ask_local',side_effect=finish_after_cancel):self.s.process_chat_job_once()
        state=self.s.state(self.ctx)
        self.assertEqual(state['aijobs'][0]['cancel_outcome'],'local_discarded')
        self.assertEqual(state['aichats'][0]['messages'],[])

    def test_source_message_lookup_is_bounded_and_workspace_scoped(self):
        source=self.s.source_messages(self.ctx,self.c['id'],[self.m['id']])
        self.assertEqual(source['messages'][0]['body'],'Pricing please')
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        with self.assertRaises(Problem):self.s.source_messages(other,self.c['id'],[self.m['id']])
        with self.assertRaises(Problem):self.s.source_messages(self.ctx,self.c['id'],['invented-message'])
        with self.assertRaises(Problem):self.s.source_messages(self.ctx,self.c['id'],['x']*6)

    def test_saved_openai_job_cannot_run_after_switching_provider_and_revoking_paid_gate(self):
        self.start()
        gate='TW_AI_'+self.ctx['tenant_id'].upper()+'_ALLOW_PAID'
        with patch.dict(os.environ,{'TW_AI_PROVIDER':'ollama',gate:'false'}),patch('chat_jobs.openai_create') as create:
            self.s.process_chat_job_once();create.assert_not_called()
        self.assertEqual(self.s.state(self.ctx)['aijobs'][0]['status'],'failed')

    def test_restart_during_cancel_without_provider_id_never_claims_not_submitted(self):
        public=self.start()
        with self.s.db() as db:
            job=self.s._get(db,self.ctx['tenant_id'],'aijob',public['id'])
            self.s._put(db,self.ctx['tenant_id'],'aijob',dict(job,status='cancelling',submitted=True,cancel_requested=True,lease='lost-worker',lease_until=1999999999),job['id'])
        with patch('chat_jobs.openai_create') as create,patch('chat_jobs.openai_cancel') as cancel:
            self.s.process_chat_job_once();create.assert_not_called();cancel.assert_not_called()
        state=self.s.state(self.ctx)['aijobs'][0]
        self.assertEqual(state['status'],'cancel_unconfirmed')
        self.assertNotEqual(state.get('cancel_outcome'),'not_submitted')

    def test_retrieve_timeout_retains_provider_stop_capability(self):
        public=self.start()
        with patch('chat_jobs.openai_create',return_value={'id':'resp_test1','status':'in_progress'}):self.s.process_chat_job_once()
        self.advance()
        with patch('chat_jobs.openai_retrieve',side_effect=ValueError('Temporary timeout')):self.s.process_chat_job_once()
        job=self.s.state(self.ctx)['aijobs'][0];self.assertEqual(job['status'],'waiting');self.assertTrue(job['can_cancel'])
        self.assertEqual(self.s.action(self.ctx,'ai.chat.cancel',{'chat_id':public['chat_id']})['requested'],1)
        with patch('chat_jobs.openai_cancel',return_value={'id':'resp_test1','status':'cancelled'}):self.s.process_chat_job_once()
        self.assertEqual(self.s.state(self.ctx)['aijobs'][0]['status'],'cancelled')

    def test_interrupted_local_submission_is_never_labelled_not_submitted(self):
        with patch.dict(os.environ,{'TW_AI_PROVIDER':'ollama'}):public=self.start()
        with self.s.db() as db:
            job=self.s._get(db,self.ctx['tenant_id'],'aijob',public['id'])
            self.s._put(db,self.ctx['tenant_id'],'aijob',dict(job,status='cancelling',submitted=True,cancel_requested=True,lease='lost-local-worker',lease_until=1999999999),job['id'])
        with patch('chat_jobs.ask_local') as model:self.s.process_chat_job_once();model.assert_not_called()
        job=self.s.state(self.ctx)['aijobs'][0]
        self.assertEqual(job['status'],'cancelled');self.assertEqual(job['cancel_outcome'],'local_discarded')

    def test_selected_model_must_be_server_allowed_and_survives_queueing(self):
        with self.assertRaises(Problem):self.start(model='not-allowed')
        with patch.dict(os.environ,{'TW_AI_ALLOWED_MODELS':'gpt-6-luna,gpt-6.1-sol'}):
            self.start(model='gpt-6.1-sol')
            with patch('chat_jobs.openai_create',return_value=self.response()) as create:self.s.process_chat_job_once()
            self.assertEqual(create.call_args.args[1],'gpt-6.1-sol')
