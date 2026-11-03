import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class AgentPermissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'permissions.db');token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
        self.contact=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001'})
        with self.s.db() as db:self.msg=self.s._message(db,self.ctx['tenant_id'],self.contact['id'],'Please share prices','in','received')
        self.agent=self.save(['tag'])
    def tearDown(self):self.tmp.cleanup()
    def save(self,allowed,**extra):return self.s.action(self.ctx,'aiagent.save',dict({'name':'Sales','instructions':'Analyze purchase interest.','allowed_actions':allowed},**extra))
    def answer(self,action):return json.dumps({'summary':'Inquiry found','findings':[{'title':'Buyer inquiry','details':'Asks about price','contact_id':self.contact['id'],'evidence_ids':[self.msg['id']],'action':action}]})
    def analyze(self,action):
        with patch('store.ask_local',return_value=self.answer(action)) as model:
            result=self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']});return result,model.call_args.args[1]
    def finding(self):return self.s.state(self.ctx)['findings'][-1]
    def test_model_contract_exposes_only_selected_proposals(self):
        _,context=self.analyze({'type':'tag','tag':'Buyer'});self.assertEqual(set(context['analysis_contract']['allowed_proposals']),{'tag'})
    def test_disallowed_proposal_fails_without_publishing_findings(self):
        with self.assertRaises(Problem):self.analyze({'type':'task','title':'Follow up'})
        self.assertEqual(self.s.state(self.ctx)['findings'],[])
    def test_empty_permissions_allow_informational_findings_only(self):
        self.agent=self.save([],id=self.agent['id']);self.analyze(None)
        with self.assertRaises(Problem):self.analyze({'type':'tag','tag':'Buyer'})
    def test_invalid_permissions_are_rejected(self):
        for values in ['tag',None,[True],['send_message'],['tag']*6]:
            with self.assertRaises(Problem):self.save(values)
    def test_edit_without_permission_field_preserves_existing_selection(self):
        updated=self.s.action(self.ctx,'aiagent.save',{'id':self.agent['id'],'name':'Renamed','instructions':'Analyze facts.'});self.assertEqual(updated['allowed_actions'],['tag'])
    def test_permission_revocation_blocks_existing_pending_approval(self):
        self.analyze({'type':'tag','tag':'Buyer'});finding=self.finding();self.save([],id=self.agent['id'])
        with self.assertRaises(Problem):self.s.action(self.ctx,'finding.review',{'id':finding['id'],'decision':'approve'})
        self.assertEqual(self.s.state(self.ctx)['contacts'][0]['tags'],[])
        self.s.action(self.ctx,'finding.review',{'id':finding['id'],'decision':'dismiss'})
    def test_archived_agent_cannot_apply_pending_proposals(self):
        self.analyze({'type':'tag','tag':'Buyer'});finding=self.finding();self.s.action(self.ctx,'aiagent.archive',{'id':self.agent['id'],'archived':True})
        with self.assertRaises(Problem):self.s.action(self.ctx,'finding.review',{'id':finding['id'],'decision':'approve'})
    def test_edit_during_generation_discards_late_findings(self):
        def edit(*args):self.save([],id=self.agent['id']);return self.answer({'type':'tag','tag':'Buyer'})
        with patch('store.ask_local',side_effect=edit):
            with self.assertRaises(Problem):self.s.action(self.ctx,'ai.run',{'agent_id':self.agent['id']})
        self.assertEqual(self.s.state(self.ctx)['findings'],[])
    def test_legacy_agents_keep_existing_review_actions(self):
        legacy=self.s.action(self.ctx,'aiagent.save',{'name':'Legacy','instructions':'Review facts.'})
        self.assertEqual(set(legacy['allowed_actions']),{'tag','assign','note','draft_reply','task'})
