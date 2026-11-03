import io
import json
import os
import unittest
from unittest.mock import patch
from meta import submit_template,send_template,list_templates,ProviderError


class MetaContractTests(unittest.TestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{'TW_META_TEST_TOKEN':'not-a-real-token','TW_META_TEST_PHONE_ID':'123','TW_META_TEST_WABA_ID':'456','TW_META_TEST_VERSION':'v99.0','TW_META_TEST_LIVE':'true'})
        self.environment.start()
    def tearDown(self):self.environment.stop()

    def test_template_submission_builds_official_request_and_numbered_example(self):
        seen=[]
        def provider(request,timeout):
            seen.append(request)
            return io.BytesIO(b'{"id":"meta-template","status":"PENDING"}')
        with patch('urllib.request.urlopen',provider):result=submit_template('test',{'name':'welcome','body':'Hi {{name}}','language':'en','category':'UTILITY'})
        self.assertEqual(result['status'],'PENDING')
        self.assertEqual(seen[0].full_url,'https://graph.facebook.com/v99.0/456/message_templates')
        body=json.loads(seen[0].data);self.assertEqual(body['components'][0]['text'],'Hi {{1}}')
        self.assertEqual(body['components'][0]['example']['body_text'],[['Customer']])

    def test_template_send_uses_recipient_language_and_parameter(self):
        seen=[]
        def provider(request,timeout):seen.append(request);return io.BytesIO(b'{"messages":[{"id":"wamid.real-shape"}]}')
        with patch('urllib.request.urlopen',provider):id=send_template('test','919000000001',{'name':'welcome','language':'en','body':'Hi {{1}}','components':[{'type':'BODY','text':'Hi {{1}}'}]},'Asha')
        self.assertEqual(id,'wamid.real-shape');body=json.loads(seen[0].data)
        self.assertEqual(body['to'],'919000000001');self.assertEqual(body['template']['components'][0]['parameters'][0]['text'],'Asha')
        self.assertEqual(seen[0].full_url,'https://graph.facebook.com/v99.0/123/messages')

    def test_disabled_gate_prevents_any_provider_request(self):
        with patch.dict(os.environ,{'TW_META_TEST_LIVE':'false'}),patch('urllib.request.urlopen',side_effect=AssertionError('Network must not run')):
            with self.assertRaises(ProviderError):send_template('test','919000000001',{'name':'hello','language':'en','body':'Hello'},'Asha')

    def test_rich_text_template_includes_header_footer_and_buttons(self):
        seen=[]
        def provider(request,timeout):seen.append(json.loads(request.data));return io.BytesIO(b'{"id":"template-1","status":"PENDING"}')
        with patch('urllib.request.urlopen',provider):submit_template('test',{'name':'welcome','body':'Hello {{name}}','language':'en','category':'MARKETING','header':'Welcome','footer':'Reply STOP to opt out','buttons':[{'type':'QUICK_REPLY','text':'Tell me more'},{'type':'URL','text':'Visit website','url':'https://example.test'}]})
        components=seen[0]['components']
        self.assertEqual(components[0],{'type':'HEADER','format':'TEXT','text':'Welcome'})
        self.assertEqual(components[2],{'type':'FOOTER','text':'Reply STOP to opt out'})
        self.assertEqual(components[3]['buttons'][1]['url'],'https://example.test')
