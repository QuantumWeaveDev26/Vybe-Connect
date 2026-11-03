import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from auth_limits import consume


class AuthLimitTests(unittest.TestCase):
    def setUp(self):self.buckets={};self.lock=threading.Lock()
    def use(self,identity='owner@example.test',stamp=100):return consume(self.buckets,self.lock,'proxy',identity,stamp)
    def test_per_account_limit_does_not_block_another_account(self):
        self.assertTrue(all(self.use() for _ in range(12)));self.assertFalse(self.use());self.assertTrue(self.use('other@example.test'));self.assertFalse(self.use('OWNER@EXAMPLE.TEST'))
    def test_address_budget_is_bounded_across_many_identities(self):
        self.assertTrue(all(self.use(str(i)) for i in range(120)));self.assertFalse(self.use('extra'))
    def test_expired_buckets_are_reclaimed(self):
        for _ in range(12):self.use()
        self.assertTrue(self.use(stamp=161));self.assertEqual(len(self.buckets),2)
    def test_competing_requests_cannot_exceed_account_limit(self):
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:self.use(),range(24)))
        self.assertEqual(sum(results),12)
