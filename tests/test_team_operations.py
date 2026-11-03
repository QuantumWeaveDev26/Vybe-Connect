import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from ai_handoff import handoff


class TeamOperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'teams.db')
        self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token']);self.t=self.ctx['tenant_id']
        self.a=self.s.action(self.ctx,'member.add',{'name':'A','email':'a@example.test','password':'long-enough-password','role':'agent'})
        self.b=self.s.action(self.ctx,'member.add',{'name':'B','email':'b@example.test','password':'long-enough-password','role':'agent'})
        self.agent=self.s.auth(self.s.login('a@example.test','long-enough-password')['token'])
        self.contact=self.s.action(self.ctx,'contact.save',{'name':'Customer','phone':'919000000001'})
    def tearDown(self):self.tmp.cleanup()
    def team(self,**changes):return self.s.action(self.ctx,'team.save',dict({'name':'Support','members':[self.a['id'],self.b['id']],'enabled':True},**changes))
    def availability(self,ctx,status='available',**changes):return self.s.action(ctx,'availability.set',dict({'status':status,'minutes':60},**changes))
    def route(self,team,contact=None,**changes):return self.s.action(self.ctx,'chat.route',dict({'id':(contact or self.contact)['id'],'team_id':team['id'],'strategy':'least_busy','respect_availability':True,'max_open':0},**changes))
    def test_team_requires_admin_and_current_workspace_members(self):
        with self.assertRaises(Problem):self.s.action(self.agent,'team.save',{'name':'No','members':[],'enabled':True})
        for members in [['foreign'],[True],'invalid']:
            with self.assertRaises(Problem):self.team(members=members)
        team=self.team();self.assertEqual(team['version'],1)
        with self.assertRaises(Problem):self.team(name='SUPPORT')
    def test_stale_team_editor_and_foreign_workspace_are_rejected(self):
        team=self.team();self.team(id=team['id'],version=1,name='Help')
        with self.assertRaises(Problem):self.team(id=team['id'],version=1)
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,tenant_id=other['id']),'team.save',dict(team,version=2))
    def test_personal_availability_cannot_target_another_member(self):
        self.availability(self.agent,user=self.b['id'])
        state=self.s.state(self.ctx)['team_operations'];available={x['user']:x for x in state['availability']}
        self.assertEqual(available[self.a['id']]['status'],'available');self.assertNotIn(self.b['id'],available)
        for values in [{'status':'online'},{'minutes':0},{'minutes':481},{'minutes':True}]:
            with self.assertRaises(Problem):self.availability(self.agent,**values)
    def test_unavailable_and_expired_members_are_not_assigned(self):
        team=self.team();result=self.route(team);self.assertEqual(result['assignee'],'')
        self.availability(self.agent);self.assertEqual(self.route(team)['assignee'],self.a['id'])
        self.s.action(self.ctx,'chat.update',{'id':self.contact['id'],'assignee':''})
        with patch('team_operations.time.time',return_value=9999999999):self.assertEqual(self.route(team)['assignee'],'')
    def test_routing_policy_cap_and_assignment_history(self):
        team=self.team();self.availability(self.agent);self.route(team)
        second=self.s.action(self.ctx,'contact.save',{'name':'Second','phone':'919000000002'})
        result=self.route(team,second,max_open=1);self.assertEqual(result['assignee'],'')
        events=self.s.state(self.ctx)['team_operations']['assignments'];self.assertTrue(any(e['contact_id']==self.contact['id'] and e['to']==self.a['id'] for e in events))
    def test_manual_routing_does_not_silently_replace_existing_assignment(self):
        team=self.team();self.s.action(self.ctx,'chat.update',{'id':self.contact['id'],'assignee':self.ctx['user']['id']})
        with self.assertRaises(Problem):self.route(team)
    def test_removed_member_is_pruned_from_teams_and_availability(self):
        team=self.team();self.availability(self.agent);self.s.action(self.ctx,'member.remove',{'id':self.a['id']})
        state=self.s.state(self.ctx)['team_operations'];self.assertNotIn(self.a['id'],state['teams'][0]['members']);self.assertEqual(state['availability'],[])
    def test_customer_ai_uses_current_team_and_explicit_availability_policy(self):
        team=self.team();self.availability(self.agent)
        assistant=self.s.action(self.ctx,'customer-assistant.save',{'name':'AI','instructions':'Use approved sources.','enabled':False,'mode':'draft','handoff_strategy':'least_busy','handoff_pool':[],'handoff_team_id':team['id'],'respect_availability':True,'handoff_max_open':1})
        with self.s.db() as db:
            db.execute('BEGIN IMMEDIATE');result=handoff(self.s,db,self.t,assistant,self.contact,{'id':'job'},'Needs support')
        self.assertEqual(result['assignee'],self.a['id'])
        self.assertEqual(result['handoff']['routing']['team_id'],team['id'])
    def test_disabled_team_does_not_fall_back_outside_team(self):
        team=self.team(enabled=False)
        with self.assertRaises(Problem):self.route(team)
    def test_concurrent_team_routing_observes_committed_workloads(self):
        team=self.team();self.availability(self.agent)
        bctx=self.s.auth(self.s.login('b@example.test','long-enough-password')['token']);self.availability(bctx)
        second=self.s.action(self.ctx,'contact.save',{'name':'Second','phone':'919000000002'})
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda c:self.route(team,c),[self.contact,second]))
        self.assertEqual({r['assignee'] for r in results},{self.a['id'],self.b['id']})

    def test_automation_assignments_are_recorded(self):
        self.s.action(self.ctx,'flow.save',{'name':'Assign','keyword':'help','reply':'Hello','enabled':True,'graph':{'start':'assign','nodes':[{'id':'assign','type':'assign','member_id':self.a['id']}]}})
        self.s.inbound(self.t,{'id':'flow-in','from':'919000000001','text':{'body':'help'}})
        self.s.action(self.ctx,'rule.save',{'name':'Assign B','keyword':'route','reply':'','enabled':True,'actions':[{'type':'assign','value':self.b['id']}]})
        self.s.inbound(self.t,{'id':'rule-in','from':'919000000001','text':{'body':'route'}})
        events=self.s.state(self.ctx)['team_operations']['assignments'];self.assertTrue(any(e['source']=='chatbot' and e['to']==self.a['id'] for e in events));self.assertTrue(any(e['source']=='rule' and e['to']==self.b['id'] for e in events))
    def test_stale_admin_cannot_change_customer_routing(self):
        self.s.action(self.ctx,'member.role',{'id':self.a['id'],'role':'admin'})
        with self.s.db() as db:db.execute("UPDATE members SET role='agent' WHERE tenant=? AND user=?",(self.t,self.ctx['user']['id']))
        with self.assertRaises(Problem):self.s.action(self.ctx,'customer-assistant.save',{'name':'AI','instructions':'Use knowledge','mode':'draft','enabled':False})
