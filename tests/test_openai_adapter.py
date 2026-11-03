import io
import json
import os
import unittest
from unittest.mock import patch
from ai import ai_status, ask_local


class OpenAIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_AI_ENABLED':'true','TW_OPENAI_API_KEY':'unit-test-placeholder','TW_AI_BUSINESS1_ALLOW_PAID':'false'});self.env.start()
        self.context={'_workspace_id':'business1','business':'Acme','knowledge_sources':[]}

    def tearDown(self):self.env.stop()

    def test_paid_calls_require_workspace_opt_in_and_never_expose_key(self):
        with patch('ai.urllib.request.urlopen') as transport:
            with self.assertRaisesRegex(ValueError,'paid'):ask_local('Question',self.context,[])
            transport.assert_not_called()
        self.assertNotIn('unit-test-placeholder',json.dumps(ai_status('business1')))
        self.assertFalse(ai_status('business1')['enabled'])

    def test_responses_payload_and_message_output_use_official_endpoint(self):
        body={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Grounded answer'}]}]}
        with patch.dict(os.environ,{'TW_AI_BUSINESS1_ALLOW_PAID':'true'}),patch('ai.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(body).encode())) as transport:
            self.assertEqual(ask_local('Question',self.context,[]),'Grounded answer')
        request=transport.call_args.args[0];payload=json.loads(request.data)
        self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
        self.assertEqual(payload['model'],'gpt-6-luna');self.assertFalse(payload['store'])
        self.assertNotIn('tools',payload);self.assertNotIn('_workspace_id',payload['instructions'])

    def test_schema_refusal_and_incomplete_output_fail_without_fake_findings(self):
        context=dict(self.context,analysis_contract={'rules':'Return structured findings.'})
        for response in [{'status':'incomplete','output':[]},{'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'No'}]}]}]:
            with patch.dict(os.environ,{'TW_AI_BUSINESS1_ALLOW_PAID':'true'}),patch('ai.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as transport:
                with self.assertRaises(ValueError):ask_local('Analyze',context,[])
            payload=json.loads(transport.call_args.args[0].data)
            self.assertEqual(payload['text']['format']['type'],'json_schema')
            self.assertTrue(payload['text']['format']['strict'])

    def test_provider_failures_do_not_echo_credentials(self):
        with patch.dict(os.environ,{'TW_AI_BUSINESS1_ALLOW_PAID':'true'}),patch('ai.urllib.request.urlopen',side_effect=RuntimeError('unit-test-placeholder')):
            with self.assertRaises(ValueError) as error:ask_local('Question',self.context,[])
        self.assertNotIn('unit-test-placeholder',str(error.exception))

    def test_malformed_message_content_is_an_explicit_provider_error(self):
        result={'status':'completed','output':[{'type':'message','content':'invalid content shape'}]}
        with patch.dict(os.environ,{'TW_AI_BUSINESS1_ALLOW_PAID':'true'}),patch('ai.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(result).encode())):
            with self.assertRaisesRegex(ValueError,'invalid'):ask_local('Question',self.context,[])

    def test_workspace_gate_and_key_do_not_cross_tenants(self):
        with patch.dict(os.environ,{'TW_AI_BUSINESS1_ALLOW_PAID':'true','TW_AI_BUSINESS1_OPENAI_API_KEY':'tenant-specific-test-key'}):
            self.assertTrue(ai_status('business1')['enabled'])
            self.assertFalse(ai_status('business2')['enabled'])
            response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Answer'}]}]}
            with patch('ai.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as transport:ask_local('Question',self.context,[])
            self.assertEqual(transport.call_args.args[0].get_header('Authorization'),'Bearer tenant-specific-test-key')
