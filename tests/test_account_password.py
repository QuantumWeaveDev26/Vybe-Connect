import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class AccountPasswordTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'account.db';self.s=Store(self.path);self.old='long-enough-password';self.new='a-new-long-password';self.token=self.s.setup('Owner','owner@example.test',self.old,'Acme')['token'];self.ctx=self.s.auth(self.token)
    def tearDown(self):self.tmp.cleanup()
    def test_verified_change_revokes_all_sessions_and_preserves_workspaces(self):
        other_token=self.s.login('owner@example.test',self.old)['token'];workspace=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        self.s.change_password(self.ctx,self.old,self.new)
        for token in [self.token,other_token]:
            with self.assertRaises(Problem):self.s.auth(token)
        with self.assertRaises(Problem):self.s.login('owner@example.test',self.old)
        login=self.s.login('owner@example.test',self.new);self.assertEqual(self.s.auth(login['token'],workspace['id'])['tenant_id'],workspace['id'])
    def test_wrong_current_password_does_not_change_credentials_or_sessions(self):
        with self.assertRaises(Problem):self.s.change_password(self.ctx,'wrong-password',self.new)
        self.assertEqual(self.s.auth(self.token)['user']['id'],self.ctx['user']['id'])
    def test_invalid_or_identical_new_password_is_rejected(self):
        for value in [self.old,'short',None,'x'*257]:
            with self.assertRaises(Problem):self.s.change_password(self.ctx,self.old,value)
    def test_operator_recovery_is_global_but_does_not_grant_memberships(self):
        self.s.operator_reset_password('owner@example.test',self.new)
        with self.assertRaises(Problem):self.s.auth(self.token)
        ctx=self.s.auth(self.s.login('owner@example.test',self.new)['token']);self.assertEqual(len(ctx['workspaces']),1)
    def test_unknown_recovery_target_does_not_create_account(self):
        with self.assertRaises(Problem):self.s.operator_reset_password('missing@example.test',self.new)
        self.assertEqual(self.s.auth(self.token)['user']['id'],self.ctx['user']['id'])
    def test_concurrent_changes_cannot_both_use_old_password(self):
        def change(index):
            try:self.s.change_password(self.ctx,self.old,self.new+str(index));return True
            except Problem:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(change,range(2)))
        self.assertEqual(sum(results),1)
    def test_other_accounts_keep_their_sessions_and_credentials(self):
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':self.old,'role':'agent'});agent=self.s.login('agent@example.test',self.old)['token'];self.s.change_password(self.ctx,self.old,self.new)
        self.assertEqual(self.s.auth(agent)['user']['email'],'agent@example.test')
    def test_old_login_cannot_create_a_session_after_password_recovery(self):
        from store import password_hash
        def recover_during_hash(password,salt):
            if password==self.old:self.s.operator_reset_password('owner@example.test',self.new)
            return password_hash(password,salt)
        with patch('store.password_hash',side_effect=recover_during_hash):
            with self.assertRaises(Problem):self.s.login('owner@example.test',self.old)
    def test_recovery_refuses_to_create_a_missing_database(self):
        from recover_account import existing_store
        missing=Path(self.tmp.name)/'missing.db'
        with self.assertRaises(ValueError):existing_store(missing,'owner@example.test')
        self.assertFalse(missing.exists())
