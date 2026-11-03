import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store, Problem


class AgentSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'agents.db';self.s=Store(self.path)
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.agent=self.s.action(self.ctx,'aiagent.save',{'name':'Daily Digest','instructions':'Summarize actual workspace facts.'})
        self.env=patch.dict(os.environ,{'TW_AI_ENABLED':'true','TW_AI_MODEL':'test-local-model'});self.env.start()

    def tearDown(self):self.env.stop();self.tmp.cleanup()

    def schedule(self):return self.s.action(self.ctx,'aiagent.schedule',{'id':self.agent['id'],'enabled':True,'interval':3600})

    def test_schedule_persists_runs_when_due_and_advances_across_restart(self):
        with patch('store.now',return_value=2000000000):self.schedule()
        restarted=Store(self.path)
        with patch('store.now',return_value=2000003601),patch('store.ask_local',return_value=json.dumps({'summary':'No conversations in this workspace.','findings':[]})) as model:
            self.assertTrue(restarted.process_agent_schedule_once())
            self.assertFalse(restarted.process_agent_schedule_once())
        state=self.s.state(self.ctx);self.assertEqual(model.call_count,1)
        self.assertEqual(state['airuns'][0]['trigger'],'scheduled')
        self.assertEqual(state['airuns'][0]['status'],'completed')
        self.assertEqual(state['aiagents'][0]['next_run'],2000007201)
        self.assertEqual(state['queue'],[])

    def test_paused_archived_and_unconfigured_agents_do_not_run(self):
        self.schedule();self.s.action(self.ctx,'aiagent.schedule',{'id':self.agent['id'],'enabled':False})
        with patch('store.now',return_value=2100000000),patch('store.ask_local') as model:
            self.assertFalse(self.s.process_agent_schedule_once());model.assert_not_called()
        with patch.dict(os.environ,{'TW_AI_ENABLED':'false'}):
            with self.assertRaisesRegex(Problem,'configured'):self.schedule()
        self.schedule();self.s.action(self.ctx,'aiagent.archive',{'id':self.agent['id']})
        with patch('store.now',return_value=2100000000),patch('store.ask_local') as model:
            self.assertFalse(self.s.process_agent_schedule_once());model.assert_not_called()
        with self.assertRaises(Problem):self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})

    def test_schedule_requires_admin_and_foreign_agent_cannot_be_modified(self):
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        with self.assertRaises(Problem):self.s.action(other,'aiagent.schedule',{'id':self.agent['id'],'enabled':True,'interval':3600})
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'another-long-password','role':'agent'})
        agent=self.s.auth(self.s.login('agent@example.test','another-long-password')['token'])
        with self.assertRaises(Problem):self.s.action(agent,'aiagent.schedule',{'id':self.agent['id'],'enabled':True,'interval':3600})

    def test_edit_preserves_schedule_and_failure_waits_until_next_due(self):
        with patch('store.now',return_value=2000000000):self.schedule()
        self.s.action(self.ctx,'aiagent.save',{'id':self.agent['id'],'name':'Renamed','instructions':'Use actual facts.'})
        self.assertTrue(self.s.state(self.ctx)['aiagents'][0]['schedule_enabled'])
        with patch('store.now',return_value=2000003601),patch('store.ask_local',side_effect=ValueError('Local model unavailable')) as model:
            self.assertTrue(self.s.process_agent_schedule_once());self.assertFalse(self.s.process_agent_schedule_once())
        self.assertEqual(model.call_count,1);self.assertEqual(self.s.state(self.ctx)['airuns'][0]['status'],'failed')

    def test_manual_and_scheduled_execution_cannot_overlap(self):
        entered=threading.Event();release=threading.Event();results=[]
        def slow_model(*args):entered.set();release.wait(5);return json.dumps({'summary':'No findings.','findings':[]})
        def run():
            try:results.append(self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']}))
            except Exception as e:results.append(e)
        with patch('store.ask_local',side_effect=slow_model):
            thread=threading.Thread(target=run);thread.start()
            self.assertTrue(entered.wait(3))
            try:
                with self.assertRaisesRegex(Problem,'already running'):self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
            finally:release.set();thread.join(6)
        self.assertFalse(thread.is_alive());self.assertEqual(len(results),1);self.assertIsInstance(results[0],dict)

    def test_expired_worker_cannot_publish_findings(self):
        def expire_lease(*args):
            with self.s.db() as db:db.execute('DELETE FROM agent_leases')
            return json.dumps({'summary':'Old run.','findings':[]})
        with patch('store.ask_local',side_effect=expire_lease):
            with self.assertRaisesRegex(Problem,'lease'):self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
        self.assertEqual(self.s.state(self.ctx)['findings'],[])

    def test_archive_and_restore_cannot_revive_an_inflight_run(self):
        def archive_restore(*args):
            self.s.action(self.ctx,'aiagent.archive',{'id':self.agent['id']})
            self.s.action(self.ctx,'aiagent.archive',{'id':self.agent['id'],'archived':False})
            return json.dumps({'summary':'Old run must be discarded.','findings':[]})
        with patch('store.ask_local',side_effect=archive_restore):
            with self.assertRaisesRegex(Problem,'lease'):self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
        self.assertEqual(self.s.state(self.ctx)['airuns'][0]['status'],'interrupted')
        with patch('store.ask_local',return_value=json.dumps({'summary':'Fresh run.','findings':[]})):
            self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
        self.assertEqual(self.s.state(self.ctx)['airuns'][-1]['status'],'completed')

    def test_openai_scheduler_obeys_per_workspace_paid_gate(self):
        gate='TW_AI_'+self.ctx['tenant_id'].upper()+'_ALLOW_PAID'
        with patch.dict(os.environ,{'TW_AI_PROVIDER':'openai','TW_OPENAI_API_KEY':'unit-test-only',gate:'true'}):
            with patch('store.now',return_value=2000000000):self.schedule()
            with patch('store.now',return_value=2000003601),patch('store.ask_local',return_value=json.dumps({'summary':'No findings.','findings':[]})) as model:
                self.assertTrue(self.s.process_agent_schedule_once())
                self.assertEqual(model.call_args.args[1]['_workspace_id'],self.ctx['tenant_id'])
            with patch.dict(os.environ,{gate:'false'}),patch('store.now',return_value=2100000000),patch('store.ask_local') as model:
                self.assertFalse(self.s.process_agent_schedule_once());model.assert_not_called()
