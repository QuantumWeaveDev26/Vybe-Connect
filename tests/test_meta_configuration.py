import os
import unittest
from unittest.mock import patch
from meta import status


class MetaConfigurationTests(unittest.TestCase):
    def values(self):
        return {'TW_META_CHECK_'+k:v for k,v in {
            'TOKEN':'private-test-token','PHONE_ID':'12345','WABA_ID':'67890',
            'APP_SECRET':'a'*32,'VERIFY_TOKEN':'private-verify-token','VERSION':'v25.0','LIVE':'false'
        }.items()}

    def test_invalid_formats_are_not_reported_as_configured_or_leaked(self):
        values=self.values()
        values.update(TW_META_CHECK_VERSION='https://graph.facebook.com/v25.0',TW_META_CHECK_APP_SECRET='wrong-secret')
        with patch.dict(os.environ,values):result=status('check')
        self.assertFalse(result['configured'])
        self.assertEqual(set(result['invalid']),{'VERSION','APP_SECRET'})
        self.assertNotIn('wrong-secret',str(result))
        self.assertNotIn('private-test-token',str(result))

    def test_valid_formats_are_configured_with_sending_disabled(self):
        with patch.dict(os.environ,self.values()):result=status('check')
        self.assertTrue(result['configured'])
        self.assertFalse(result['live'])
        self.assertEqual(result['invalid'],{})

    def test_missing_fields_are_distinct_from_invalid_fields(self):
        values=self.values();values['TW_META_CHECK_TOKEN']='';values['TW_META_CHECK_PHONE_ID']='not-a-number'
        with patch.dict(os.environ,values):result=status('check')
        self.assertFalse(result['present']['TOKEN'])
        self.assertNotIn('TOKEN',result['invalid'])
        self.assertIn('PHONE_ID',result['invalid'])
