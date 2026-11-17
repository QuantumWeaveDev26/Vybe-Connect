import csv,io,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
import whatsapp_calls


class OperationsReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.s=Store(Path(self.tmp.name)/'operations.db');self.owner=self.s.auth(self.s.setup('Owner','owner@example.test','long-operations-password','Business')['token']);self.t=self.owner['tenant_id']
        self.member=self.s.action(self.owner,'member.add',{'name':'=FORMULA','email':'agent@example.test','password':'long-agent-password','role':'agent'})
        self.agent=self.s.auth(self.s.login('agent@example.test','long-agent-password')['token'])
        self.c=self.s.action(self.owner,'contact.save',{'name':'Customer','phone':'12025550146'})
    def permissions(self,**changes):
        p=self.s.state(self.owner)['members'];version=next(m['permissions']['version'] for m in p if m['id']==self.member['id'])
        return self.s.action(self.owner,'member.permissions',{'id':self.member['id'],'version':version,'permissions':dict(calling=True,reports=True,exports=True,**changes) if not changes else {k:changes.get(k,True) for k in ('calling','reports','exports')}})
    def call(self,**changes):
        value=dict(provider_id='call_test',direction='inbound',phone='12025550146',created=int(time.time()),status='ringing',owner='',offer='v=0\r\no=PRIVATE')
        value.update(changes)
        with self.s.db() as db:return self.s._put(db,self.t,'voicecall',value)
    def report(self,ctx=None,export=False):return self.s.message_analytics(ctx or self.owner,'2026-01-01','2026-12-31',export=export)
    def test_permission_revocation_blocks_existing_context_and_exports_before_network(self):
        self.permissions(calling=False,reports=False,exports=False)
        with patch('outbound_calls.remote') as remote:
            with self.assertRaises(Problem):self.s.action(self.agent,'calls.start',{'contact_id':self.c['id']})
            remote.assert_not_called()
        for fn in (lambda:self.report(self.agent),lambda:self.s.export_contacts(self.agent)):
            with self.assertRaises(Problem):fn()
        self.assertEqual(self.s.state(self.agent)['calling']['calls'],[])
    def test_exports_can_be_disabled_while_reports_remain_readable(self):
        self.permissions(exports=False)
        self.assertIn('operations',self.report(self.agent))
        with self.assertRaises(Problem):self.report(self.agent,True)
    def test_stale_admin_foreign_target_and_stale_policy_version_are_rejected(self):
        with self.assertRaises(Problem):self.s.action(dict(self.agent,role='admin'),'member.permissions',{'id':self.member['id'],'version':0,'permissions':dict(calling=False,reports=False,exports=False)})
        self.permissions(calling=False)
        with self.assertRaises(Problem):self.s.action(self.owner,'member.permissions',{'id':self.member['id'],'version':0,'permissions':dict(calling=True,reports=True,exports=True)})
        with self.assertRaises(Problem):self.s.action(self.owner,'member.permissions',{'id':'foreign','version':0,'permissions':dict(calling=True,reports=True,exports=True)})
    def test_ringing_assignment_and_note_work_without_provider_activation(self):
        call=self.call()
        with patch('whatsapp_calls.request') as remote,patch('outbound_calls.remote') as outbound:
            assigned=self.s.action(self.owner,'calls.assign',{'id':call['id'],'owner':self.member['id'],'expected_owner':''})
            self.assertEqual(assigned['owner'],self.member['id'])
            with self.assertRaises(Problem):self.s.action(self.owner,'calls.assign',{'id':call['id'],'owner':self.owner['user']['id'],'expected_owner':''})
            note=self.s.action(self.agent,'calls.note',{'id':call['id'],'body':'Internal follow-up'})
            self.assertEqual(note['notes'][0]['author'],self.member['id']);self.assertNotIn('offer',note)
            remote.assert_not_called();outbound.assert_not_called()
    def test_active_call_assignment_is_not_faked_as_media_transfer(self):
        call=self.call(status='connected',owner=self.member['id'])
        with self.assertRaises(Problem):self.s.action(self.owner,'calls.assign',{'id':call['id'],'owner':self.owner['user']['id'],'expected_owner':self.member['id']})
    def test_assignment_checks_target_permission_and_notes_check_ownership(self):
        call=self.call();self.permissions(calling=False)
        with self.assertRaises(Problem):self.s.action(self.owner,'calls.assign',{'id':call['id'],'owner':self.member['id'],'expected_owner':''})
        self.permissions()
        with self.assertRaises(Problem):self.s.action(self.agent,'calls.note',{'id':call['id'],'body':'Not my call'})
    def test_duplicate_termination_preserves_recorded_duration(self):
        call=self.call(status='connected',connected_at=100,created=90)
        with patch('whatsapp_calls.time.time',return_value=130):whatsapp_calls.ingest(self.s,self.t,[{'id':'call_test','event':'terminate'}])
        with patch('whatsapp_calls.time.time',return_value=999):whatsapp_calls.ingest(self.s,self.t,[{'id':'call_test','event':'terminate'}])
        with self.s.db() as db:self.assertEqual(self.s._get(db,self.t,'voicecall',call['id'])['ended'],130)
    def test_response_samples_exclude_drafts_notes_unknown_and_private_bodies(self):
        stamp=1790000000
        with self.s.db() as db:
            for direction,status,offset in [('in','received',0),('in','received',5),('note','internal',10),('out','draft',15),('out','unknown',20),('out','accepted',30),('in','received',40)]:self.s._message(db,self.t,self.c['id'],'PRIVATE BODY',direction,status,ts=stamp+offset)
        report=self.report();o=report['operations'];self.assertEqual(o['responses'],1);self.assertEqual(o['average_response_seconds'],30);self.assertEqual(o['awaiting_response'],1)
        self.assertNotIn('PRIVATE BODY',str(report))
    def test_call_report_missing_timestamps_and_csv_formula_safety(self):
        self.call(created=1790000000,owner=self.member['id'],status='ended',connected_at=1790000010,ended=1790000050)
        self.call(provider_id='old_call',created=1790000000,status='ended')
        o=self.report()['operations'];self.assertEqual(o['calls']['total'],2);self.assertEqual(o['calls']['connected_seconds'],40);self.assertEqual(o['calls']['duration_samples'],1)
        rows=list(csv.reader(io.StringIO(self.report(export=True)['csv'])))
        self.assertTrue(any(row[1]=="'=FORMULA" for row in rows if row[0]=='operator'))
    def test_resolution_durations_require_recorded_reopen_and_do_not_replay(self):
        for stamp,status in [(1790000000,'solved'),(1790000010,'open'),(1790000070,'solved'),(1790000080,'solved')]:
            with patch('store.now',return_value=stamp):self.s.action(self.owner,'chat.update',{'id':self.c['id'],'status':status})
        o=self.report()['operations'];self.assertEqual(o['resolved'],2);self.assertEqual(o['resolution_samples'],1);self.assertEqual(o['average_resolution_seconds'],60)

    def test_history_is_cursor_paged_private_and_keeps_old_active_calls_visible(self):
        active=self.call(status='connected',owner=self.member['id'])
        for i in range(105):self.call(provider_id='call_'+str(i),status='ended')
        first=self.s.action(self.owner,'calls.history',{'limit':100})
        second=self.s.action(self.owner,'calls.history',{'limit':100,'before':first['next_before']})
        self.assertEqual(len(first['calls']),100);self.assertEqual(len(second['calls']),6)
        self.assertFalse({c['id'] for c in first['calls']}&{c['id'] for c in second['calls']})
        self.assertNotIn('PRIVATE',str(first));self.assertIsNone(second['next_before'])
        self.assertIn(active['id'],{c['id'] for c in self.s.state(self.owner)['calling']['calls']})
        for invalid in (True,0,-1,2**80):
            with self.assertRaises(Problem):self.s.action(self.owner,'calls.history',{'before':invalid})

    def test_two_ringing_assignments_cannot_both_win_with_the_same_old_owner(self):
        from concurrent.futures import ThreadPoolExecutor
        call=self.call()
        def assign(target):
            try:self.s.action(self.owner,'calls.assign',{'id':call['id'],'owner':target,'expected_owner':''});return True
            except Problem:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(assign,[self.member['id'],self.owner['user']['id']]))
        self.assertEqual(sum(results),1)

    def test_owner_cannot_claim_a_second_call_while_already_connected(self):
        self.call(status='connected',owner=self.member['id'])
        ringing=self.call(provider_id='second_call')
        with patch('whatsapp_calls.status',return_value={'ready':True}),patch('whatsapp_calls.request') as provider:
            with self.assertRaisesRegex(Exception,'current call'):self.s.action(self.agent,'calls.claim',{'id':ringing['id']})
            provider.assert_not_called()

    def test_personalized_macro_uses_crm_fields_and_never_sends(self):
        contact=self.s.action(self.owner,'contact.save',dict(self.c,attributes={'plan':'Starter'}))
        macro=self.s.action(self.owner,'growth.macro.save',{'name':'Personalized','reply':'Hi {{ name }}, your {plan} inquiry is ready. {{missing}}','note':'','tag':''})
        with patch('urllib.request.urlopen',side_effect=AssertionError('No provider request')):
            self.s.action(self.owner,'growth.macro.apply',{'id':macro['id'],'contact_id':contact['id']})
        state=self.s.state(self.owner);message=state['messages'][-1]
        self.assertEqual(message['status'],'draft');self.assertEqual(message['body'],'Hi Customer, your Starter inquiry is ready. {{missing}}');self.assertFalse(state['queue'])

    def test_removed_operator_activity_remains_in_historical_report(self):
        self.call(created=1790000000,status='ended',owner=self.member['id'])
        self.s.action(self.owner,'member.remove',{'id':self.member['id']})
        operators=self.report()['operations']['operators'];former=next(m for m in operators if m['id']==self.member['id'])
        self.assertEqual(former['calls'],1);self.assertIn('former member',former['name'])
