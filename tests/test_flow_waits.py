import tempfile
import unittest
import threading
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class FlowWaitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'wait.db';self.s=Store(self.path);self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.clock=patch('store.now',return_value=100000);self.clock.start()
    def tearDown(self):self.clock.stop();self.tmp.cleanup()
    def save(self,graph=None,**values):
        return self.s.action(self.ctx,'flow.save',dict({'name':'Follow up','keyword':'help','reply':'Hello','enabled':True,'graph':graph or {'start':'first','nodes':[{'id':'first','type':'message','text':'First','next':'wait'},{'id':'wait','type':'wait','seconds':60,'next':'after'},{'id':'after','type':'message','text':'After wait'}]}},**values))
    def incoming(self,id='incoming',text='help'):
        return self.s.inbound(self.ctx['tenant_id'],{'id':id,'from':'919000000001','timestamp':'100000','text':{'body':text}})
    def drafts(self):return [m['body'] for m in self.s.state(self.ctx)['messages'] if m['status']=='draft']
    def test_wait_persists_across_restart_and_continues_once_after_due(self):
        self.save();self.incoming();self.assertEqual(self.drafts(),['First']);self.s=Store(self.path)
        with patch('store.now',return_value=100059):self.s.process_flow_wait_once()
        self.assertEqual(self.drafts(),['First'])
        with patch('store.now',return_value=100060):self.s.process_flow_wait_once();self.s.process_flow_wait_once()
        self.assertEqual(self.drafts(),['First','After wait']);self.assertNotIn('flow_session',self.s.state(self.ctx)['contacts'][0])
    def test_new_message_does_not_skip_wait_or_answer_next_question(self):
        self.save({'start':'wait','nodes':[{'id':'wait','type':'wait','seconds':60,'next':'question'},{'id':'question','type':'question','text':'Your name?','variable':'answer','next':'end'},{'id':'end','type':'message','text':'Hello {{answer}}'}]});self.incoming();self.incoming('early','Too early')
        self.assertEqual(self.drafts(),[])
        with patch('store.now',return_value=100060):self.s.process_flow_wait_once()
        self.assertEqual(self.drafts(),['Your name?'])
        with patch('store.now',return_value=100061):self.incoming('answer','Asha')
        self.assertEqual(self.drafts(),['Your name?','Hello Asha'])
    def test_stop_and_takeover_cancel_pending_waits(self):
        self.save();self.incoming();self.incoming('stop','STOP')
        with patch('store.now',return_value=100100):self.s.process_flow_wait_once()
        self.assertEqual(self.drafts(),['First']);self.incoming('restart','help');contact=self.s.state(self.ctx)['contacts'][0]
        self.s.action(self.ctx,'chat.takeover',{'id':contact['id']})
        with patch('store.now',return_value=100100):self.s.process_flow_wait_once()
        self.assertEqual(self.drafts(),['First','First'])
    def test_editing_or_disabling_flow_cancels_old_sessions(self):
        flow=self.save();self.incoming();self.save(id=flow['id'])
        with patch('store.now',return_value=100100):self.s.process_flow_wait_once()
        self.assertEqual(self.drafts(),['First']);self.assertNotIn('flow_session',self.s.state(self.ctx)['contacts'][0])
    def test_invalid_delay_values_rejected(self):
        for value in [0,-1,604801,True,'60',None]:
            with self.assertRaises(Problem):self.save({'start':'wait','nodes':[{'id':'wait','type':'wait','seconds':value}]})
    def test_second_wait_starts_from_actual_continuation_time(self):
        self.save({'start':'one','nodes':[{'id':'one','type':'wait','seconds':60,'next':'two'},{'id':'two','type':'wait','seconds':60,'next':'done'},{'id':'done','type':'message','text':'Done'}]});self.incoming()
        with patch('store.now',return_value=100600):self.s.process_flow_wait_once()
        self.assertEqual(self.s.state(self.ctx)['contacts'][0]['flow_session']['due'],100660);self.assertEqual(self.drafts(),[])
    def test_wait_expansion_never_calls_a_provider(self):
        self.save();self.incoming()
        with patch('store.now',return_value=100100),patch('store.send_text') as send,patch('customer_assistant.ask_local') as ai:
            self.s.process_flow_wait_once();send.assert_not_called();ai.assert_not_called()

    def test_two_workers_do_not_duplicate_continuation(self):
        self.save();self.incoming();other=Store(self.path);errors=[]
        def advance(store):
            try:store.process_flow_wait_once()
            except Exception as error:errors.append(error)
        with patch('store.now',return_value=100060):
            workers=[threading.Thread(target=advance,args=(store,)) for store in [self.s,other]]
            for worker in workers:worker.start()
            for worker in workers:worker.join()
        self.assertEqual(errors,[]);self.assertEqual(self.drafts(),['First','After wait'])

    def test_disabled_flow_cancels_wait_and_question_sessions(self):
        flow=self.save();self.incoming();self.save(id=flow['id'],enabled=False)
        with patch('store.now',return_value=100100):self.s.process_flow_wait_once()
        self.assertEqual(self.drafts(),['First']);self.assertNotIn('flow_session',self.s.state(self.ctx)['contacts'][0])
