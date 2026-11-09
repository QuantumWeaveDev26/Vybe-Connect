import io,json,tempfile,unittest,urllib.request
from pathlib import Path
from unittest.mock import Mock
from tools.acceptance_live_ai import Budget

class AcceptanceBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'report.json'
    def request(self,model='gpt-6-luna',url='https://api.openai.com/v1/responses'):
        return urllib.request.Request(url,data=json.dumps({'model':model,'input':'Synthetic QA','max_output_tokens':99999}).encode(),method='POST')
    def test_budget_and_provider_rejections_happen_before_network(self):
        b=Budget(self.path,0.001);b.native=Mock()
        for req in [self.request(),self.request('other-model'),self.request(url='https://graph.facebook.com/v1/responses')]:
            with self.assertRaises(ValueError):b.open(req)
        b.native.assert_not_called();self.assertEqual(b.data['calls'],[])
    def test_uncertain_submission_retains_budget_and_is_not_retried(self):
        b=Budget(self.path,0.01);b.native=Mock(side_effect=TimeoutError('uncertain'))
        with self.assertRaises(TimeoutError):b.open(self.request())
        self.assertGreater(b.data['reserved_usd'],0)
        with self.assertRaises(ValueError):b.open(self.request())
        self.assertEqual(b.native.call_count,1)
        with self.assertRaises(ValueError):Budget(self.path,0.4)
    def test_output_limit_and_usage_release(self):
        b=Budget(self.path,0.4);req=self.request()
        b.native=Mock(return_value=io.BytesIO(json.dumps({'id':'resp_qa','status':'completed','usage':{'input_tokens':100,'output_tokens':10}}).encode()))
        b.open(req)
        self.assertEqual(json.loads(req.data)['max_output_tokens'],1024)
        self.assertEqual(b.data['reserved_usd'],0);self.assertAlmostEqual(b.data['spent_upper_usd'],0.00015)
    def test_quota_failure_stops_all_later_provider_requests(self):
        import urllib.error
        b=Budget(self.path,0.4)
        b.native=Mock(side_effect=urllib.error.HTTPError('https://api.openai.com/v1/responses',429,'Quota',{},None))
        with self.assertRaises(urllib.error.HTTPError):b.open(self.request())
        with self.assertRaises(ValueError):b.open(self.request())
        self.assertEqual(b.native.call_count,1)
        self.assertEqual(b.data['provider_error_status'],429)
