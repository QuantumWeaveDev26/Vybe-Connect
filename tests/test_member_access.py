import tempfile
import threading
import unittest
from pathlib import Path
from store import Store,Problem


class MemberAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'members.db');token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
        self.agent=self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'agent-long-password','role':'agent'})
        self.agent_token=self.s.login('agent@example.test','agent-long-password')['token']
    def tearDown(self):self.tmp.cleanup()
    def test_last_administrator_cannot_be_removed_or_demoted(self):
        for action,data in [('member.remove',{}),('member.role',{'role':'agent'})]:
            with self.assertRaises(Problem):self.s.action(self.ctx,action,dict(data,id=self.ctx['user']['id']))
        self.assertEqual(self.s.auth(self.agent_token)['role'],'agent')
    def test_promotion_and_demotion_change_next_request_permissions(self):
        self.s.action(self.ctx,'member.role',{'id':self.agent['id'],'role':'admin'});self.assertEqual(self.s.auth(self.agent_token)['role'],'admin')
        self.s.action(self.ctx,'member.role',{'id':self.agent['id'],'role':'agent'});self.assertEqual(self.s.auth(self.agent_token)['role'],'agent')
    def test_agent_and_stale_administrator_context_cannot_mutate_access(self):
        with self.assertRaises(Problem):self.s.action(self.s.auth(self.agent_token),'member.role',{'id':self.ctx['user']['id'],'role':'agent'})
        self.s.action(self.ctx,'member.role',{'id':self.agent['id'],'role':'admin'});old=self.s.auth(self.agent_token)
        self.s.action(self.ctx,'member.role',{'id':self.agent['id'],'role':'agent'})
        with self.assertRaises(Problem):self.s.action(old,'member.remove',{'id':self.ctx['user']['id']})
    def test_removal_is_workspace_scoped_and_clears_assignments(self):
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'});other_ctx=dict(self.ctx,tenant_id=other['id'])
        self.s.action(other_ctx,'member.add',{'email':'agent@example.test','role':'agent'})
        contact=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001'})
        self.s.action(self.ctx,'chat.update',{'id':contact['id'],'assignee':self.agent['id']})
        self.s.action(self.ctx,'task.save',{'title':'Follow up','contact_id':contact['id'],'owner':self.agent['id']})
        self.s.action(self.ctx,'member.remove',{'id':self.agent['id']})
        with self.assertRaises(Problem):self.s.auth(self.agent_token,self.ctx['tenant_id'])
        self.assertEqual(self.s.auth(self.agent_token,other['id'])['tenant_id'],other['id']);state=self.s.state(self.ctx)
        self.assertEqual(state['contacts'][0]['assignee'],'');self.assertEqual(state['tasks'][0]['owner'],'')
    def test_demoting_invitation_issuer_revokes_pending_links(self):
        self.s.action(self.ctx,'member.role',{'id':self.agent['id'],'role':'admin'});issuer=self.s.auth(self.agent_token)
        invite=self.s.action(issuer,'invite.create',{'email':'new@example.test','role':'agent'})
        self.s.action(self.ctx,'member.role',{'id':self.agent['id'],'role':'agent'})
        with self.assertRaises(Problem):self.s.inspect_invitation(invite['token'])
        self.assertEqual(self.s.state(self.ctx)['invitations'][0]['status'],'revoked')
    def test_concurrent_self_demotions_preserve_one_administrator(self):
        self.s.action(self.ctx,'member.role',{'id':self.agent['id'],'role':'admin'});second=self.s.auth(self.agent_token);results=[]
        def demote(ctx):
            try:self.s.action(ctx,'member.role',{'id':ctx['user']['id'],'role':'agent'});results.append('ok')
            except Problem:results.append('blocked')
        workers=[threading.Thread(target=demote,args=(ctx,)) for ctx in [self.ctx,second]]
        for worker in workers:worker.start()
        for worker in workers:worker.join()
        self.assertCountEqual(results,['ok','blocked'])
    def test_unknown_and_foreign_targets_are_rejected(self):
        for action in ['member.role','member.remove']:
            with self.assertRaises(Problem):self.s.action(self.ctx,action,{'id':'foreign','role':'agent'})
        with self.assertRaises(Problem):self.s.action(self.ctx,'member.role',{'id':self.agent['id'],'role':'owner'})
