import json
import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class CustomerAssistantTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'customer-ai.db')
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.prefix='TW_AI_'+self.ctx['tenant_id'].upper()+'_'
        self.env=patch.dict(os.environ,{'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'test-only',self.prefix+'ALLOW_PAID':'true',self.prefix+'AUTO_REPLY':'false'});self.env.start()
        self.ready=patch('customer_assistant.meta_status',return_value={'live':True,'configured':True});self.ready.start()
        self.source=self.s.action(self.ctx,'knowledge.save',{'title':'Hours','body':'We open at nine and close at five.','enabled':True})
        self.assistant=self.save()
    def tearDown(self):self.ready.stop();self.env.stop();self.tmp.cleanup()
    def save(self,**changes):return self.s.action(self.ctx,'customer-assistant.save',dict({'name':'Support','instructions':'Answer from business knowledge. Escalate missing information.','enabled':True,'mode':'draft','keywords':[],'source_ids':[self.source['id']],'daily_limit':100},**changes))
    def incoming(self,id='incoming_1',text='What are your hours?',phone='919000000001'):
        return self.s.inbound(self.ctx['tenant_id'],{'id':id,'from':phone,'text':{'body':text},'timestamp':str(int(time.time()))})
    def output(self,**changes):return json.dumps(dict({'reply':'We are open from nine to five.','needs_human':False,'reason':'Supported by Hours.','knowledge_references':[]},**changes))
    def work_once(self,result=None,side_effect=None):
        with patch('customer_assistant.ask_local',return_value=result or self.output(),side_effect=side_effect) as model,patch('customer_assistant.send_text',return_value='wamid_reply') as send:
            self.s.process_customer_reply_once();return model,send

    def test_real_inbound_generates_one_grounded_draft_and_no_send(self):
        self.incoming();self.incoming();model,send=self.work_once();send.assert_not_called();self.assertEqual(model.call_count,1)
        state=self.s.state(self.ctx);self.assertEqual(len(state['customer_reply_jobs']),1);self.assertEqual(state['messages'][-1]['status'],'draft')
        context=model.call_args.args[1];self.assertEqual(context['knowledge_sources'][0]['title'],'Hours');self.assertTrue(context['_customer_reply']);self.assertNotIn('campaigns',context)

    def test_private_notes_and_other_contacts_never_reach_customer_model(self):
        self.incoming('other',phone='919000000002');self.incoming()
        contacts=self.s.state(self.ctx)['contacts'];target=next(c for c in contacts if c['phone']=='919000000001')
        self.s.action(self.ctx,'message.send',{'contact_id':target['id'],'body':'PRIVATE STAFF NOTE','note':True})
        with self.s.db() as db:
            for row in db.execute("SELECT id,data FROM entities WHERE kind='customerreplyjob'").fetchall():
                data=json.loads(row['data'])
                if data['contact_id']!=target['id']:self.s._put(db,self.ctx['tenant_id'],'customerreplyjob',dict(data,status='cancelled'),row['id'])
        model,_=self.work_once();serialized=json.dumps(model.call_args.args[1]);self.assertNotIn('PRIVATE STAFF NOTE',serialized);self.assertNotIn('919000000002',serialized)

    def test_live_mode_requires_separate_flag_and_sends_only_once(self):
        with self.assertRaises(Problem):self.save(mode='live')
        with patch.dict(os.environ,{self.prefix+'AUTO_REPLY':'true'}):
            self.save(mode='live');self.incoming();model,send=self.work_once();self.assertEqual(send.call_count,1)
            with patch('customer_assistant.ask_local') as again:self.s.process_customer_reply_once();again.assert_not_called()
        self.assertEqual(self.s.state(self.ctx)['messages'][-1]['status'],'accepted')
        state=self.s.state(self.ctx);self.assertEqual(state['contacts'][0]['outgoing_watch']['message_id'],state['messages'][-1]['id'])

    def test_handoff_produces_pending_human_control_without_live_send(self):
        with patch.dict(os.environ,{self.prefix+'AUTO_REPLY':'true'}):
            self.save(mode='live');self.incoming();model,send=self.work_once(self.output(needs_human=True,reply='A teammate will help with that.',reason='No policy covers this request.'));send.assert_not_called()
        contact=self.s.state(self.ctx)['contacts'][0];self.assertTrue(contact['automation_hold']);self.assertEqual(contact['status'],'pending')

    def test_stop_and_human_takeover_suppress_jobs(self):
        self.incoming();contact=self.s.state(self.ctx)['contacts'][0];self.s.action(self.ctx,'chat.takeover',{'id':contact['id']})
        model,send=self.work_once();model.assert_not_called();send.assert_not_called()
        self.s.action(self.ctx,'chat.resume',{'id':contact['id']});self.incoming('stop','STOP')
        model,send=self.work_once();model.assert_not_called();send.assert_not_called()

    def test_new_message_during_generation_discards_late_answer(self):
        self.incoming()
        def changed(*args):self.incoming('new_message','Actually, what is your refund policy?');return self.output()
        model,send=self.work_once(side_effect=changed);send.assert_not_called()
        self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))

    def test_policy_edit_during_generation_discards_stale_answer(self):
        self.incoming()
        def changed(*args):self.s.action(self.ctx,'knowledge.save',{'id':self.source['id'],'title':'Hours','body':'Hours changed.','enabled':True});return self.output()
        self.work_once(side_effect=changed);self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))

    def test_paid_access_revoked_before_worker_prevents_inference(self):
        self.incoming()
        with patch.dict(os.environ,{self.prefix+'ALLOW_PAID':'false'}):
            model,send=self.work_once();model.assert_not_called();send.assert_not_called()

    def test_uncertain_send_is_not_retried(self):
        with patch.dict(os.environ,{self.prefix+'AUTO_REPLY':'true'}):
            self.save(mode='live');self.incoming()
            with patch('customer_assistant.ask_local',return_value=self.output()),patch('customer_assistant.send_text',side_effect=TimeoutError('secret')) as send:
                self.s.process_customer_reply_once();self.s.process_customer_reply_once();self.assertEqual(send.call_count,1)
        job=self.s.state(self.ctx)['customer_reply_jobs'][0];self.assertEqual(job['status'],'unknown');self.assertNotIn('secret',json.dumps(job))

    def test_unapproved_knowledge_is_not_exposed_and_empty_approval_hands_off_locally(self):
        self.s.action(self.ctx,'knowledge.save',{'title':'Staff only','body':'PRIVATE CUSTOMER PASSWORD','enabled':True})
        self.incoming();model,_=self.work_once();self.assertNotIn('PRIVATE CUSTOMER PASSWORD',json.dumps(model.call_args.args[1]))
        self.save(source_ids=[]);self.incoming('another','Refund question?',phone='919000000003');model,send=self.work_once();model.assert_not_called();send.assert_not_called()
        target=next(c for c in self.s.state(self.ctx)['contacts'] if c['phone']=='919000000003');self.assertTrue(target['automation_hold'])

    def test_staff_reply_before_generation_suppresses_automatic_follow_up(self):
        self.incoming();contact=self.s.state(self.ctx)['contacts'][0]
        with self.s.db() as db:self.s._message(db,self.ctx['tenant_id'],contact['id'],'A staff member answered.','out','accepted','wamid_staff')
        model,send=self.work_once();model.assert_not_called();send.assert_not_called()

    def test_daily_generation_limit_is_enforced_before_provider_call(self):
        self.save(daily_limit=1);self.incoming();self.work_once()
        self.incoming('second','Refund question?',phone='919000000004');model,send=self.work_once();model.assert_not_called();send.assert_not_called()

    def test_disabled_assistant_simulations_and_rule_owned_messages_do_not_enqueue(self):
        self.save(enabled=False);self.incoming();self.assertFalse(self.s.state(self.ctx)['customer_reply_jobs'])
        self.save();self.s.inbound(self.ctx['tenant_id'],{'id':'sim','from':'919000000003','text':{'body':'Hours?'}},simulated=True)
        self.s.action(self.ctx,'rule.save',{'name':'Hours rule','keyword':'hours','reply':'A saved reply','enabled':True});self.incoming('rule_owned')
        self.assertFalse(self.s.state(self.ctx)['customer_reply_jobs'])

    def test_window_expiry_during_generation_prevents_live_send(self):
        with patch.dict(os.environ,{self.prefix+'AUTO_REPLY':'true'}):
            self.save(mode='live');self.incoming()
            def expired(*args):
                with self.s.db() as db:
                    contact=self.s._list(db,self.ctx['tenant_id'],'contact')[0];self.s._put(db,self.ctx['tenant_id'],'contact',dict(contact,last_real_inbound=int(time.time())-86410),contact['id'])
                return self.output()
            model,send=self.work_once(side_effect=expired);send.assert_not_called()

    def test_paid_access_revoked_during_generation_discards_reply(self):
        self.incoming()
        def revoked(*args):os.environ[self.prefix+'ALLOW_PAID']='false';return self.output()
        self.work_once(side_effect=revoked);self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))

    def test_provider_failure_requests_human_review_without_retry_or_secret_leak(self):
        self.incoming();model,send=self.work_once(side_effect=TimeoutError('PRIVATE API KEY'))
        self.assertEqual(model.call_count,1);send.assert_not_called()
        model,send=self.work_once();model.assert_not_called();send.assert_not_called()
        state=self.s.state(self.ctx);self.assertTrue(state['contacts'][0]['automation_hold']);self.assertNotIn('PRIVATE API KEY',json.dumps(state['customer_reply_jobs']))

    def test_accepted_job_cannot_be_relabelled_as_cancelled(self):
        with patch.dict(os.environ,{self.prefix+'AUTO_REPLY':'true'}):
            self.save(mode='live');self.incoming();self.work_once()
        job=self.s.state(self.ctx)['customer_reply_jobs'][0]
        with self.assertRaises(Problem):self.s.action(self.ctx,'customer-assistant.cancel',{'id':job['id']})

    def test_openai_customer_contract_is_strict_and_has_no_tools(self):
        from ai import ask_local
        result={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':self.output()}]}]}
        with patch('openai_adapter.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(result).encode())) as call:
            answer=ask_local('Hours?',{'_workspace_id':self.ctx['tenant_id'],'_customer_reply':True,'business':'Acme','knowledge_sources':[],'knowledge_passages':[]},[])
        self.assertIn('nine',answer);payload=json.loads(call.call_args.args[0].data)
        self.assertTrue(payload['text']['format']['strict']);self.assertFalse(payload['store']);self.assertNotIn('tools',payload)

    def test_settings_jobs_and_source_selection_are_tenant_and_admin_scoped(self):
        self.incoming();other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        state=self.s.state(other);self.assertIsNone(state['customer_assistant']);self.assertFalse(state['customer_reply_jobs'])
        with self.assertRaises(Problem):self.s.action(other,'customer-assistant.save',{'name':'Cross','instructions':'Use knowledge.','source_ids':[self.source['id']]})
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'another-long-password','role':'agent'})
        agent=self.s.auth(self.s.login('agent@example.test','another-long-password')['token'])
        with self.assertRaises(Problem):self.s.action(agent,'customer-assistant.save',{'name':'Denied','instructions':'No','enabled':True})

    def test_settings_edit_and_local_stop_fence_inflight_generation(self):
        self.incoming()
        def stopped(*args):
            job=self.s.state(self.ctx)['customer_reply_jobs'][0];self.s.action(self.ctx,'customer-assistant.cancel',{'id':job['id']});return self.output()
        self.work_once(side_effect=stopped);self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))
        self.incoming('next','Hello again')
        def edited(*args):self.save(instructions='Updated support policy.');return self.output()
        self.work_once(side_effect=edited);self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))

    def test_worker_loss_does_not_repeat_model_or_whatsapp_submission(self):
        self.incoming()
        with self.s.db() as db:
            job=self.s._list(db,self.ctx['tenant_id'],'customerreplyjob')[0];self.s._put(db,self.ctx['tenant_id'],'customerreplyjob',dict(job,status='generating',lease='lost',lease_until=int(time.time())-1),job['id'])
        model,send=self.work_once();model.assert_not_called();send.assert_not_called();self.assertEqual(self.s.state(self.ctx)['customer_reply_jobs'][0]['status'],'unknown')

    def test_invented_document_reference_requests_human_review(self):
        self.incoming();model,send=self.work_once(self.output(knowledge_references=[{'document_id':'foreign','chunk_id':'invented'}]));send.assert_not_called()
        state=self.s.state(self.ctx);self.assertTrue(state['contacts'][0]['automation_hold']);self.assertFalse(any(m['direction']=='out' for m in state['messages']))
