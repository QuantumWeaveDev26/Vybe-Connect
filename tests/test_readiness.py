import json
import os
import unittest
from unittest.mock import patch
from readiness import snapshot


class ReadinessTests(unittest.TestCase):
    def test_missing_credentials_remain_blocked_without_network_or_secret_output(self):
        with patch.dict(os.environ,{},clear=True),patch('socket.socket',side_effect=AssertionError('No network')):
            result=snapshot()
        self.assertTrue(all(v=='setup_needed' for v in result['configuration'].values()))
        self.assertFalse(result['ready_for_paying_customers'])

    def test_configured_services_do_not_claim_provider_acceptance(self):
        env={'TW_PLATFORM_AI_MANAGED':'true','TW_AI_ENABLED':'true','TW_OPENAI_API_KEY':'PRIVATE-KEY','TW_AI_MODEL':'gpt-6-luna'}
        with patch.dict(os.environ,env,clear=True),patch('business_providers.status',return_value={'ready':True}),patch('business_providers.plans',return_value={'starter':{}}),patch('embedded_signup.configuration',return_value={'ready':True,'APP_SECRET':'PRIVATE'}),patch('google_connections.configuration',return_value={'ready':True,'secret':'PRIVATE'}),patch('recovery_mail.configuration',return_value={'ready':True,'password':'PRIVATE'}):
            result=snapshot()
        self.assertTrue(all(v=='configured' for v in result['configuration'].values()))
        self.assertFalse(result['ready_for_paying_customers'])
        self.assertEqual(result['live_acceptance'],'not_established')
        self.assertNotIn('PRIVATE',json.dumps(result))

    def test_invalid_configuration_is_a_setup_blocker_without_raw_error(self):
        with patch.dict(os.environ,{},clear=True),patch('google_connections.configuration',side_effect=ValueError('PRIVATE')):
            result=snapshot()
        self.assertEqual(result['configuration']['google_connections'],'setup_needed')
        self.assertNotIn('PRIVATE',json.dumps(result))
