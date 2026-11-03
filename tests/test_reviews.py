import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store, Problem


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'reviews.db')
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.c=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001'})
        with self.s.db() as db:self.msg=self.s._message(db,self.ctx['tenant_id'],self.c['id'],'Please send pricing.','in','received')
        self.agent=self.s.action(self.ctx,'aiagent.save',{'name':'Sales review','instructions':'Look for purchase interest.'})

    def tearDown(self):self.tmp.cleanup()

    def analyze(self,action=None,**kw):
        finding=dict(title='Pricing inquiry',details='Customer asks for pricing; review the proposed next step.',contact_id=self.c['id'],evidence_ids=[self.msg['id']],action=action or {'type':'tag','tag':'Interested'})
        finding.update(kw)
        with patch('store.ask_local',return_value=json.dumps({'summary':'One inquiry found in the sample.','findings':[finding]})):
            return self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})

    def test_analysis_persists_pending_findings_and_approval_applies_once(self):
        run=self.analyze();state=self.s.state(self.ctx)
        self.assertEqual(run['status'],'completed');self.assertEqual(state['contacts'][0]['tags'],[])
        finding=state['findings'][0]
        self.assertEqual(finding['status'],'pending');self.assertEqual(state['queue'],[])
        result=self.s.action(self.ctx,'finding.review',{'id':finding['id'],'decision':'approve'})
        self.assertEqual(result['status'],'applied');self.assertIn('Interested',self.s.state(self.ctx)['contacts'][0]['tags'])
        with self.assertRaises(Problem):self.s.action(self.ctx,'finding.review',{'id':finding['id'],'decision':'approve'})

    def test_reviewed_assignment_cancels_pending_automation_continuations(self):
        with self.s.db() as db:
            c=self.s._get(db,self.ctx['tenant_id'],'contact',self.c['id']);self.s._put(db,self.ctx['tenant_id'],'contact',dict(c,outgoing_watch={'message_id':'old'},flow_session={'flow_id':'old'}),c['id'])
        self.analyze({'type':'assign','owner':self.ctx['user']['id']});finding=self.s.state(self.ctx)['findings'][0]
        self.s.action(self.ctx,'finding.review',{'id':finding['id'],'decision':'approve'})
        contact=self.s.state(self.ctx)['contacts'][0];self.assertTrue(contact['automation_hold']);self.assertNotIn('outgoing_watch',contact);self.assertNotIn('flow_session',contact)

    def test_review_can_dismiss_and_stale_targets_cannot_be_changed(self):
        self.analyze();f=self.s.state(self.ctx)['findings'][0]
        self.s.action(self.ctx,'finding.review',{'id':f['id'],'decision':'dismiss'})
        self.assertEqual(self.s.state(self.ctx)['contacts'][0]['tags'],[])
        self.analyze();f=self.s.state(self.ctx)['findings'][-1]
        self.s.action(self.ctx,'chat.update',{'id':self.c['id'],'status':'pending'})
        with self.assertRaisesRegex(Problem,'changed'):self.s.action(self.ctx,'finding.review',{'id':f['id'],'decision':'approve'})
        self.assertEqual(self.s.state(self.ctx)['findings'][-1]['status'],'pending')

    def test_invalid_or_foreign_evidence_and_unapproved_actions_rejected(self):
        for overrides in [{'contact_id':'other-business'}, {'evidence_ids':['invented-message']}, {'evidence_ids':[]}]:
            with self.assertRaises(Problem):self.analyze(**overrides)
        with self.assertRaises(Problem):self.analyze({'type':'send_message','body':'Buy now'})
        self.assertEqual(self.s.state(self.ctx)['findings'],[])
        self.assertTrue(all(r['status']=='failed' for r in self.s.state(self.ctx)['airuns']))

    def test_only_admin_can_review_and_foreign_workspaces_cannot_read_or_apply(self):
        self.analyze();f=self.s.state(self.ctx)['findings'][0]
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'another-long-password','role':'agent'})
        agent=self.s.auth(self.s.login('agent@example.test','another-long-password')['token'])
        with self.assertRaises(Problem) as e:self.s.action(agent,'finding.review',{'id':f['id'],'decision':'approve'})
        self.assertEqual(e.exception.code,403)
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        self.assertEqual(self.s.state(other)['findings'],[])
        with self.assertRaises(Problem):self.s.action(other,'finding.review',{'id':f['id'],'decision':'approve'})

    def test_approved_reply_is_a_draft_and_tasks_do_not_send(self):
        for action in [{'type':'draft_reply','body':'Here is a draft pricing reply.'},{'type':'task','title':'Prepare quotation'},{'type':'note','body':'Customer asked about pricing.'},{'type':'assign','owner':self.ctx['user']['id']}]:
            self.analyze(action);f=self.s.state(self.ctx)['findings'][-1]
            self.s.action(self.ctx,'finding.review',{'id':f['id'],'decision':'approve'})
        state=self.s.state(self.ctx)
        self.assertEqual(state['queue'],[])
        self.assertEqual([m['status'] for m in state['messages'] if m['direction']=='out'],['draft'])
        self.assertEqual(len(state['tasks']),1)
        self.assertEqual(state['contacts'][0]['assignee'],self.ctx['user']['id'])

    def test_malformed_provider_response_is_recorded_as_failed(self):
        with patch('store.ask_local',return_value='Not JSON'):
            with self.assertRaises(Problem):self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
        self.assertEqual(self.s.state(self.ctx)['airuns'][0]['status'],'failed')
        self.assertEqual(self.s.state(self.ctx)['findings'],[])

    def test_conversation_change_during_context_capture_invalidates_proposal(self):
        original=self.s._ai_context
        def capture_then_change(*args):
            captured=original(*args)
            self.s.action(self.ctx,'message.send',{'contact_id':self.c['id'],'body':'A teammate already addressed this.','note':True})
            return captured
        with patch.object(self.s,'_ai_context',side_effect=capture_then_change):self.analyze()
        f=self.s.state(self.ctx)['findings'][0]
        with self.assertRaisesRegex(Problem,'changed'):
            self.s.action(self.ctx,'finding.review',{'id':f['id'],'decision':'approve'})
        self.assertEqual(self.s.state(self.ctx)['contacts'][0]['tags'],[])
