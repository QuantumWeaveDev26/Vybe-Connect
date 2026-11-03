import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from store import Store, Problem


class CrmTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.s=Store(Path(self.tmp.name)/'crm.db')
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token']
        self.ctx=self.s.auth(self.token)
        self.c=self.s.action(self.ctx,'contact.save',{'name':'Customer','phone':'919000000001'})

    def tearDown(self):self.tmp.cleanup()

    def deal(self,**kw):
        return self.s.action(self.ctx,'deal.save',dict({'title':'Implementation','contact_id':self.c['id'],'amount_minor':129900,'currency':'INR','stage':'new','owner':self.ctx['user']['id']},**kw))

    def test_deals_and_tasks_persist_and_move_without_changing_inbox_status(self):
        d=self.deal()
        moved=self.deal(id=d['id'],stage='qualified')
        self.assertEqual(moved['stage'],'qualified')
        task=self.s.action(self.ctx,'task.save',{'title':'Arrange demo','contact_id':self.c['id'],'deal_id':d['id'],'owner':self.ctx['user']['id'],'due':'2026-11-03T10:00:00+05:30'})
        self.assertEqual(task['status'],'open')
        self.assertEqual(datetime.fromtimestamp(task['due'],timezone.utc).isoformat(),'2026-11-03T04:30:00+00:00')
        self.s.action(self.ctx,'task.complete',{'id':task['id'],'completed':True})
        state=Store(self.s.path).state(self.ctx)
        self.assertEqual(state['deals'][0]['amount_minor'],129900)
        self.assertEqual(state['tasks'][0]['status'],'done')
        self.assertEqual(state['contacts'][0]['status'],'open')
        self.assertEqual(state['queue'],[])

    def test_foreign_contacts_deals_and_members_are_rejected(self):
        d=self.deal()
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        for action,data in [('deal.save',dict(d)),('task.save',{'title':'Foreign','contact_id':self.c['id']}),('task.save',{'title':'Foreign','deal_id':d['id']})]:
            with self.assertRaises(Problem):self.s.action(other,action,data)
        self.assertEqual(self.s.state(other)['deals'],[])
        with self.assertRaises(Problem):self.deal(owner='not-a-member')

    def test_validates_money_stage_contact_task_links_and_due_time(self):
        for data in [{'amount_minor':1.1},{'amount_minor':True},{'amount_minor':-1},{'amount_minor':10**15},{'currency':'INVALID'},{'stage':'invented'}]:
            with self.assertRaises(Problem):self.deal(**data)
        d=self.deal()
        other=self.s.action(self.ctx,'contact.save',{'name':'Other','phone':'919000000002'})
        for data in [{'due':'2026-11-03T10:00'},{'due':'bad'},{'contact_id':other['id'],'deal_id':d['id']}]:
            with self.assertRaises(Problem):self.s.action(self.ctx,'task.save',dict({'title':'Follow up'},**data))

    def test_agents_can_manage_crm_and_task_completion_is_reversible(self):
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'a-long-agent-password','role':'agent'})
        agent=self.s.auth(self.s.login('agent@example.test','a-long-agent-password')['token'])
        t=self.s.action(agent,'task.save',{'title':'Call back','contact_id':self.c['id'],'owner':agent['user']['id']})
        self.s.action(agent,'task.complete',{'id':t['id'],'completed':True})
        self.s.action(agent,'task.complete',{'id':t['id'],'completed':False})
        self.assertEqual(self.s.state(agent)['tasks'][0]['status'],'open')

    def test_linked_task_prevents_deal_reassignment_to_another_contact(self):
        deal=self.deal()
        self.s.action(self.ctx,'task.save',{'title':'Follow up','deal_id':deal['id']})
        other=self.s.action(self.ctx,'contact.save',{'name':'Other','phone':'919000000002'})
        with self.assertRaisesRegex(Problem,'linked tasks'):
            self.deal(id=deal['id'],contact_id=other['id'])
        state=self.s.state(self.ctx)
        self.assertEqual(state['deals'][0]['contact_id'],self.c['id'])
        self.assertEqual(state['tasks'][0]['contact_id'],self.c['id'])
