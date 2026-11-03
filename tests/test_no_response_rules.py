import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class NoResponseRuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'followup.db';self.s=Store(self.path);token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
        self.contact=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001'});self.stamp=int(time.time())
    def tearDown(self):self.tmp.cleanup()
    def rule(self,**changes):return self.s.action(self.ctx,'rule.save',dict({'name':'Followup','event':'customer_no_response','enabled':True,'wait_seconds':60,'actions':[{'type':'task','value':'Customer followup'}]},**changes))
    def outbound(self,status='accepted'):
        with patch('store.now',return_value=self.stamp),self.s.db() as db:return self.s._message(db,self.ctx['tenant_id'],self.contact['id'],'Staff reply','out',status)
    def advance(self,seconds):
        with patch('store.now',return_value=self.stamp+seconds):return self.s.process_no_response_once()
    def test_actual_acceptance_waits_until_due_and_survives_restart_once(self):
        self.rule();self.outbound();self.s=Store(self.path);self.advance(59);self.assertEqual(self.s.state(self.ctx)['tasks'],[])
        self.advance(60);self.advance(90);self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_drafts_unknown_sends_and_simulations_do_not_arm_followups(self):
        self.rule()
        for status in ['draft','unknown','failed','simulated']:self.outbound(status)
        self.advance(100);self.assertEqual(self.s.state(self.ctx)['tasks'],[])
    def test_new_real_inbound_cancels_but_simulation_does_not_cancel_real_watch(self):
        self.rule();self.outbound();self.s.inbound(self.ctx['tenant_id'],{'id':'reply','from':'919000000001','text':{'body':'Thanks'}});self.advance(100)
        self.assertEqual(self.s.state(self.ctx)['tasks'],[])
        self.outbound();self.s.inbound(self.ctx['tenant_id'],{'id':'sim','from':'919000000001','text':{'body':'Synthetic'}},True);self.advance(100)
        self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_enable_and_edit_do_not_replay_preexisting_outbound_messages(self):
        self.outbound();rule=self.rule();self.advance(100);self.assertEqual(self.s.state(self.ctx)['tasks'],[])
        self.outbound();self.rule(id=rule['id']);self.advance(100);self.assertEqual(self.s.state(self.ctx)['tasks'],[])
    def test_takeover_and_stop_cancel_watches(self):
        self.rule();self.outbound();self.s.action(self.ctx,'chat.takeover',{'id':self.contact['id']});self.advance(100);self.assertEqual(self.s.state(self.ctx)['tasks'],[])
        self.s.action(self.ctx,'chat.resume',{'id':self.contact['id']});self.outbound();self.s.inbound(self.ctx['tenant_id'],{'id':'stop','from':'919000000001','text':{'body':'STOP'}});self.advance(100);self.assertEqual(self.s.state(self.ctx)['tasks'],[])
    def test_each_rule_waits_for_its_own_duration(self):
        self.rule();self.rule(name='Later',wait_seconds=600);self.outbound();self.advance(60);self.advance(60);self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
        self.advance(600);self.assertEqual(len(self.s.state(self.ctx)['tasks']),2)
    def test_new_accepted_reply_rearms_after_prior_evaluation(self):
        self.rule();self.outbound();self.advance(60);self.outbound();self.advance(60);self.assertEqual(len(self.s.state(self.ctx)['tasks']),2)
    def test_delay_bounds_are_validated(self):
        for value in [0,604801,True,'60']:
            with self.assertRaises(Problem):self.rule(wait_seconds=value)
    def test_flow_handoff_discards_reply_watch(self):
        from flows import run_graph
        result,_=run_graph({'id':'flow','graph':{'start':'human','nodes':[{'id':'human','type':'handoff'}]}},dict(self.contact,outgoing_watch={'message_id':'old'}),'')
        self.assertNotIn('outgoing_watch',result)
    def test_competing_workers_evaluate_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from no_response_rules import process_once
        self.rule();self.outbound()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:process_once(Store(self.path),self.stamp+60),range(2)))
        self.assertEqual(sum(results),1);self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_live_text_acceptance_arms_but_delivery_upgrade_does_not_reset(self):
        from reply_tracking import accepted
        self.rule();self.s.inbound(self.ctx['tenant_id'],{'id':'real','from':'919000000001','text':{'body':'Hi'}})
        with patch('store.meta_status',return_value={'live':True}),patch('store.send_text',return_value='wamid.test'),patch('store.now',return_value=self.stamp):
            message=self.s._live_reply(self.ctx,{'contact_id':self.contact['id'],'body':'Hello'})
        with self.s.db() as db:
            db.execute("UPDATE messages SET status='read' WHERE id=?",(message['id'],));self.assertFalse(accepted(self.s,db,self.ctx['tenant_id'],message['id'],self.stamp+50))
        self.advance(60);self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
