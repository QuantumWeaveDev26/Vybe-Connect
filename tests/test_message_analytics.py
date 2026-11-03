import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from store import Store,Problem


class MessageAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'reports.db');token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
        self.contact=self.s.action(self.ctx,'contact.save',{'name':'Buyer','phone':'919000000001'});self.stamp=int(datetime(2026,10,1,tzinfo=timezone.utc).timestamp())
    def tearDown(self):self.tmp.cleanup()
    def message(self,direction,status,offset=0,tenant=None):
        with self.s.db() as db:self.s._message(db,tenant or self.ctx['tenant_id'],self.contact['id'],'PRIVATE BODY',direction,status,ts=self.stamp+offset)
    def report(self,start='2026-10-01',end='2026-10-03'):return self.s.message_analytics(self.ctx,start,end)
    def test_real_statuses_and_empty_days_are_counted_without_private_text(self):
        self.message('in','received');self.message('out','accepted');self.message('out','read',86400);self.message('out','unknown');self.message('out','failed')
        for direction,status in [('out','draft'),('in','simulated'),('out','simulated'),('note','internal')]:self.message(direction,status)
        report=self.report();self.assertEqual(report['totals']['inbound'],1);self.assertEqual(report['totals']['accepted'],1);self.assertEqual(report['totals']['read'],1);self.assertEqual(report['totals']['unknown'],1);self.assertEqual(report['contacts'],1)
        self.assertEqual(len(report['days']),3);self.assertEqual(report['days'][2]['inbound'],0);self.assertNotIn('PRIVATE BODY',str(report));self.assertNotIn(self.contact['id'],str(report))
    def test_range_boundaries_are_inclusive_utc_dates(self):
        self.message('in','received',-1);self.message('in','received',0);self.message('in','received',3*86400-1);self.message('in','received',3*86400)
        self.assertEqual(self.report()['totals']['inbound'],2)
    def test_report_reads_more_than_inbox_recent_message_limit(self):
        with self.s.db() as db:
            for _ in range(2100):self.s._message(db,self.ctx['tenant_id'],self.contact['id'],'Recorded','in','received',ts=self.stamp)
        self.assertEqual(self.report()['totals']['inbound'],2100)
    def test_other_workspace_events_are_excluded(self):
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'});self.message('in','received',tenant=other['id']);self.message('out','delivered')
        report=self.report();self.assertEqual(report['totals']['inbound'],0);self.assertEqual(report['totals']['delivered'],1)
    def test_invalid_dates_reversed_and_overlong_ranges_are_rejected(self):
        for start,end in [('bad','2026-10-03'),('2026-10-04','2026-10-03'),('2024-01-01','2026-01-01'),('2026-10-01T00:00Z','2026-10-03')]:
            with self.assertRaises(Problem):self.report(start,end)
    def test_delivery_states_are_not_invented_from_acceptance(self):
        self.message('out','accepted');self.message('out','unknown');report=self.report()
        self.assertEqual(report['totals']['delivered'],0);self.assertEqual(report['totals']['read'],0)
    def test_revoked_membership_is_checked_even_with_old_context(self):
        with self.s.db() as db:db.execute('DELETE FROM members WHERE tenant=? AND user=?',(self.ctx['tenant_id'],self.ctx['user']['id']))
        with self.assertRaises(Problem):self.report()
    def test_leap_year_366_day_range_is_allowed(self):
        self.assertEqual(len(self.report('2024-01-01','2024-12-31')['days']),366)
