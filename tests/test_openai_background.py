import io
import json
import unittest
from unittest.mock import patch
from openai_background import openai_create,openai_retrieve,openai_cancel


class BackgroundTransportTests(unittest.TestCase):
    def test_create_uses_background_store_false_and_strict_chat_references(self):
        response={'id':'resp_test','status':'queued'}
        with patch('openai_background.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as call:
            self.assertEqual(openai_create('test-only','gpt-6-luna','System','Question',[])['id'],'resp_test')
        request=call.call_args.args[0];payload=json.loads(request.data)
        self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
        self.assertTrue(payload['background']);self.assertFalse(payload['store']);self.assertNotIn('tools',payload)
        self.assertTrue(payload['text']['format']['strict'])

    def test_retrieve_and_cancel_use_validated_fixed_response_path(self):
        for fn,method,path in [(openai_retrieve,'GET','/resp_test'),(openai_cancel,'POST','/resp_test/cancel')]:
            with patch('openai_background.urllib.request.urlopen',return_value=io.BytesIO(b'{"status":"cancelled"}')) as call:fn('test-only','resp_test')
            request=call.call_args.args[0];self.assertEqual(request.method,method);self.assertEqual(request.full_url,'https://api.openai.com/v1/responses'+path)
        with patch('openai_background.urllib.request.urlopen') as call:
            with self.assertRaises(ValueError):openai_cancel('test-only','../../other-host')
            call.assert_not_called()

    def test_errors_do_not_echo_key_or_automatically_retry_create(self):
        with patch('openai_background.urllib.request.urlopen',side_effect=RuntimeError('test-secret')) as call:
            with self.assertRaises(ValueError) as error:openai_create('test-secret','gpt-6-luna','System','Question',[])
            self.assertEqual(call.call_count,1);self.assertNotIn('test-secret',str(error.exception))
