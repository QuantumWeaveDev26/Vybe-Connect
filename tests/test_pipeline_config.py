import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class PipelineConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'pipeline.db');self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token']);self.c=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001'})
        self.stages=[{'id':'new','label':'New'},{'id':'demo','label':'Demo scheduled'},{'id':'won','label':'Won'},{'id':'lost','label':'Lost'}]
    def tearDown(self):self.tmp.cleanup()
    def configure(self,**changes):return self.s.action(self.ctx,'pipeline.save',dict({'stages':self.stages,'closure_days':10},**changes))
    def deal(self,**changes):return self.s.action(self.ctx,'deal.save',dict({'title':'Opportunity','contact_id':self.c['id'],'stage':'new'},**changes))
    def test_custom_stage_and_default_closure_deadline(self):
        self.configure();deal=self.deal(stage='demo');self.assertEqual(deal['stage'],'demo');self.assertEqual(deal['closure_due'],deal['created']+10*86400)
    def test_stage_in_use_cannot_be_removed(self):
        self.configure();self.deal(stage='demo')
        with self.assertRaises(Problem):self.configure(stages=[s for s in self.stages if s['id']!='demo'])
    def test_invalid_and_duplicate_stages_are_rejected(self):
        for stages in [[],[{'id':'new','label':'New'}],self.stages+[{'id':'demo','label':'Duplicate'}],self.stages+[{'id':'bad.path','label':'Bad'}]]:
            with self.assertRaises(Problem):self.configure(stages=stages)
        with self.assertRaises(Problem):self.configure(closure_days=True)
    def test_moves_record_one_transition_and_closure_time(self):
        self.configure();deal=self.deal();self.deal(id=deal['id'],stage='demo');self.deal(id=deal['id'],stage='demo');won=self.deal(id=deal['id'],stage='won')
        history=self.s.state(self.ctx)['pipeline']['events'];self.assertEqual(len(history),3);self.assertGreater(won['closed_at'],0)
    def test_configuration_is_workspace_scoped(self):
        self.configure();other=self.s.auth(self.s.login('owner@example.test','long-enough-password')['token'],self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        self.assertNotIn('demo',[s['id'] for s in self.s.state(other)['pipeline']['stages']])
    def test_agent_cannot_change_pipeline_configuration(self):
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'long-enough-password','role':'agent'});agent=self.s.auth(self.s.login('agent@example.test','long-enough-password')['token'])
        with self.assertRaises(Problem):self.s.action(agent,'pipeline.save',{'stages':self.stages,'closure_days':10})
    def test_terminal_change_refreshes_closure_time_and_reopening_clears_it(self):
        self.configure();deal=self.deal()
        with patch('crm.time.time',return_value=200000):won=self.deal(id=deal['id'],stage='won')
        with patch('crm.time.time',return_value=200100):lost=self.deal(id=deal['id'],stage='lost')
        self.assertEqual(lost['closed_at'],200100);self.assertEqual(self.deal(id=deal['id'],stage='demo')['closed_at'],0)
