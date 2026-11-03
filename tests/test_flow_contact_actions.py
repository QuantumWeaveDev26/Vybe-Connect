import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class FlowContactActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'flow.db');token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
        self.member=self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'long-enough-password','role':'agent'})
        self.c=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001','tags':['Old','Keep']})
    def tearDown(self):self.tmp.cleanup()
    def save(self,nodes):return self.s.action(self.ctx,'flow.save',{'name':'Route buyer','keyword':'help','reply':'Hello','enabled':True,'graph':{'start':nodes[0]['id'],'nodes':nodes}})
    def incoming(self):return self.s.inbound(self.ctx['tenant_id'],{'id':'incoming','from':'919000000001','text':{'body':'help'}})
    def state(self):return self.s.state(self.ctx)
    def test_attribute_remove_tag_assignment_and_rendered_draft_are_persistent(self):
        self.save([{'id':'set','type':'attribute','field':'service','value':'Support for {{name}}','next':'remove'},{'id':'remove','type':'untag','tag':'OLD','next':'assign'},{'id':'assign','type':'assign','member_id':self.member['id'],'next':'reply'},{'id':'reply','type':'message','text':'{{service}}'}]);self.incoming();state=self.state();c=state['contacts'][0]
        self.assertEqual(c['attributes']['service'],'Support for Buyer');self.assertEqual(c['tags'],['Keep']);self.assertEqual(c['assignee'],self.member['id']);self.assertEqual(state['messages'][-1]['body'],'Support for Buyer');self.assertFalse(c.get('automation_hold'))
    def test_invalid_nodes_and_foreign_assignments_rejected(self):
        for node in [{'type':'attribute','field':'bad.path','value':'x'},{'type':'attribute','field':'ok','value':'x'*1001},{'type':'untag','tag':''},{'type':'assign','member_id':'foreign'}]:
            with self.assertRaises(Problem):self.save([dict(node,id='bad')])
    def test_removed_member_blocks_entire_flow_and_keeps_inbound(self):
        self.save([{'id':'draft','type':'message','text':'Must not publish','next':'assign'},{'id':'assign','type':'assign','member_id':self.member['id']}]);self.s.action(self.ctx,'member.remove',{'id':self.member['id']});self.incoming();state=self.state();c=state['contacts'][0]
        self.assertTrue(c['automation_hold']);self.assertEqual(c['flow_last_event']['status'],'blocked');self.assertEqual([m for m in state['messages'] if m['direction']=='out'],[]);self.assertTrue(any(m['direction']=='in' for m in state['messages']))
    def test_attribute_capacity_failure_discards_prior_node_changes(self):
        self.s.action(self.ctx,'contact.save',dict(self.c,attributes={str(i):'value' for i in range(50)}))
        self.save([{'id':'tag','type':'tag','tag':'New','next':'set'},{'id':'set','type':'attribute','field':'extra','value':'Overflow'}]);self.incoming();c=self.state()['contacts'][0]
        self.assertNotIn('New',c['tags']);self.assertNotIn('extra',c['attributes']);self.assertTrue(c['automation_hold'])
    def test_existing_attribute_can_change_at_capacity(self):
        self.s.action(self.ctx,'contact.save',dict(self.c,attributes={str(i):'value' for i in range(50)}));self.save([{'id':'set','type':'attribute','field':'1','value':'Changed'}]);self.incoming();c=self.state()['contacts'][0]
        self.assertEqual(c['attributes']['1'],'Changed');self.assertFalse(c.get('automation_hold'))
    def test_timer_cancels_after_member_removal_without_repeated_retry(self):
        with patch('store.now',return_value=100000):
            self.save([{'id':'wait','type':'wait','seconds':60,'next':'assign'},{'id':'assign','type':'assign','member_id':self.member['id']}]);self.incoming()
        self.s.action(self.ctx,'member.remove',{'id':self.member['id']})
        with patch('store.now',return_value=100060):self.assertTrue(self.s.process_flow_wait_once());self.assertFalse(self.s.process_flow_wait_once())
        c=self.state()['contacts'][0];self.assertNotIn('flow_session',c);self.assertEqual(c['flow_last_event']['status'],'blocked')
    def test_tag_capacity_is_not_silently_truncated(self):
        self.s.action(self.ctx,'contact.save',dict(self.c,tags=[str(i) for i in range(25)]));self.save([{'id':'tag','type':'tag','tag':'Overflow'}]);self.incoming();c=self.state()['contacts'][0]
        self.assertEqual(len(c['tags']),25);self.assertTrue(c['automation_hold'])
    def test_expanded_attribute_value_is_bounded_without_partial_drafts(self):
        self.s.action(self.ctx,'contact.save',dict(self.c,attributes={'large':'x'*700}));self.save([{'id':'set','type':'attribute','field':'copy','value':'{{large}}{{large}}'}]);self.incoming();c=self.state()['contacts'][0]
        self.assertNotIn('copy',c['attributes']);self.assertTrue(c['automation_hold'])
