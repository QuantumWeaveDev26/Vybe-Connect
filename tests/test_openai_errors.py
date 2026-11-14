import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

import ai
import openai_errors as errors
from openai_adapter import request_openai
from openai_background import openai_create, openai_retrieve


class OpenAIErrorTests(unittest.TestCase):
    def setUp(self):
        with errors._lock:errors._blocked.clear()
        self.addCleanup(self.clear)

    def clear(self):
        with errors._lock:errors._blocked.clear()

    def failure(self, code='insufficient_quota', kind='insufficient_quota', retry='0'):
        body=json.dumps({'error':{'code':code,'type':kind,'message':'PRIVATE KEY AND CUSTOMER TEXT'}}).encode()
        return urllib.error.HTTPError('https://api.openai.com/v1/responses',429,'Rejected',{'Retry-After':retry},io.BytesIO(body))

    def test_quota_is_actionable_private_and_not_retried(self):
        with patch('openai_adapter.urllib.request.urlopen',side_effect=self.failure()) as network:
            for _ in range(2):
                with self.assertRaises(errors.OpenAIRequestError) as caught:
                    request_openai('quota-test-key','gpt-6-luna','System','Test',[])
                self.assertEqual(caught.exception.reason,'quota_exhausted')
                self.assertNotIn('PRIVATE',str(caught.exception))
                self.assertIn('billing',str(caught.exception))
        self.assertEqual(network.call_count,1)

    def test_rate_limit_obeys_bounded_retry_after_without_sending_retry(self):
        failure=errors.http_failure(self.failure('rate_limit_exceeded','rate_limit_error','120'),'rate-key')
        self.assertEqual(failure.reason,'rate_limited')
        self.assertEqual(failure.retry_after,120)
        with self.assertRaises(errors.OpenAIRequestError):errors.ensure_available('rate-key')
        errors.ensure_available('different-customer-key')

    def test_background_creation_is_blocked_but_existing_response_can_be_reconciled(self):
        errors.http_failure(self.failure(),'background-key')
        with patch('openai_background.urllib.request.urlopen',return_value=io.BytesIO(b'{"status":"failed"}')) as network:
            with self.assertRaises(errors.OpenAIRequestError):openai_create('background-key','gpt-6-luna','System','Test',[])
            self.assertEqual(openai_retrieve('background-key','resp_test')['status'],'failed')
        self.assertEqual(network.call_count,1)

    def test_blocked_request_does_not_consume_another_included_ai_request(self):
        key='blocked-allowance-key'
        errors.http_failure(self.failure(),key)
        with patch.dict(os.environ,{'TW_AI_PROVIDER':'openai','TW_AI_ENABLED':'true','TW_AI_MODEL':'gpt-6-luna','TW_PLATFORM_AI_MANAGED':'false','TW_AI_TEST_ALLOW_PAID':'true','TW_AI_TEST_OPENAI_API_KEY':key}):
            with patch('platform_ai.reserve') as reserve,patch('ai.request_openai') as network:
                with self.assertRaises(errors.OpenAIRequestError):ai.ask_local('Test',{'_workspace_id':'test'},[])
        reserve.assert_not_called();network.assert_not_called()

    def test_malformed_error_body_uses_safe_unknown_reason(self):
        error=urllib.error.HTTPError('https://api.openai.com/v1/responses',429,'PRIVATE',{},io.BytesIO(b'not JSON PRIVATE'))
        failure=errors.http_failure(error,'unknown-key')
        self.assertEqual(failure.reason,'quota_or_rate_limit')
        self.assertNotIn('PRIVATE',str(failure))

    def test_cooldown_expires_and_does_not_require_changing_the_key(self):
        with patch('openai_errors.time.monotonic',return_value=100):
            errors.http_failure(self.failure('rate_limit_exceeded','rate_limit_error'),'expiry-key')
        with patch('openai_errors.time.monotonic',return_value=161):
            errors.ensure_available('expiry-key')
        self.assertNotIn(errors.identity('expiry-key'),errors._blocked)

    def test_huge_retry_header_is_bounded_and_access_errors_are_safe(self):
        self.assertEqual(errors.http_failure(self.failure(retry='99999999'),'bounded-key').retry_after,3600)
        error=urllib.error.HTTPError('https://api.openai.com/v1/responses',401,'PRIVATE',{},io.BytesIO(b'PRIVATE'))
        failure=errors.http_failure(error,'invalid-key')
        self.assertEqual(failure.reason,'access_denied')
        self.assertNotIn('PRIVATE',str(failure))
