import json
import os
import time
import unittest
from unittest.mock import patch
from tests import test_customer_assistant as fixtures
from store import Problem


class HandoffRoutingTests(unittest.TestCase):
    save=fixtures.CustomerAssistantTests.save
    incoming=fixtures.CustomerAssistantTests.incoming
    output=fixtures.CustomerAssistantTests.output
    work_once=fixtures.CustomerAssistantTests.work_once
    def setUp(self):
        fixtures.CustomerAssistantTests.setUp(self)
        self.agent=self.s.action(self.ctx,'member.add',{'name':'Support','email':'support@example.test','password':'long-enough-password','role':'agent'})
    def tearDown(self):fixtures.CustomerAssistantTests.tearDown(self)
    def handoff(self):self.incoming();return self.work_once(self.output(needs_human=True,reply='',reason='Policy needs a teammate.'))

    def test_handoff_routes_to_selected_member_and_records_reason(self):
        self.save(handoff_assignee=self.agent['id']);self.handoff();contact=self.s.state(self.ctx)['contacts'][0]
        self.assertEqual(contact['assignee'],self.agent['id']);self.assertTrue(contact['handoff']['active']);self.assertEqual(contact['handoff']['reason'],'Policy needs a teammate.')

    def test_existing_valid_assignee_is_preserved(self):
        self.save(handoff_assignee=self.agent['id']);self.incoming();contact=self.s.state(self.ctx)['contacts'][0]
        self.s.action(self.ctx,'chat.update',{'id':contact['id'],'assignee':self.ctx['user']['id']})
        self.work_once(self.output(needs_human=True,reply='',reason='Review'));self.assertEqual(self.s.state(self.ctx)['contacts'][0]['assignee'],self.ctx['user']['id'])

    def test_task_option_creates_one_internal_task_and_resume_resolves_handoff(self):
        self.save(handoff_assignee=self.agent['id'],handoff_task=True);self.handoff();self.s.process_customer_reply_once()
        state=self.s.state(self.ctx);self.assertEqual(len(state['tasks']),1);self.assertEqual(state['tasks'][0]['owner'],self.agent['id'])
        self.s.action(self.ctx,'chat.resume',{'id':state['contacts'][0]['id']});contact=self.s.state(self.ctx)['contacts'][0]
        self.assertFalse(contact['handoff']['active']);self.assertFalse(contact['automation_hold']);self.assertIn('resolved_at',contact['handoff'])

    def test_foreign_member_and_non_boolean_task_option_rejected(self):
        with self.assertRaises(Problem):self.save(handoff_assignee='foreign_member')
        with self.assertRaises(Problem):self.save(handoff_task='true')

    def test_removed_route_falls_back_to_administrator(self):
        self.save(handoff_assignee=self.agent['id'])
        with self.s.db() as db:db.execute('DELETE FROM members WHERE tenant=? AND user=?',(self.ctx['tenant_id'],self.agent['id']))
        self.handoff();self.assertEqual(self.s.state(self.ctx)['contacts'][0]['assignee'],self.ctx['user']['id'])

    def test_customer_worker_uses_least_busy_pool_for_model_handoff(self):
        busy=self.s.action(self.ctx,'contact.save',{'name':'Busy','phone':'919000000099'})
        self.s.action(self.ctx,'chat.update',{'id':busy['id'],'assignee':self.ctx['user']['id'],'status':'pending'})
        self.save(handoff_strategy='least_busy',handoff_pool=[self.ctx['user']['id'],self.agent['id']],handoff_task=True)
        self.handoff();state=self.s.state(self.ctx);target=next(c for c in state['contacts'] if c['id']!=busy['id'])
        self.assertEqual(target['assignee'],self.agent['id']);self.assertEqual(target['handoff']['routing']['strategy'],'least_busy');self.assertEqual(state['tasks'][0]['owner'],self.agent['id'])

    def test_model_failure_uses_same_handoff_routing_without_customer_send(self):
        self.save(handoff_assignee=self.agent['id'],handoff_task=True);self.incoming()
        _,send=self.work_once(side_effect=TimeoutError('private provider error'));send.assert_not_called()
        state=self.s.state(self.ctx);self.assertEqual(state['contacts'][0]['assignee'],self.agent['id']);self.assertEqual(len(state['tasks']),1);self.assertNotIn('private provider error',json.dumps(state))

    def test_expired_worker_routes_review_once_without_model_resubmission(self):
        self.save(handoff_assignee=self.agent['id'],handoff_task=True);self.incoming()
        with self.s.db() as db:
            job=self.s._list(db,self.ctx['tenant_id'],'customerreplyjob')[0]
            self.s._put(db,self.ctx['tenant_id'],'customerreplyjob',dict(job,status='generating',lease='lost',lease_until=int(time.time())-1),job['id'])
        with patch('customer_assistant.ask_local') as model:
            self.s.process_customer_reply_once();self.s.process_customer_reply_once();model.assert_not_called()
        state=self.s.state(self.ctx);self.assertTrue(state['contacts'][0]['automation_hold']);self.assertEqual(len(state['tasks']),1)

    def test_expired_generation_does_not_reopen_a_conversation_answered_by_staff(self):
        self.save(handoff_assignee=self.agent['id'],handoff_task=True);self.incoming()
        with self.s.db() as db:
            job=self.s._list(db,self.ctx['tenant_id'],'customerreplyjob')[0]
            self.s._put(db,self.ctx['tenant_id'],'customerreplyjob',dict(job,status='generating',lease='lost',lease_until=int(time.time())-1),job['id'])
            self.s._message(db,self.ctx['tenant_id'],job['contact_id'],'Staff answered.','out','accepted')
        self.s.process_customer_reply_once();state=self.s.state(self.ctx)
        self.assertFalse(state['contacts'][0].get('automation_hold'));self.assertEqual(state['tasks'],[])

    def test_uncertain_live_submission_routes_to_human_without_retry(self):
        with patch.dict(os.environ,{self.prefix+'AUTO_REPLY':'true'}):
            self.save(mode='live',handoff_assignee=self.agent['id'],handoff_task=True);self.incoming()
            with patch('customer_assistant.ask_local',return_value=self.output()),patch('customer_assistant.send_text',side_effect=TimeoutError()) as send:
                self.s.process_customer_reply_once();self.s.process_customer_reply_once();send.assert_called_once()
        state=self.s.state(self.ctx);self.assertEqual(state['contacts'][0]['assignee'],self.agent['id']);self.assertEqual(len(state['tasks']),1)
