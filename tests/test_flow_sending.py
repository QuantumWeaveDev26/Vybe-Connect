import tempfile
import unittest
import time
import threading
import os
from pathlib import Path
from unittest.mock import patch
from store import Store


class FlowSendingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'liveflow.db');self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token']);self.stamp=int(time.time())
        self.ready=patch('flow_delivery.ready',return_value=True);self.ready.start()
    def tearDown(self):self.ready.stop();self.tmp.cleanup()
    def save(self,nodes=None):return self.s.action(self.ctx,'flow.save',{'name':'Bot','keyword':'help','reply':'Hi','enabled':True,'delivery_mode':'live','graph':{'start':'one','nodes':nodes or [{'id':'one','type':'message','text':'Hello','next':'two'},{'id':'two','type':'message','text':'Next'}]}})
    def incoming(self,id='real',text='help',simulated=False):self.s.inbound(self.ctx['tenant_id'],{'id':id,'from':'919000000001','text':{'body':text}},simulated)
    def step(self,result='wamid.flow'):
        with patch('flow_delivery.send_text',return_value=result) as provider:self.s.process_flow_send_once();return provider
    def state(self):return self.s.state(self.ctx)
    def test_messages_queue_in_order_and_advance_only_after_acceptance(self):
        self.save();self.incoming();self.assertEqual(len(self.state()['flow_sends']),1);self.assertEqual([m for m in self.state()['messages'] if m['direction']=='out'],[])
        self.step();self.assertEqual([m['body'] for m in self.state()['messages'] if m['direction']=='out'],['Hello']);self.step('wamid.second');self.assertEqual([m['body'] for m in self.state()['messages'] if m['direction']=='out'],['Hello','Next']);self.assertNotIn('flow_session',self.state()['contacts'][0])
    def test_question_becomes_answerable_only_after_accepted_prompt(self):
        self.save([{'id':'one','type':'question','text':'Name?','variable':'answer','next':'reply'},{'id':'reply','type':'message','text':'Hi {{answer}}'}]);self.incoming();self.step();self.assertEqual(self.state()['contacts'][0]['flow_session']['mode'],'question');self.incoming('answer','Asha');self.step('wamid.answer');self.assertEqual(self.state()['messages'][-1]['body'],'Hi Asha')
    def test_wait_starts_after_actual_submission(self):
        self.save([{'id':'one','type':'message','text':'First','next':'wait'},{'id':'wait','type':'wait','seconds':60,'next':'last'},{'id':'last','type':'message','text':'Last'}]);self.incoming()
        with patch('flow_delivery.now',return_value=self.stamp+300),patch('store.now',return_value=self.stamp+300):self.step()
        self.assertEqual(self.state()['contacts'][0]['flow_session']['due'],self.stamp+360)
    def test_simulation_creates_drafts_without_provider_jobs(self):
        self.save();self.incoming(simulated=True);self.assertEqual(self.state()['flow_sends'],[]);self.assertEqual([m['status'] for m in self.state()['messages'] if m['direction']=='out'],['draft','draft'])
    def test_takeover_and_newer_message_prevent_queued_submission(self):
        self.save();self.incoming();c=self.state()['contacts'][0];self.s.action(self.ctx,'chat.takeover',{'id':c['id']});self.step().assert_not_called();self.assertEqual(self.state()['flow_sends'][0]['status'],'cancelled')
    def test_unknown_submission_pauses_without_retry(self):
        self.save();self.incoming()
        with patch('flow_delivery.send_text',side_effect=TimeoutError()) as provider:self.s.process_flow_send_once();self.s.process_flow_send_once();self.assertEqual(provider.call_count,1)
        self.assertEqual(self.state()['flow_sends'][0]['status'],'unknown');self.assertTrue(self.state()['contacts'][0]['automation_hold'])
    def test_provider_response_without_message_id_is_unknown_not_accepted(self):
        self.save();self.incoming();self.step(None);self.assertEqual(self.state()['flow_sends'][0]['status'],'unknown');self.assertEqual(len(self.state()['flow_sends']),1)
    def test_disabled_runtime_never_calls_transport(self):
        self.save();self.incoming()
        with patch('flow_delivery.ready',return_value=False):self.step().assert_not_called()
    def test_edit_cancels_old_jobs(self):
        flow=self.save();self.incoming();self.s.action(self.ctx,'flow.save',dict(flow,name='Changed'));self.step().assert_not_called()
    def test_new_inbound_before_prompt_acceptance_never_answers_question(self):
        self.save([{'id':'one','type':'question','text':'Name?','variable':'answer'}]);self.incoming();self.incoming('new','Asha');self.step().assert_not_called();self.assertNotIn('answer',self.state()['contacts'][0]['attributes'])
    def test_closed_window_and_removed_owner_prevent_send(self):
        self.save();self.incoming()
        with patch('flow_delivery.now',return_value=self.stamp+86401):self.step().assert_not_called()
    def test_simulation_cannot_advance_real_queued_prompt(self):
        self.save();self.incoming();self.incoming('sim','Synthetic',True);self.assertEqual(self.state()['contacts'][0]['flow_session']['mode'],'sending');self.step().assert_called_once()
    def test_worker_interruption_and_late_result_do_not_resume_or_retry(self):
        self.save();self.incoming()
        def delayed(*args):
            with patch('flow_delivery.now',return_value=self.stamp+100):self.s.process_flow_send_once()
            return 'wamid.late'
        with patch('flow_delivery.send_text',side_effect=delayed) as send:self.s.process_flow_send_once();self.s.process_flow_send_once();self.assertEqual(send.call_count,1)
        job=self.state()['flow_sends'][0];self.assertEqual(job['status'],'unknown');self.assertEqual(job['late_outcome'],'accepted');self.assertTrue(self.state()['contacts'][0]['automation_hold'])
    def test_competing_worker_cannot_duplicate_inflight_submission(self):
        self.save();self.incoming();entered=threading.Event();release=threading.Event();errors=[]
        def slow(*args):entered.set();release.wait(5);return 'wamid.once'
        def worker():
            try:self.s.process_flow_send_once()
            except Exception as error:errors.append(error)
        with patch('flow_delivery.send_text',side_effect=slow) as send:
            thread=threading.Thread(target=worker);thread.start()
            try:self.assertTrue(entered.wait(3));self.assertFalse(self.s.process_flow_send_once())
            finally:release.set();thread.join(6)
            self.assertEqual(send.call_count,1);self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
    def test_removed_owner_cannot_send(self):
        self.save();self.incoming()
        with self.s.db() as db:db.execute('DELETE FROM members WHERE tenant=? AND user=?',(self.ctx['tenant_id'],self.ctx['user']['id']))
        self.step().assert_not_called()
    def test_server_requires_both_complete_live_meta_and_workspace_gate(self):
        import flow_delivery
        self.ready.stop();prefix='TW_META_'+self.ctx['tenant_id'].upper()+'_FLOW_SEND'
        with patch('flow_delivery.meta_status',return_value={'configured':True,'live':True}),patch.dict(os.environ,{prefix:'false'}):self.assertFalse(flow_delivery.ready(self.ctx['tenant_id']))
        with patch('flow_delivery.meta_status',return_value={'configured':True,'live':True}),patch.dict(os.environ,{prefix:'true'}):self.assertTrue(flow_delivery.ready(self.ctx['tenant_id']));self.assertFalse(flow_delivery.ready('other_workspace'))
        with patch('flow_delivery.meta_status',return_value={'configured':True,'live':False}),patch.dict(os.environ,{prefix:'true'}):self.assertFalse(flow_delivery.ready(self.ctx['tenant_id']))
