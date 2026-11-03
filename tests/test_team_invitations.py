import json
import tempfile
import time
import unittest
import threading
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class InvitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'invites.db');self.owner_token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.owner_token)
    def tearDown(self):self.tmp.cleanup()
    def invite(self,**changes):return self.s.action(self.ctx,'invite.create',dict({'email':'invitee@example.test','role':'agent','hours':24},**changes))
    def accept(self,token,**changes):return self.s.accept_invitation(dict({'token':token,'name':'Invitee','password':'invitee-long-password'},**changes))
    def test_new_recipient_chooses_password_and_token_is_consumed_once(self):
        invite=self.invite();preview=self.s.inspect_invitation(invite['token']);self.assertEqual(preview['role'],'agent')
        accepted=self.accept(invite['token']);ctx=self.s.auth(accepted['token'],accepted['tenant_id']);self.assertEqual(ctx['role'],'agent');self.assertEqual(ctx['user']['email'],'invitee@example.test')
        with self.assertRaises(Problem):self.accept(invite['token'])
        self.s.login('invitee@example.test','invitee-long-password')
    def test_raw_token_and_hash_are_not_in_state_audit_or_stored_token(self):
        invite=self.invite();serialized=json.dumps(self.s.state(self.ctx));self.assertNotIn(invite['token'],serialized);self.assertNotIn('token_hash',serialized)
        with self.s.db() as db:
            raw=db.execute("SELECT data FROM entities WHERE kind='workspaceinvite'").fetchone()[0]
            self.assertNotIn(invite['token'],raw);self.assertIn('token_hash',raw)
    def test_expired_and_revoked_invites_cannot_be_inspected_or_accepted(self):
        invite=self.invite(hours=1)
        with patch('team_invitations.time.time',return_value=int(time.time())+3601):
            with self.assertRaises(Problem):self.s.inspect_invitation(invite['token'])
            with self.assertRaises(Problem):self.accept(invite['token'])
        self.s.action(self.ctx,'invite.revoke',{'id':invite['id']})
        with self.assertRaises(Problem):self.accept(invite['token'])
    def test_role_and_workspace_guards(self):
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,role='agent'),'invite.create',{'email':'x@example.test','role':'admin'})
        for changes in [{'role':'superadmin'},{'hours':0},{'hours':169},{'email':'bad'}]:
            with self.assertRaises(Problem):self.invite(**changes)
        invite=self.invite();other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,tenant_id=other['id']),'invite.revoke',{'id':invite['id']})
    def test_existing_account_requires_its_password_and_is_not_reset(self):
        self.s.action(self.ctx,'member.add',{'name':'Existing','email':'existing@example.test','password':'existing-long-password','role':'agent'})
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'});other_ctx=self.s.auth(self.owner_token,other['id'])
        invite=self.s.action(other_ctx,'invite.create',{'email':'existing@example.test','role':'agent','hours':24})
        self.assertTrue(self.s.inspect_invitation(invite['token'])['existing_account'])
        with self.assertRaises(Problem):self.accept(invite['token'],password='wrong-password')
        accepted=self.accept(invite['token'],password='existing-long-password',name='Must not rename');ctx=self.s.auth(accepted['token'],other['id']);self.assertEqual(ctx['user']['name'],'Existing')
        self.s.login('existing@example.test','existing-long-password')
    def test_issuer_losing_administrator_access_invalidates_invitation(self):
        invite=self.invite()
        with self.s.db() as db:db.execute("UPDATE members SET role='agent' WHERE tenant=? AND user=?",(self.ctx['tenant_id'],self.ctx['user']['id']))
        with self.assertRaises(Problem):self.accept(invite['token'])
    def test_failed_new_password_does_not_consume_invite(self):
        invite=self.invite()
        with self.assertRaises(Problem):self.accept(invite['token'],password='short')
        self.accept(invite['token'])
    def test_existing_workspace_member_cannot_be_silently_promoted(self):
        member=self.s.action(self.ctx,'member.add',{'name':'Agent','email':'member@example.test','password':'member-long-password','role':'agent'})
        with self.assertRaises(Problem):self.invite(email='member@example.test',role='admin')
    def test_duplicate_pending_email_requires_revoke_before_reissue(self):
        self.invite()
        with self.assertRaises(Problem):self.invite()

    def test_two_simultaneous_acceptances_create_one_membership(self):
        invite=self.invite();success=[];errors=[]
        def accept():
            try:success.append(self.accept(invite['token']))
            except Problem as error:errors.append(error)
        workers=[threading.Thread(target=accept) for _ in range(2)]
        for worker in workers:worker.start()
        for worker in workers:worker.join()
        self.assertEqual(len(success),1);self.assertEqual(len(errors),1)
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM members WHERE tenant=?',(self.ctx['tenant_id'],)).fetchone()[0],2)

    def test_invitation_created_before_membership_cannot_promote_later_member(self):
        invite=self.invite(role='admin')
        self.s.action(self.ctx,'member.add',{'name':'New agent','email':'invitee@example.test','password':'invitee-long-password','role':'agent'})
        with self.assertRaises(Problem):self.accept(invite['token'])
        self.assertEqual(self.s.auth(self.s.login('invitee@example.test','invitee-long-password')['token'])['role'],'agent')
