import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class FlowRichDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'data/flow.db');self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token']);self.t=self.ctx['tenant_id'];self.stamp=int(time.time())
        self.ready=patch('flow_delivery.ready',return_value=True);self.ready.start()
        self.s.action(self.ctx,'contact.save',{'name':'Customer','phone':'919000000001'})
        with patch('media_service.upload_media',return_value='123456'):self.asset=self.s.upload_media_asset(self.ctx,'guide.pdf','application/pdf',b'unit-test-document')
        self.template=self.s.action(self.ctx,'template.save',{'name':'reminder','language':'en','category':'UTILITY','body':'Hello {{name}}'})
        with self.s.db() as db:self.template=self.s._put(db,self.t,'template',dict(self.template,status='APPROVED',meta_id='approved_1'),self.template['id'])
    def tearDown(self):self.ready.stop();self.tmp.cleanup()
    def save(self,nodes,mode='live'):return self.s.action(self.ctx,'flow.save',{'name':'Rich bot','keyword':'help','reply':'Hello','enabled':True,'delivery_mode':mode,'graph':{'start':nodes[0]['id'],'nodes':nodes}})
    def incoming(self,simulated=False):self.s.inbound(self.t,{'id':'real','from':'919000000001','text':{'body':'help'}},simulated)
    def state(self):return self.s.state(self.ctx)
    def media(self,**changes):return dict({'id':'media','type':'media','asset_id':self.asset['id'],'caption':'Guide for {{name}}'},**changes)
    def tpl(self,**changes):return dict({'id':'template','type':'template','template_id':self.template['id']},**changes)
    def step(self):
        with patch('flow_delivery.send_text',return_value='wamid.text') as text,patch('flow_delivery.send_media',return_value='wamid.media') as media,patch('flow_delivery.send_template',return_value='wamid.template') as template:self.s.process_flow_send_once();return text,media,template
    def test_media_node_dispatches_existing_adapter_and_continues_after_acceptance(self):
        self.save([self.media(next='done'),{'id':'done','type':'attribute','field':'sent','value':'yes'}]);self.incoming();text,media,template=self.step();text.assert_not_called();template.assert_not_called();self.assertEqual(media.call_args.args[2:6],('123456','document','Guide for Customer','guide.pdf'));self.assertEqual(self.state()['contacts'][0]['attributes']['sent'],'yes')
    def test_template_sends_outside_window_only_with_current_consent(self):
        self.save([{'id':'wait','type':'wait','seconds':90000,'next':'template'},self.tpl()]);self.incoming();c=self.state()['contacts'][0];self.s.action(self.ctx,'contact.save',dict(c,optin=True))
        due=c['flow_session']['due']
        with patch('store.now',return_value=due),patch('flow_delivery.now',return_value=due):self.s.process_flow_wait_once();text,media,template=self.step()
        text.assert_not_called();media.assert_not_called();template.assert_called_once();self.assertEqual(self.state()['flow_sends'][0]['status'],'accepted')
    def test_consent_revocation_after_queue_prevents_template(self):
        self.save([self.tpl()]);self.incoming();text,media,template=self.step();template.assert_not_called();self.assertEqual(self.state()['flow_sends'][0]['status'],'cancelled')
    def test_foreign_and_missing_resources_are_rejected(self):
        for node in [self.media(asset_id='foreign'),self.tpl(template_id='foreign')]:
            with self.assertRaises(Problem):self.save([node])
    def test_resource_change_after_enqueue_cancels_without_substitution(self):
        self.save([self.media()]);self.incoming()
        with self.s.db() as db:self.s._put(db,self.t,'media',dict(self.asset,provider_id='999999'),self.asset['id'])
        _,media,_=self.step();media.assert_not_called();self.assertEqual(self.state()['flow_sends'][0]['status'],'cancelled')
    def test_phone_change_after_enqueue_cancels_pending_text(self):
        self.save([{'id':'text','type':'message','text':'Hello'}]);self.incoming();c=self.state()['contacts'][0];self.s.action(self.ctx,'contact.save',dict(c,phone='919000000002'));text,_,_=self.step();text.assert_not_called()
    def test_simulated_media_creates_only_a_draft(self):
        self.save([self.media()]);self.incoming(True);self.assertEqual(self.state()['flow_sends'],[]);self.assertIn('[document]',self.state()['messages'][-1]['body']);self.assertEqual(self.state()['messages'][-1]['status'],'draft')
    def test_template_approval_change_prevents_submission(self):
        self.save([self.tpl()]);self.incoming();c=self.state()['contacts'][0];self.s.action(self.ctx,'contact.save',dict(c,optin=True))
        with self.s.db() as db:self.s._put(db,self.t,'template',dict(self.template,status='REJECTED'),self.template['id'])
        _,_,template=self.step();template.assert_not_called()
    def test_unapproved_template_is_available_in_draft_mode_only(self):
        with self.s.db() as db:self.s._put(db,self.t,'template',dict(self.template,status='local_draft',meta_id=''),self.template['id'])
        with self.assertRaises(Problem):self.save([self.tpl()])
        self.save([self.tpl()],mode='draft');self.incoming();self.assertEqual(self.state()['messages'][-1]['status'],'draft')
    def test_audio_caption_and_oversized_caption_are_rejected(self):
        with patch('media_service.upload_media',return_value='222222'):audio=self.s.upload_media_asset(self.ctx,'voice.mp3','audio/mpeg',b'unit-audio')
        for node in [self.media(asset_id=audio['id'],caption='Not allowed'),self.media(caption='x'*1025)]:
            with self.assertRaises(Problem):self.save([node])
    def test_expanded_caption_failure_never_queues_or_calls_provider(self):
        c=self.state()['contacts'][0];self.s.action(self.ctx,'contact.save',dict(c,attributes={'long':'x'*700}));self.save([self.media(caption='{{long}}{{long}}')]);self.incoming();self.assertEqual(self.state()['flow_sends'],[]);self.assertTrue(self.state()['contacts'][0]['automation_hold'])
    def test_template_snapshot_and_name_parameter_are_frozen(self):
        c=self.state()['contacts'][0];self.s.action(self.ctx,'contact.save',dict(c,optin=True));self.save([self.tpl()]);self.incoming();c=self.state()['contacts'][0];self.s.action(self.ctx,'contact.save',dict(c,name='Changed'))
        _,_,template=self.step();self.assertEqual(template.call_args.args[-1],'Customer');self.assertEqual(self.state()['messages'][-1]['body'],'Hello Customer')
    def test_unapproved_or_unsupported_template_shapes_fail_live_configuration(self):
        for changes in [{'body':'Hello {{2}}'},{'components':[{'type':'HEADER','format':'IMAGE'}]},{'components':[{'type':'BUTTONS','buttons':[{'url':'https://example.test/{{1}}'}]}]}]:
            with self.s.db() as db:self.s._put(db,self.t,'template',dict(self.template,**changes),self.template['id'])
            with self.assertRaises(Problem):self.save([self.tpl()])
