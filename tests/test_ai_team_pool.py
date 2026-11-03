import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from store import Store,Problem
from ai_handoff import handoff


class AITeamPoolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'routing.db';self.s=Store(self.path)
        token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token);self.t=self.ctx['tenant_id']
        self.a=self.s.action(self.ctx,'member.add',{'name':'A','email':'a@example.test','password':'long-enough-password','role':'agent'})
        self.b=self.s.action(self.ctx,'member.add',{'name':'B','email':'b@example.test','password':'long-enough-password','role':'agent'})
        self.c=self.contact('Target','919000000001')
    def tearDown(self):self.tmp.cleanup()
    def contact(self,name,phone,**changes):return self.s.action(self.ctx,'contact.save',dict(name=name,phone=phone,**changes))
    def configure(self,**changes):
        return self.s.action(self.ctx,'customer-assistant.save',dict({'name':'Support','instructions':'Use business knowledge.','enabled':False,'mode':'draft','source_ids':[],'handoff_strategy':'least_busy','handoff_pool':[self.a['id'],self.b['id']],'handoff_task':True},**changes))
    def route(self,assistant,contact=None,job='job'):
        with self.s.db() as db:
            db.execute('BEGIN IMMEDIATE');c=self.s._get(db,self.t,'contact',(contact or self.c)['id'])
            return handoff(self.s,db,self.t,assistant,c,{'id':job},'Needs a teammate')
    def assign(self,contact,user,status='open'):
        self.s.action(self.ctx,'chat.update',{'id':contact['id'],'assignee':user,'status':status})
    def test_routes_to_least_busy_and_records_assignment_snapshot(self):
        assistant=self.configure();busy=self.contact('Busy','919000000002');self.assign(busy,self.a['id'])
        result=self.route(assistant);self.assertEqual(result['assignee'],self.b['id']);self.assertEqual(result['handoff']['routing']['strategy'],'least_busy');self.assertEqual(result['handoff']['routing']['assigned_load'],0)
        self.assertEqual(self.s.state(self.ctx)['tasks'][0]['owner'],self.b['id'])
    def test_preserves_existing_assignment_outside_pool(self):
        assistant=self.configure();self.assign(self.c,self.ctx['user']['id']);result=self.route(assistant)
        self.assertEqual(result['assignee'],self.ctx['user']['id']);self.assertEqual(result['handoff']['routing']['strategy'],'preserved')
    def test_solved_work_does_not_count_and_ties_follow_pool_order(self):
        assistant=self.configure(handoff_pool=[self.b['id'],self.a['id']]);busy=self.contact('Solved','919000000002');self.assign(busy,self.b['id'],'solved')
        self.assertEqual(self.route(assistant)['assignee'],self.b['id'])
    def test_removed_member_is_ignored_and_empty_pool_falls_back(self):
        assistant=self.configure()
        self.s.action(self.ctx,'member.remove',{'id':self.a['id']});self.assertEqual(self.route(assistant)['assignee'],self.b['id'])
        other=self.contact('Other','919000000003');self.s.action(self.ctx,'member.remove',{'id':self.b['id']})
        self.assertEqual(self.route(assistant,other,'second')['assignee'],self.ctx['user']['id'])
    def test_invalid_pool_and_strategy_are_rejected(self):
        for values in [{'handoff_pool':[]},{'handoff_pool':['foreign']},{'handoff_pool':[self.a['id']]*51},{'handoff_pool':'bad'},{'handoff_pool':[True]},{'handoff_strategy':'random'}]:
            with self.assertRaises(Problem):self.configure(**values)
    def test_fixed_mode_retains_existing_behavior(self):
        assistant=self.configure(handoff_strategy='fixed',handoff_pool=[],handoff_assignee=self.b['id']);self.assertEqual(self.route(assistant)['assignee'],self.b['id'])
    def test_workload_from_other_workspace_does_not_affect_routing(self):
        assistant=self.configure();other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        with self.s.db() as db:self.s._put(db,other['id'],'contact',dict(self.c,assignee=self.a['id'],status='open'))
        self.assertEqual(self.route(assistant)['assignee'],self.a['id'])
    def test_concurrent_handoffs_observe_each_other(self):
        assistant=self.configure();other=self.contact('Other','919000000002')
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda args:self.route(assistant,*args),[(self.c,'one'),(other,'two')]))
        self.assertEqual({r['assignee'] for r in results},{self.a['id'],self.b['id']})
    def test_round_robin_persists_rotation_and_preserves_existing_assignee(self):
        assistant=self.configure(handoff_strategy='round_robin');first=self.route(assistant);self.assertEqual(first['assignee'],self.a['id'])
        self.s=Store(self.path);second=self.contact('Second','919000000002');self.assertEqual(self.route(assistant,second,'second')['assignee'],self.b['id'])
        self.route(assistant,second,'preserved');third=self.contact('Third','919000000003');self.assertEqual(self.route(assistant,third,'third')['assignee'],self.a['id'])
    def test_round_robin_ignores_removed_members(self):
        assistant=self.configure(handoff_strategy='round_robin');self.route(assistant);self.s.action(self.ctx,'member.remove',{'id':self.a['id']});other=self.contact('Other','919000000002');self.assertEqual(self.route(assistant,other,'other')['assignee'],self.b['id'])
    def test_competing_round_robin_handoffs_do_not_pick_same_slot(self):
        assistant=self.configure(handoff_strategy='round_robin');other=self.contact('Other','919000000002')
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda args:self.route(assistant,*args),[(self.c,'one'),(other,'two')]))
        self.assertEqual({r['assignee'] for r in results},{self.a['id'],self.b['id']})
