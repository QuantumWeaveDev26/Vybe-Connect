import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class RuleActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'rules.db');token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
    def tearDown(self):self.tmp.cleanup()
    def save(self,actions,**changes):return self.s.action(self.ctx,'rule.save',dict({'name':'Support rule','keyword':'help','reply':'','enabled':True,'actions':actions},**changes))
    def incoming(self,id='incoming',text='help'):
        return self.s.inbound(self.ctx['tenant_id'],{'id':id,'from':'919000000001','text':{'body':text}})
    def test_ordered_actions_update_contact_and_make_one_task_on_replayed_inbound(self):
        self.save([{'type':'tag','value':'Lead'},{'type':'attribute','field':'topic','value':'Support'},{'type':'assign','value':self.ctx['user']['id']},{'type':'draft','value':'Team will help.'},{'type':'task','value':'Review request'},{'type':'handoff'}])
        self.incoming();self.incoming();state=self.s.state(self.ctx);contact=state['contacts'][0]
        self.assertIn('Lead',contact['tags']);self.assertEqual(contact['attributes']['topic'],'Support');self.assertEqual(contact['assignee'],self.ctx['user']['id']);self.assertTrue(contact['automation_hold']);self.assertEqual(len(state['tasks']),1)
        self.assertEqual(len([m for m in state['messages'] if m['status']=='draft']),1)
    def test_saved_segment_condition_controls_matching(self):
        segment=self.s.action(self.ctx,'segment.save',{'name':'VIP','criteria':{'field':'tags','operator':'contains','value':'VIP'}})
        self.save([{'type':'tag','value':'Matched'}],segment_id=segment['id']);self.incoming()
        state=self.s.state(self.ctx);self.assertNotIn('Matched',state['contacts'][0]['tags'])
        contact=state['contacts'][0];self.s.action(self.ctx,'contact.save',dict(contact,tags=['VIP']));self.incoming('second')
        self.assertIn('Matched',self.s.state(self.ctx)['contacts'][0]['tags'])
    def test_deleted_segment_blocks_instead_of_widening_rule(self):
        segment=self.s.action(self.ctx,'segment.save',{'name':'VIP','criteria':{'field':'name','operator':'not_empty'}})
        self.save([{'type':'tag','value':'Must not apply'}],segment_id=segment['id']);self.s.action(self.ctx,'segment.delete',{'id':segment['id']});self.incoming()
        self.assertNotIn('Must not apply',self.s.state(self.ctx)['contacts'][0]['tags'])
    def test_removed_member_blocks_all_actions_before_partial_mutation(self):
        member=self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'long-enough-password','role':'agent'})
        self.save([{'type':'tag','value':'Partial'},{'type':'assign','value':member['id']}])
        with self.s.db() as db:db.execute('DELETE FROM members WHERE tenant=? AND user=?',(self.ctx['tenant_id'],member['id']))
        self.incoming();self.assertNotIn('Partial',self.s.state(self.ctx)['contacts'][0]['tags'])
    def test_stop_and_human_takeover_suppress_actions(self):
        self.save([{'type':'task','value':'Must not create'}]);self.incoming(text='STOP');contact=self.s.state(self.ctx)['contacts'][0]
        self.s.action(self.ctx,'chat.takeover',{'id':contact['id']});self.incoming('held','help');self.assertEqual(self.s.state(self.ctx)['tasks'],[])
    def test_invalid_actions_and_foreign_references_rejected(self):
        for actions in [[],[{'type':'send','value':'Hi'}],[{'type':'assign','value':'foreign'}],[{'type':'attribute','field':'optin','value':True}],[{'type':'handoff'},{'type':'status','value':'open'}],[{'type':'status','value':'bad'}]]:
            with self.assertRaises(Problem):self.save(actions)
        with self.assertRaises(Problem):self.save([{'type':'tag','value':'VIP'}],segment_id='foreign')
    def test_tag_removal_and_status_changes(self):
        self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001','tags':['Old']})
        self.save([{'type':'untag','value':'Old'},{'type':'status','value':'solved'}]);self.incoming();contact=self.s.state(self.ctx)['contacts'][0]
        self.assertEqual(contact['tags'],[]);self.assertEqual(contact['status'],'solved')
    def test_actions_never_invoke_providers(self):
        self.save([{'type':'draft','value':'Unsent'},{'type':'task','value':'Local task'}])
        with patch('store.send_text') as send,patch('customer_assistant.ask_local') as ai:
            self.incoming();send.assert_not_called();ai.assert_not_called()

    def test_priority_selects_first_eligible_rule(self):
        self.save([{'type':'tag','value':'Low'}],priority=500)
        self.save([{'type':'tag','value':'High'}],priority=1);self.incoming();contact=self.s.state(self.ctx)['contacts'][0]
        self.assertIn('High',contact['tags']);self.assertNotIn('Low',contact['tags'])

    def test_legacy_reply_edit_updates_its_implicit_draft(self):
        rule=self.s.action(self.ctx,'rule.save',{'name':'Legacy','keyword':'help','reply':'Old reply','enabled':True})
        self.s.action(self.ctx,'rule.save',{'id':rule['id'],'name':'Legacy','keyword':'help','reply':'New reply','enabled':True});self.incoming()
        self.assertEqual(self.s.state(self.ctx)['messages'][-1]['body'],'New reply')

    def test_attribute_capacity_blocks_entire_rule_before_creating_draft(self):
        self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001','attributes':{str(n):'v' for n in range(50)}})
        self.save([{'type':'draft','value':'Must not create'},{'type':'attribute','field':'extra','value':'Too many'}]);self.incoming()
        self.assertFalse(any(m['status']=='draft' for m in self.s.state(self.ctx)['messages']))
