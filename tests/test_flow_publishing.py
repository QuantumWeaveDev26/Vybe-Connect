import tempfile
import unittest
from pathlib import Path
from store import Store,Problem


class FlowPublishingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'flows.db')
        self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'])
        self.values={'name':'Help','keyword':'help','reply':'Hello','enabled':True,'delivery_mode':'draft','graph':{'start':'hello','nodes':[{'id':'hello','type':'message','text':'Hello'}]}}
    def tearDown(self):self.tmp.cleanup()
    def create(self):return self.s.action(self.ctx,'flow.draft.save',self.values)
    def publish(self,draft):return self.s.action(self.ctx,'flow.publish',{'id':draft['id'],'draft_revision':draft['draft']['revision'],'base_version':draft['version']})
    def test_new_draft_never_activates_until_explicit_publish(self):
        flow=self.create();self.assertFalse(flow['enabled']);self.assertEqual(flow['version'],0)
        published=self.publish(flow);self.assertTrue(published['enabled']);self.assertEqual(published['version'],1)
    def test_draft_edits_leave_active_graph_and_version_unchanged(self):
        live=self.publish(self.create());draft=self.s.action(self.ctx,'flow.draft.save',dict(self.values,id=live['id'],base_version=1,draft_revision=0,keyword='new',reply='Changed'))
        state=self.s.state(self.ctx);flow=state['flows'][0]
        self.assertEqual(flow['keyword'],'help');self.assertEqual(flow['version'],1);self.assertEqual(flow['draft']['keyword'],'new')
        self.assertEqual(draft['draft']['reply'],'Changed')
    def test_old_editor_cannot_overwrite_a_newer_draft(self):
        flow=self.create();payload=dict(self.values,id=flow['id'],base_version=0,draft_revision=1)
        self.s.action(self.ctx,'flow.draft.save',payload)
        with self.assertRaises(Problem):self.s.action(self.ctx,'flow.draft.save',payload)
        with self.assertRaises(Problem):self.publish(flow)
    def test_legacy_publish_records_snapshot_and_stales_prior_draft(self):
        flow=self.create();self.s.action(self.ctx,'flow.save',dict(self.values,id=flow['id']))
        with self.assertRaises(Problem):self.publish(flow)
        with self.s.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM flow_versions').fetchone()[0],1)
    def test_history_is_immutable_and_restore_only_creates_a_draft(self):
        first=self.publish(self.create())
        second=self.s.action(self.ctx,'flow.save',dict(self.values,id=first['id'],keyword='second'))
        restored=self.s.action(self.ctx,'flow.draft.restore',{'id':first['id'],'version':1,'base_version':2,'draft_revision':0})
        self.assertEqual(restored['keyword'],'second');self.assertEqual(restored['draft']['keyword'],'help')
        third=self.publish(restored);self.assertEqual(third['version'],3);self.assertEqual(third['keyword'],'help')
        with self.s.db() as db:
            import json
            rows=db.execute('SELECT version,data FROM flow_versions ORDER BY version').fetchall()
            self.assertEqual([r['version'] for r in rows],[1,2,3]);self.assertEqual(json.loads(rows[1]['data'])['keyword'],'second')
    def test_agents_and_other_tenants_cannot_edit_or_publish(self):
        flow=self.create()
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,role='agent'),'flow.publish',{'id':flow['id']})
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,tenant_id=other['id']),'flow.draft.save',dict(self.values,id=flow['id'],base_version=0,draft_revision=1))
    def test_publication_revalidates_current_teammates(self):
        member=self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'long-enough-password','role':'agent'})
        graph={'start':'assign','nodes':[{'id':'assign','type':'assign','member_id':member['id']}]}
        flow=self.s.action(self.ctx,'flow.draft.save',dict(self.values,graph=graph))
        self.s.action(self.ctx,'member.remove',{'id':member['id']})
        with self.assertRaises(Problem):self.publish(flow)

    def test_draft_does_not_cancel_wait_but_publishing_does(self):
        graph={'start':'wait','nodes':[{'id':'wait','type':'wait','seconds':60,'next':'hello'},{'id':'hello','type':'message','text':'Hello'}]}
        flow=self.s.action(self.ctx,'flow.save',dict(self.values,graph=graph))
        self.s.inbound(self.ctx['tenant_id'],{'id':'inbound','from':'919000000001','text':{'body':'help'}})
        contact=self.s.state(self.ctx)['contacts'][0];self.assertIn('flow_session',contact)
        draft=self.s.action(self.ctx,'flow.draft.save',dict(self.values,id=flow['id'],base_version=1,draft_revision=0,graph=graph))
        self.assertIn('flow_session',self.s.state(self.ctx)['contacts'][0])
        self.publish(draft);self.assertNotIn('flow_session',self.s.state(self.ctx)['contacts'][0])
    def test_stale_admin_context_cannot_publish_after_demotion(self):
        flow=self.create()
        with self.s.db() as db:db.execute("UPDATE members SET role='agent' WHERE tenant=? AND user=?",(self.ctx['tenant_id'],self.ctx['user']['id']))
        with self.assertRaises(Problem):self.publish(flow)
