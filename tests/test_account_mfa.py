import base64
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from store import Store, Problem
from account_mfa import totp


class MFATests(unittest.TestCase):
    def setUp(self):
        self.clock=patch('account_mfa.time.time',return_value=1800000000);self.clock.start()
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'mfa.db')
        self.password='long-enough-password';self.email='owner@example.test'
        self.token=self.s.setup('Owner',self.email,self.password,'Acme')['token'];self.ctx=self.s.auth(self.token)
    def tearDown(self):self.clock.stop();self.tmp.cleanup()
    def enroll(self):
        enrollment=self.s.account_mfa(self.ctx,'begin',{'current_password':self.password})
        self.secret=enrollment['secret']
        result=self.s.account_mfa(self.ctx,'confirm',{'current_password':self.password,'code':totp(self.secret,1800000000)})
        self.codes=result['recovery_codes'];return result
    def test_rfc_6238_sha1_vectors(self):
        secret=base64.b32encode(b'12345678901234567890').decode()
        for stamp,expected in [(59,'94287082'),(1111111109,'07081804'),(1111111111,'14050471'),(1234567890,'89005924'),(2000000000,'69279037'),(20000000000,'65353130')]:
            self.assertEqual(totp(secret,stamp,digits=8),expected)
    def test_enrollment_requires_password_and_proof_before_enabling(self):
        with self.assertRaises(Problem):self.s.account_mfa(self.ctx,'begin',{'current_password':'wrong'})
        pending=self.s.account_mfa(self.ctx,'begin',{'current_password':self.password})
        self.assertFalse(self.s.mfa_status(self.ctx)['enabled'])
        with self.assertRaises(Problem):self.s.account_mfa(self.ctx,'confirm',{'current_password':self.password,'code':'invalid'})
        self.assertIn('token',self.s.login(self.email,self.password))
        self.assertIn('secret',pending)
    def test_enable_revokes_sessions_and_password_alone_cannot_login(self):
        self.enroll()
        with self.assertRaises(Problem):self.s.auth(self.token)
        with self.assertRaises(Problem):self.s.login(self.email,self.password)
        with self.assertRaises(Problem):self.s.login(self.email,self.password,totp(self.secret,1800000000))
        login=self.s.login(self.email,self.password,totp(self.secret,1800000030));self.assertEqual(self.s.auth(login['token'])['user']['email'],self.email)
    def test_login_code_cannot_be_replayed_even_concurrently(self):
        self.enroll();code=totp(self.secret,1800000030)
        def login(_):
            try:self.s.login(self.email,self.password,code);return True
            except Problem:return False
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sum(pool.map(login,range(2))),1)
    def test_recovery_codes_are_hashed_and_single_use(self):
        self.enroll();self.s.login(self.email,self.password,self.codes[0])
        with self.assertRaises(Problem):self.s.login(self.email,self.password,self.codes[0])
        with self.s.db() as db:
            raw=json.dumps(dict(db.execute('SELECT * FROM account_mfa').fetchone()))
            self.assertNotIn(self.codes[1],raw)
        self.assertEqual(self.s.mfa_status(self.ctx)['recovery_remaining'],9)
    def test_wrong_password_does_not_consume_recovery_code(self):
        self.enroll()
        with self.assertRaises(Problem):self.s.login(self.email,'wrong-password',self.codes[0])
        self.s.login(self.email,self.password,self.codes[0])
    def test_expired_enrollment_is_rejected(self):
        pending=self.s.account_mfa(self.ctx,'begin',{'current_password':self.password})
        with patch('account_mfa.time.time',return_value=1800000601):
            with self.assertRaises(Problem):self.s.account_mfa(self.ctx,'confirm',{'current_password':self.password,'code':totp(pending['secret'],1800000601)})
    def test_status_and_workspace_state_do_not_expose_secrets(self):
        self.enroll();public=json.dumps(self.s.mfa_status(self.ctx))+json.dumps(self.s.state(self.ctx))
        self.assertNotIn(self.secret,public)
        for code in self.codes:self.assertNotIn(code,public)
    def test_disable_requires_second_factor_and_revokes_sessions(self):
        self.enroll();token=self.s.login(self.email,self.password,self.codes[0])['token'];ctx=self.s.auth(token)
        with self.assertRaises(Problem):self.s.account_mfa(ctx,'disable',{'current_password':self.password,'code':'bad'})
        self.s.account_mfa(ctx,'disable',{'current_password':self.password,'code':self.codes[1]})
        with self.assertRaises(Problem):self.s.auth(token)
        self.s.login(self.email,self.password)
    def test_revoked_session_context_cannot_modify_security(self):
        self.enroll()
        with self.assertRaises(Problem):self.s.account_mfa(self.ctx,'disable',{'current_password':self.password,'code':self.codes[0]})
    def test_rotation_invalidates_previous_recovery_codes(self):
        self.enroll();ctx=self.s.auth(self.s.login(self.email,self.password,self.codes[0])['token'])
        new=self.s.account_mfa(ctx,'recovery',{'current_password':self.password,'code':self.codes[1]})['recovery_codes']
        with self.assertRaises(Problem):self.s.login(self.email,self.password,self.codes[2])
        self.s.login(self.email,self.password,new[0])
    def test_password_operator_recovery_preserves_mfa(self):
        self.enroll();new='another-long-password';self.s.operator_reset_password(self.email,new)
        with self.assertRaises(Problem):self.s.login(self.email,new)
        self.s.login(self.email,new,self.codes[0])
    def test_invitation_existing_account_cannot_bypass_mfa(self):
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        self.s.action(self.ctx,'member.add',{'name':'Second admin','email':'second@example.test','password':self.password,'role':'admin'})
        second=self.s.auth(self.s.login('second@example.test',self.password)['token'])
        # Owner leaves the first workspace; another admin can invite them back.
        self.s.action(second,'member.remove',{'id':self.ctx['user']['id']})
        self.ctx=self.s.auth(self.token,other['id']);self.enroll()
        invite=self.s.action(second,'invite.create',{'email':self.email,'role':'agent','hours':1})
        with self.assertRaises(Problem):self.s.accept_invitation({'token':invite['token'],'password':self.password})
        result=self.s.accept_invitation({'token':invite['token'],'password':self.password,'code':self.codes[0]})
        self.assertIn('token',result)
