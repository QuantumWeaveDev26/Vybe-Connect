import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class DripTests(unittest.TestCase):
    def setUp(self):
        self.clock=patch('store.now',return_value=2000000000);self.clock.start()
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'drip.db')
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.contact=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001','optin':True})
        with self.s.db() as db:self.template=self.s._put(db,self.ctx['tenant_id'],'template',{'name':'welcome','body':'Hello','language':'en','status':'APPROVED','meta_id':'123'})
        self.live=patch('drip_sequences.meta_status',return_value={'live':True,'configured':True});self.live.start()
        self.queue_live=patch('store.meta_status',return_value={'live':True});self.queue_live.start()
    def tearDown(self):self.clock.stop();self.live.stop();self.queue_live.stop();self.tmp.cleanup()
    def action(self,operation,**data):return self.s.action(self.ctx,operation,data)
    def save(self):return self.action('sequence.save',name='Follow-up',steps=[{'template_id':self.template['id'],'wait_seconds':0},{'template_id':self.template['id'],'wait_seconds':3600}])
    def launch(self,sequence,nonce='stable_launch_nonce_12345'):return self.action('sequence.launch',id=sequence['id'],contact_ids=[self.contact['id']],nonce=nonce)

    def test_steps_persist_and_launch_is_idempotent_and_snapshot_based(self):
        sequence=self.save();run=self.launch(sequence);again=self.launch(sequence)
        self.assertEqual(run['id'],again['id']);self.assertEqual(len(self.s.state(self.ctx)['queue']),2)
        self.action('sequence.save',id=sequence['id'],name='Edited',steps=[{'template_id':self.template['id'],'wait_seconds':600}])
        self.assertEqual(Store(self.s.path).state(self.ctx)['sequence_runs'][0]['name'],'Follow-up')

    def test_delay_is_measured_from_actual_previous_submission(self):
        run=self.launch(self.save())
        self.clock.stop();self.clock=patch('store.now',return_value=2000007200);self.clock.start()
        with patch('store.send_template',return_value='wamid_first') as provider:
            self.assertTrue(self.s.process_queue_once());self.assertFalse(self.s.process_queue_once());self.assertEqual(provider.call_count,1)
        self.clock.stop();self.clock=patch('store.now',return_value=2000010800);self.clock.start()
        with patch('store.send_template',return_value='wamid_second'):self.assertTrue(self.s.process_queue_once())
        self.assertEqual(self.s.state(self.ctx)['sequence_runs'][0]['counts']['accepted'],2)

    def test_unknown_submission_cancels_later_steps_without_retry(self):
        run=self.launch(self.save())
        with patch('store.send_template',side_effect=TimeoutError('uncertain')) as provider:
            self.s.process_queue_once();self.s.process_queue_once();self.assertEqual(provider.call_count,1)
        statuses={q['status'] for q in self.s.state(self.ctx)['queue']};self.assertEqual(statuses,{'unknown','cancelled'})

    def test_pause_resume_and_cancel_control_only_unsent_work(self):
        run=self.launch(self.save());self.action('sequence.pause',id=run['id'])
        self.assertEqual({c['status'] for c in self.s.state(self.ctx)['campaigns']},{'paused'})
        with patch('store.send_template') as provider:self.assertFalse(self.s.process_queue_once());provider.assert_not_called()
        self.action('sequence.resume',id=run['id'])
        with patch('store.send_template',return_value='wamid_first'):self.assertTrue(self.s.process_queue_once())
        self.action('sequence.cancel',id=run['id']);self.assertEqual({q['status'] for q in self.s.state(self.ctx)['queue']},{'accepted','cancelled'})
        self.assertEqual({c['status'] for c in self.s.state(self.ctx)['campaigns']},{'submitted','cancelled'})

    def test_launch_requires_approved_templates_live_gate_and_consent(self):
        sequence=self.save()
        with patch('drip_sequences.meta_status',return_value={'live':False}):
            with self.assertRaises(Problem):self.launch(sequence)
        with patch('drip_sequences.meta_status',return_value={'live':True,'configured':False}):
            with self.assertRaises(Problem):self.launch(sequence)
        self.action('contact.save',id=self.contact['id'],name='Buyer',phone='919000000001',optin=False)
        with self.assertRaises(Problem):self.launch(sequence)
        self.assertFalse(self.s.state(self.ctx)['queue'])

    def test_invalid_wait_and_cross_workspace_templates_are_rejected(self):
        with self.assertRaises(Problem):self.action('sequence.save',name='Invalid',steps=[{'template_id':self.template['id'],'wait_seconds':-1}])
        other=self.s.auth(self.token,self.action('workspace.create',name='Other')['id'])
        with self.assertRaises(Problem):self.s.action(other,'sequence.save',{'name':'Cross scope','steps':[{'template_id':self.template['id'],'wait_seconds':0}]})

    def test_consent_is_rechecked_before_each_submission(self):
        self.launch(self.save());self.action('contact.save',id=self.contact['id'],name='Buyer',phone='919000000001',optin=False)
        with patch('store.send_template') as provider:self.s.process_queue_once();provider.assert_not_called()
        self.assertEqual({q['status'] for q in self.s.state(self.ctx)['queue']},{'skipped','cancelled'})

    def test_worker_interruption_does_not_release_follow_on_step(self):
        self.launch(self.save())
        with self.s.db() as db:db.execute("UPDATE outbound SET status='sending',claimed=? WHERE id=(SELECT id FROM outbound ORDER BY rowid LIMIT 1)",(2000000000-301,))
        with patch('store.send_template') as provider:self.s.process_queue_once();provider.assert_not_called()
        self.assertEqual({q['status'] for q in self.s.state(self.ctx)['queue']},{'unknown','cancelled'})

    def test_reused_nonce_with_other_audience_is_rejected(self):
        sequence=self.save();self.launch(sequence);other=self.action('contact.save',name='Another',phone='919000000002',optin=True)
        with self.assertRaises(Problem):self.action('sequence.launch',id=sequence['id'],contact_ids=[other['id']],nonce='stable_launch_nonce_12345')
        self.assertEqual(len(self.s.state(self.ctx)['queue']),2)

    def test_agents_cannot_launch_or_control_sequences(self):
        run=self.launch(self.save());self.action('member.add',name='Agent',email='agent@example.test',password='another-long-password',role='agent')
        agent=self.s.auth(self.s.login('agent@example.test','another-long-password')['token'])
        with self.assertRaises(Problem):self.s.action(agent,'sequence.cancel',{'id':run['id']})
