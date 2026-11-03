import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from password_recovery import token_for


ENV={'TW_RECOVERY_ENABLED':'true','TW_RECOVERY_SECRET':'test-only-'+('a'*48),'TW_PUBLIC_ORIGIN':'https://chat.example.test','TW_SMTP_HOST':'mail.example.test','TW_SMTP_FROM':'support@example.test','TW_SMTP_SECURITY':'ssl','TW_SMTP_USERNAME':'','TW_SMTP_PASSWORD':''}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,ENV);self.env.start();self.clock=patch('password_recovery.time.time',return_value=1800000000);self.clock.start()
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'reset.db');self.password='long-enough-password';self.email='owner@example.test'
        self.token=self.s.setup('Owner',self.email,self.password,'Acme')['token'];self.ctx=self.s.auth(self.token)
    def tearDown(self):self.tmp.cleanup();self.clock.stop();self.env.stop()
    def request(self):
        self.s.request_password_reset(self.email)
        with self.s.db() as db:
            row=db.execute('SELECT * FROM password_resets ORDER BY created DESC,id DESC LIMIT 1').fetchone();user=db.execute('SELECT * FROM users WHERE email=?',(self.email,)).fetchone()
        return token_for(row['id'],user)
    def test_known_unknown_and_disabled_have_identical_public_responses(self):
        known=self.s.request_password_reset(self.email);unknown=self.s.request_password_reset('missing@example.test')
        with patch.dict(os.environ,{'TW_RECOVERY_ENABLED':'false'}):disabled=self.s.request_password_reset(self.email)
        self.assertEqual(known,unknown);self.assertEqual(known,disabled);self.assertNotIn('token',json.dumps(known))
    def test_success_revokes_all_sessions_and_does_not_login(self):
        reset=self.request();result=self.s.complete_password_reset(reset,'a-new-long-password')
        self.assertNotIn('token',result)
        with self.assertRaises(Problem):self.s.auth(self.token)
        with self.assertRaises(Problem):self.s.login(self.email,self.password)
        self.s.login(self.email,'a-new-long-password')
    def test_token_is_not_stored_in_plaintext_or_public_state(self):
        reset=self.request()
        with self.s.db() as db:raw=json.dumps([dict(r) for r in db.execute('SELECT * FROM password_resets')])
        self.assertNotIn(reset,raw);self.assertNotIn(reset,json.dumps(self.s.state(self.ctx)))
    def test_expired_altered_and_replayed_links_are_rejected(self):
        reset=self.request()
        with self.assertRaises(Problem):self.s.complete_password_reset(reset+'x','a-new-long-password')
        with patch('password_recovery.time.time',return_value=1800000901):
            with self.assertRaises(Problem):self.s.complete_password_reset(reset,'a-new-long-password')
        self.s.complete_password_reset(reset,'a-new-long-password')
        with self.assertRaises(Problem):self.s.complete_password_reset(reset,'another-long-password')
    def test_invalid_new_password_does_not_consume_the_link(self):
        reset=self.request()
        with self.assertRaises(Problem):self.s.complete_password_reset(reset,'short')
        self.s.complete_password_reset(reset,'a-new-long-password')
    def test_concurrent_consumers_cannot_both_reset(self):
        reset=self.request()
        def consume(i):
            try:self.s.complete_password_reset(reset,'a-new-long-password'+str(i));return True
            except Problem:return False
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sum(pool.map(consume,range(2))),1)
    def test_password_change_and_key_rotation_invalidate_links(self):
        reset=self.request();self.s.change_password(self.ctx,self.password,'changed-long-password')
        with self.assertRaises(Problem):self.s.complete_password_reset(reset,'a-new-long-password')
        with patch('password_recovery.time.time',return_value=1800000061):reset=self.request()
        with patch.dict(os.environ,{'TW_RECOVERY_SECRET':'different-'+('b'*48)}):
            with self.assertRaises(Problem):self.s.complete_password_reset(reset,'a-new-long-password')
    def test_requests_are_persistently_bounded_without_locking_account(self):
        self.request();self.s.request_password_reset(self.email)
        for stamp in [1800000061,1800000122,1800000183]:
            with patch('password_recovery.time.time',return_value=stamp):self.s.request_password_reset(self.email)
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM password_resets').fetchone()[0],3)
        self.s.login(self.email,self.password)
    def test_reset_preserves_mfa_and_memberships(self):
        from account_mfa import totp
        secret=self.s.account_mfa(self.ctx,'begin',{'current_password':self.password})['secret'];codes=self.s.account_mfa(self.ctx,'confirm',{'current_password':self.password,'code':totp(secret,1800000000)})['recovery_codes']
        reset=self.request();self.s.complete_password_reset(reset,'a-new-long-password')
        with self.assertRaises(Problem):self.s.login(self.email,'a-new-long-password')
        ctx=self.s.auth(self.s.login(self.email,'a-new-long-password',codes[0])['token']);self.assertEqual(ctx['tenant_id'],self.ctx['tenant_id'])
    def test_worker_uses_public_origin_and_submits_only_once(self):
        reset=self.request()
        with patch('password_recovery.send_recovery') as send:
            self.assertTrue(self.s.process_recovery_mail_once());self.assertFalse(self.s.process_recovery_mail_once())
            self.assertEqual(send.call_count,1);self.assertEqual(send.call_args.args[1],'https://chat.example.test/#reset='+reset)
    def test_failed_or_uncertain_delivery_is_not_automatically_retried(self):
        self.request()
        with patch('password_recovery.send_recovery',side_effect=TimeoutError('private SMTP detail')) as send:
            self.s.process_recovery_mail_once();self.assertFalse(self.s.process_recovery_mail_once());self.assertEqual(send.call_count,1)
        with self.s.db() as db:raw=json.dumps(dict(db.execute('SELECT * FROM password_resets').fetchone()))
        self.assertNotIn('private SMTP detail',raw)
    def test_worker_does_not_send_after_password_change_or_gate_disable(self):
        self.request();self.s.change_password(self.ctx,self.password,'changed-long-password')
        with patch('password_recovery.send_recovery') as send:self.s.process_recovery_mail_once();send.assert_not_called()
        with patch.dict(os.environ,{'TW_RECOVERY_ENABLED':'false'}),patch('password_recovery.send_recovery') as send:self.s.process_recovery_mail_once();send.assert_not_called()

    def test_completing_one_link_invalidates_other_outstanding_links(self):
        first=self.request()
        with patch('password_recovery.time.time',return_value=1800000061):
            second=self.request();self.s.complete_password_reset(second,'a-new-long-password')
            with self.assertRaises(Problem):self.s.complete_password_reset(first,'another-long-password')
    def test_competing_mail_workers_submit_one_message(self):
        self.request()
        with patch('password_recovery.send_recovery') as send:
            with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:self.s.process_recovery_mail_once(),range(2)))
            self.assertEqual(send.call_count,1)
