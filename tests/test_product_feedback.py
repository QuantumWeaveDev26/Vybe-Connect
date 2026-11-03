import tempfile
import unittest
from pathlib import Path
from store import Store,Problem


class ProductFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'feedback.db')
        self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'])
        self.member=self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'long-enough-password','role':'agent'})
        self.agent=self.s.auth(self.s.login('agent@example.test','long-enough-password')['token'])
    def tearDown(self):self.tmp.cleanup()
    def save(self,ctx=None,**values):return self.s.action(ctx or self.ctx,'feedback.save',dict({'rating':4,'body':'A useful improvement','category':'feedback','page':'external-agents'},**values))
    def test_report_persists_in_workspace_without_provider_effects(self):
        result=self.save();self.assertEqual(result['status'],'open');self.assertEqual(result['owner'],self.ctx['user']['id'])
        state=self.s.state(self.ctx);self.assertEqual(state['product_feedback'][0]['id'],result['id']);self.assertEqual(state['messages'],[])
    def test_agent_sees_only_own_reports_and_admin_sees_workspace_reports(self):
        owner=self.save();agent=self.save(self.agent)
        self.assertEqual([r['id'] for r in self.s.state(self.agent)['product_feedback']],[agent['id']]);self.assertEqual(len(self.s.state(self.ctx)['product_feedback']),2)
    def test_status_updates_require_current_admin_and_version(self):
        report=self.save(self.agent)
        with self.assertRaises(Problem):self.s.action(self.agent,'feedback.status',{'id':report['id'],'version':1,'status':'resolved'})
        changed=self.s.action(self.ctx,'feedback.status',{'id':report['id'],'version':1,'status':'reviewing'});self.assertEqual(changed['version'],2)
        with self.assertRaises(Problem):self.s.action(self.ctx,'feedback.status',{'id':report['id'],'version':1,'status':'resolved'})
    def test_foreign_workspace_and_removed_actor_cannot_mutate_feedback(self):
        report=self.save();other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,tenant_id=other['id']),'feedback.status',{'id':report['id'],'version':1,'status':'resolved'})
        self.s.action(self.ctx,'member.remove',{'id':self.member['id']})
        with self.assertRaises(Problem):self.save(self.agent)
    def test_invalid_or_empty_reports_are_rejected(self):
        for values in [{'rating':True},{'rating':6},{'rating':0,'body':''},{'body':'x'*4001},{'category':'payment'},{'page':'<script>'}]:
            with self.assertRaises(Problem):self.save(**values)
    def test_frequency_is_bounded(self):
        for _ in range(20):self.save()
        with self.assertRaises(Problem):self.save()
