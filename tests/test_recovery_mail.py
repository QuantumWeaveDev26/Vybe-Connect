import os
import ssl
import unittest
from unittest.mock import patch,MagicMock,call,ANY
from recovery_mail import configuration,send_recovery

ENV={'TW_RECOVERY_ENABLED':'true','TW_RECOVERY_SECRET':'synthetic-secret-'+('x'*40),'TW_PUBLIC_ORIGIN':'https://chat.example.test','TW_SMTP_HOST':'smtp.example.test','TW_SMTP_FROM':'support@example.test','TW_SMTP_SECURITY':'ssl','TW_SMTP_USERNAME':'mailer','TW_SMTP_PASSWORD':'synthetic-password'}


class RecoveryMailTests(unittest.TestCase):
    def setUp(self):self.env=patch.dict(os.environ,ENV,clear=True);self.env.start()
    def tearDown(self):self.env.stop()
    def test_ssl_transport_checks_certificate_and_logs_in(self):
        with patch('recovery_mail.smtplib.SMTP_SSL') as connection:
            smtp=connection.return_value.__enter__.return_value;smtp.send_message.return_value={}
            send_recovery('owner@example.test','https://chat.example.test/#reset=test-link')
            context=connection.call_args.kwargs['context'];self.assertTrue(context.check_hostname);self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
            smtp.starttls.assert_not_called();smtp.login.assert_called_once_with('mailer','synthetic-password')
            message=smtp.send_message.call_args.args[0];self.assertEqual(message['To'],'owner@example.test');self.assertIn('/#reset=test-link',message.get_content())
    def test_starttls_happens_before_credentials_or_message(self):
        with patch.dict(os.environ,{'TW_SMTP_SECURITY':'starttls'}),patch('recovery_mail.smtplib.SMTP') as connection:
            smtp=connection.return_value.__enter__.return_value;smtp.send_message.return_value={}
            send_recovery('owner@example.test','https://chat.example.test/#reset=test-link')
            self.assertEqual(smtp.method_calls[:4],[call.ehlo(),call.starttls(context=ANY),call.ehlo(),call.login('mailer','synthetic-password')])
            self.assertEqual(connection.call_args.args[1],587)
    def test_disabled_or_insecure_configuration_never_connects(self):
        for values in [{'TW_RECOVERY_ENABLED':'false'},{'TW_SMTP_SECURITY':'plain'},{'TW_PUBLIC_ORIGIN':'http://chat.example.test'},{'TW_PUBLIC_ORIGIN':'https://chat.example.test/path'},{'TW_RECOVERY_SECRET':'short'},{'TW_SMTP_FROM':'bad\r\nBcc: other@example.test'}]:
            with patch.dict(os.environ,values),patch('recovery_mail.smtplib.SMTP_SSL') as connection,patch('recovery_mail.smtplib.SMTP') as insecure:
                self.assertFalse(configuration()['ready'])
                with self.assertRaises(ValueError):send_recovery('owner@example.test','https://chat.example.test/#reset=test-link')
                connection.assert_not_called();insecure.assert_not_called()
    def test_wrong_link_origin_is_rejected(self):
        with patch('recovery_mail.smtplib.SMTP_SSL') as connection:
            with self.assertRaises(ValueError):send_recovery('owner@example.test','https://attacker.test/#reset=test-link')
            connection.assert_not_called()
    def test_refused_recipient_is_not_reported_as_success(self):
        with patch('recovery_mail.smtplib.SMTP_SSL') as connection:
            connection.return_value.__enter__.return_value.send_message.return_value={'owner@example.test':(550,b'refused')}
            with self.assertRaises(OSError):send_recovery('owner@example.test','https://chat.example.test/#reset=test-link')
