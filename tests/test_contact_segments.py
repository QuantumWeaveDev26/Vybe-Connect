import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class SegmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'segments.db')
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
        self.a=self.s.action(self.ctx,'contact.save',{'name':'Alpha','phone':'919000000001','optin':True,'tags':['Buyer'],'attributes':{'score':90,'city':'Pune','renewal':'2026-11-01'}})
        self.b=self.s.action(self.ctx,'contact.save',{'name':'Beta','phone':'919000000002','optin':False,'tags':['Lead'],'attributes':{'score':40,'city':'Delhi'}})
    def tearDown(self):self.tmp.cleanup()
    def criteria(self):return {'mode':'all','rules':[{'field':'tags','operator':'contains','value':'Buyer'},{'field':'attributes.score','operator':'gte','value':80}]}
    def save(self):return self.s.action(self.ctx,'segment.save',{'name':'High intent','criteria':self.criteria()})
    def preview(self,criteria):return self.s.action(self.ctx,'segment.preview',{'criteria':criteria})

    def test_typed_all_any_matching_and_persistence(self):
        segment=self.save();self.assertEqual(Store(self.s.path).state(self.ctx)['segments'][0]['id'],segment['id'])
        self.assertEqual(self.preview(self.criteria())['contact_ids'],[self.a['id']])
        any_rule={'mode':'any','rules':[{'field':'optin','operator':'eq','value':False},{'field':'attributes.city','operator':'eq','value':'Pune'}]}
        self.assertEqual(self.preview(any_rule)['count'],2)

    def test_date_numeric_and_missing_value_comparisons(self):
        self.assertEqual(self.preview({'mode':'all','rules':[{'field':'attributes.renewal','operator':'date_after','value':'2026-10-29'}]})['contact_ids'],[self.a['id']])
        self.assertEqual(self.preview({'mode':'all','rules':[{'field':'attributes.renewal','operator':'not_exists'}]})['contact_ids'],[self.b['id']])
        self.assertFalse(self.preview({'mode':'all','rules':[{'field':'attributes.score','operator':'eq','value':'90'}]})['contact_ids'])

    def test_invalid_conditions_are_rejected_without_eval(self):
        for criteria in [{'mode':'eval','rules':[]},{'mode':'all','rules':[{'field':'__class__','operator':'eq','value':'x'}]},{'mode':'all','rules':[{'field':'optin','operator':'eq','value':'true'}]},{'mode':'all','rules':[{'field':'name','operator':'regex','value':'.*'}]}]:
            with self.subTest(criteria=criteria),self.assertRaises(Problem):self.preview(criteria)

    def test_segment_is_workspace_scoped_and_agents_can_only_preview(self):
        segment=self.save();other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        self.assertFalse(self.s.state(other)['segments'])
        with self.assertRaises(Problem):self.s.action(other,'segment.delete',{'id':segment['id']})
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'another-long-password','role':'agent'})
        agent=self.s.auth(self.s.login('agent@example.test','another-long-password')['token'])
        self.assertEqual(self.s.action(agent,'segment.preview',{'criteria':self.criteria()})['count'],1)
        with self.assertRaises(Problem):self.s.action(agent,'segment.save',{'name':'Denied','criteria':self.criteria()})

    def test_campaign_resolves_current_segment_and_rechecks_consent(self):
        segment=self.save()
        with self.s.db() as db:template=self.s._put(db,self.ctx['tenant_id'],'template',{'name':'offer','body':'Hello','language':'en','status':'APPROVED','meta_id':'123'})
        campaign=self.s.action(self.ctx,'campaign.save',{'name':'Segment campaign','template_id':template['id'],'segment_id':segment['id']})
        self.assertEqual(campaign['audience'],1)
        self.s.action(self.ctx,'contact.save',{'id':self.b['id'],'name':'Beta','phone':'919000000002','optin':True,'tags':['Buyer'],'attributes':{'score':100}})
        with patch('store.meta_status',return_value={'live':True}):self.s.action(self.ctx,'campaign.launch',{'id':campaign['id']})
        self.assertEqual(len(self.s.state(self.ctx)['queue']),2)

    def test_deleted_segment_blocks_launch_instead_of_broadcasting_to_all(self):
        segment=self.save()
        with self.s.db() as db:template=self.s._put(db,self.ctx['tenant_id'],'template',{'name':'offer','body':'Hello','language':'en','status':'APPROVED','meta_id':'123'})
        campaign=self.s.action(self.ctx,'campaign.save',{'name':'Scoped','template_id':template['id'],'segment_id':segment['id']})
        self.s.action(self.ctx,'segment.delete',{'id':segment['id']})
        with patch('store.meta_status',return_value={'live':True}),self.assertRaises(Problem):self.s.action(self.ctx,'campaign.launch',{'id':campaign['id']})
        self.assertFalse(self.s.state(self.ctx)['queue'])
