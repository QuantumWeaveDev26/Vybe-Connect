import io,json,unittest,urllib.error
from unittest.mock import patch
import provider_transport

class ProviderDiagnosticTests(unittest.TestCase):
 def test_meta_diagnostics_keep_only_numeric_code(self):
  error=urllib.error.HTTPError('https://graph.facebook.com',400,'private body',{},io.BytesIO(json.dumps({'error':{'code':190,'message':'secret-token-and-business-data'}}).encode()))
  with patch('provider_transport.urllib.request.build_opener') as opener:
   opener.return_value.open.side_effect=error
   with self.assertRaises(provider_transport.RemoteError) as result:provider_transport.request('https://graph.facebook.com/v25.0/123')
  self.assertEqual(result.exception.provider_code,190);self.assertEqual(result.exception.http_status,400)
  self.assertNotIn('secret',str(result.exception));self.assertNotIn('secret',str(vars(result.exception)))
 def test_provider_error_body_is_not_exposed(self):
  error=urllib.error.HTTPError('https://graph.facebook.com',403,'private',{},io.BytesIO(b'{"error":{"code":"private-secret","message":"sensitive"}}'))
  with patch('provider_transport.urllib.request.build_opener') as opener:
   opener.return_value.open.side_effect=error
   with self.assertRaises(provider_transport.RemoteError) as result:provider_transport.request('https://graph.facebook.com/v25.0/123')
  self.assertIsNone(result.exception.provider_code);self.assertNotIn('private',str(vars(result.exception)))
