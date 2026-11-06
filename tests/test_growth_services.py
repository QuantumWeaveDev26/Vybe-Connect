import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
import growth_services as growth
import whatsapp_forms as forms
import meta


class GrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'test.db')
        token=self.store.setup('Owner','owner@growth.test','long-test-password','Growth business')['token']
        self.ctx=self.store.auth(token);self.tenant=self.ctx['tenant_id']
        other=self.store.action(self.ctx,'workspace.create',{'name':'Other business'})
        self.other=self.store.auth(token,other['id'])
        self.contact=self.store.action(self.ctx,'contact.save',{'name':'Customer','phone':'919000000001'})
        self.network=patch('urllib.request.urlopen',side_effect=AssertionError('Tests cannot contact providers'));self.network.start();self.addCleanup(self.network.stop)

    def act(self,op,data,ctx=None):return self.store.action(ctx or self.ctx,'growth.'+op,data)
    def recipe(self,mode='contact'):
        return self.act('recipe.save',{'name':'Incoming event','mode':mode,'mapping':{'phone':'customer.phone','name':'customer.name','source_id':'campaign'},'reply':'Hello {{name}}','enabled':True})
    def event(self,r,event='event-1',payload=None,secret=None):
        raw=json.dumps(payload or {'customer':{'phone':'919000000002','name':'New customer'},'campaign':'campaign-42','optin':True,'last_real_inbound':int(time.time())}).encode()
        return growth.receive(self.store,r['id'],'Bearer '+(secret or r['secret']),event,raw)

    def test_recipe_authorization_deduplication_rotation_and_no_consent(self):
        r=self.recipe('draft');accepted=self.event(r);self.assertTrue(accepted['accepted'])
        self.assertTrue(self.event(r)['duplicate'])
        with self.assertRaises(Problem):self.event(r,payload={'customer':{'phone':'919000000003','name':'Changed'}})
        with self.assertRaises(Problem):self.event(r,'wrong',secret='bad')
        state=self.store.state(self.ctx);c=next(c for c in state['contacts'] if c['id']==accepted['contact_id'])
        self.assertFalse(c['optin']);self.assertFalse(c.get('last_real_inbound'));self.assertEqual(c['attribution']['source_id'],'campaign-42')
        self.assertEqual([m['status'] for m in state['messages']],['draft'])
        self.assertNotIn(r['secret'],json.dumps(state));self.assertNotIn('secret_hash',json.dumps(state))
        rotated=self.act('recipe.rotate',{'id':r['id']})
        with self.assertRaises(Problem):self.event(r,'old-secret')
        self.assertTrue(self.event(r,'new-secret',secret=rotated['secret'])['accepted'])

    def test_recipe_lead_uses_real_crm_schema(self):
        r=self.recipe('lead');self.event(r)
        deal=self.store.state(self.ctx)['deals'][0]
        self.assertEqual(deal['currency'],'INR');self.assertEqual(deal['amount_minor'],0);self.assertEqual(deal['stage'],'new');self.assertIn('closure_due',deal)

    def test_recipe_stale_admin_and_disabled_are_rejected(self):
        r=self.recipe()
        with self.store.db() as db:db.execute("UPDATE members SET role='agent' WHERE tenant=? AND user=?",(self.tenant,self.ctx['user']['id']))
        with self.assertRaises(Problem):self.event(r)
        with self.assertRaises(Problem):self.act('recipe.rotate',{'id':r['id']})

    def test_cross_workspace_records_cannot_be_modified(self):
        r=self.recipe();m=self.act('macro.save',{'name':'Macro','reply':'Hello','note':'','tag':''})
        for op,d in [('recipe.rotate',{'id':r['id']}),('macro.apply',{'id':m['id'],'contact_id':self.contact['id']}),('delete',{'kind':'recipe','id':r['id']})]:
            with self.subTest(op=op),self.assertRaises(Problem):self.act(op,d,self.other)

    def test_snooze_expires_and_inbound_wakes_without_forging_attribution(self):
        self.act('snooze',{'contact_id':self.contact['id'],'until':int(time.time())+3600})
        simulated={'id':'simulated-inbound','from':self.contact['phone'],'text':{'body':'Question'},'referral':{'source_id':'fake-ad','source_type':'ad'}}
        self.store.inbound(self.tenant,simulated,True)
        c=self.store.state(self.ctx)['contacts'][0];self.assertNotIn('attribution',c)
        real=dict(simulated,id='verified-webhook-id',referral={'source_id':'ad-123','source_type':'ad'})
        self.store.inbound(self.tenant,real)
        c=self.store.state(self.ctx)['contacts'][0];self.assertEqual(c['snoozed_until'],0);self.assertEqual(c['attribution']['kind'],'meta_ad')
        self.assertEqual(self.store.state(self.ctx)['growth']['attribution_report'][0]['leads'],1)

    def test_macro_creates_only_drafts_private_notes_and_tags(self):
        r=self.act('macro.save',{'name':'Follow-up','reply':'Hi {{name}}','note':'Checked request','tag':'Follow up'})
        self.act('macro.apply',{'id':r['id'],'contact_id':self.contact['id']})
        state=self.store.state(self.ctx);self.assertEqual({m['status'] for m in state['messages']},{'draft','internal'});self.assertIn('Follow up',state['contacts'][0]['tags']);self.assertEqual(len(state['internal_comments']),1)
        self.act('resolve',{'contact_id':self.contact['id']});self.assertEqual(self.store.state(self.ctx)['growth']['support_report']['resolved'],1)

    def test_branch_membership_and_reports(self):
        with self.assertRaises(Problem):self.act('branch.save',{'name':'Invalid','members':['another-user']})
        branch=self.act('branch.save',{'name':'Bangalore','members':[self.ctx['user']['id']]})
        c=self.act('branch.route',{'contact_id':self.contact['id'],'branch_id':branch['id']})
        self.assertEqual(c['assignee'],self.ctx['user']['id']);self.assertEqual(c['branch_id'],branch['id'])
        self.assertEqual(self.store.state(self.ctx)['growth']['branch_report'][0]['contacts'],1)
        with self.assertRaises(Problem):self.act('delete',{'kind':'branch','id':branch['id']})

    def test_public_articles_require_confirmation_escape_html_and_hide_drafts(self):
        article={'title':'Returns','slug':'returns','body':'<script>bad()</script>','published':False}
        r=self.act('article.save',article)
        self.assertNotIn('<script>',growth.help_page(self.store,self.tenant))
        with self.assertRaises(Problem):growth.help_page(self.store,self.tenant,'returns')
        with self.assertRaises(Problem):self.act('article.save',dict(article,id=r['id'],published=True))
        self.act('article.save',dict(article,id=r['id'],published=True,confirm_public=True))
        page=growth.help_page(self.store,self.tenant,'returns');self.assertIn('&lt;script&gt;',page);self.assertNotIn('<script>',page)
        with self.assertRaises(Problem):growth.help_page(self.store,self.other['tenant_id'],'returns')
        self.act('delete',{'kind':'article','id':r['id']})
        with self.assertRaises(Problem):growth.help_page(self.store,self.tenant,'returns')

    def test_survey_one_time_expiry_and_scores(self):
        r=self.act('survey.create',{'contact_id':self.contact['id']})
        self.assertIn('<form',growth.survey(self.store,r['token']))
        with self.assertRaises(Problem):growth.survey(self.store,r['token'],{'rating':'6'})
        self.assertIn('Thank you',growth.survey(self.store,r['token'],{'rating':'5','comment':'Great'}))
        with self.assertRaises(Problem):growth.survey(self.store,r['token'],{'rating':'1'})
        self.assertEqual(self.store.state(self.ctx)['growth']['support_report']['csat_percent'],100)
        self.assertNotIn(r['token'],json.dumps(self.store.state(self.ctx)))
        other=self.act('survey.create',{'contact_id':self.contact['id']})
        with self.store.db() as db:
            item=self.store._get(db,self.tenant,'csatsurvey',other['id']);self.store._put(db,self.tenant,'csatsurvey',dict(item,expires=1),item['id'])
        with self.assertRaises(Problem):growth.survey(self.store,other['token'])


class WhatsAppFormTests(GrowthTests):
    def form(self):return self.act('form.save',{'title':'Course inquiry','fields':[{'label':'Your name','type':'text','required':True},{'label':'Course','type':'choice','required':True,'options':['Science','Arts']}]})
    def settings(self):return {'TOKEN':'private-test-token','WABA_ID':'123','PHONE_ID':'456','VERSION':'v25.0','LIVE':'true','APP_SECRET':'a'*32,'VERIFY_TOKEN':'verify'}
    def test_form_definition_validation_and_no_implicit_network(self):
        f=self.form();self.assertEqual(f['status'],'local_draft');self.assertEqual(f['definition']['screens'][0]['layout']['children'][0]['children'][-1]['on-click-action']['name'],'complete')
        with self.assertRaises(Problem):self.act('form.save',{'title':'Bad','fields':[{'label':'X','type':'choice','options':['one']}]})
        with self.assertRaises(Problem):self.act('form.create',{'id':f['id']})
        self.assertEqual(self.act('form.export',{'id':f['id']}),f['definition'])

    def test_form_management_requires_confirmed_provider_results(self):
        f=self.form()
        with patch('meta.status',return_value={'configured':True,'live':True}),patch('meta.settings',return_value=self.settings()),patch('meta.graph_request',return_value={'id':'789'}) as graph:
            f=self.act('form.create',{'id':f['id'],'confirm':True});self.assertEqual(f['meta_id'],'789');self.assertEqual(graph.call_args.args[2],'flows')
            with self.assertRaises(Problem):self.act('form.publish',{'id':f['id'],'confirm':True})
            with patch('whatsapp_forms.upload',return_value={'success':True,'validation_errors':[]}):self.act('form.upload',{'id':f['id'],'confirm':True})
            graph.return_value={'success':True};f=self.act('form.publish',{'id':f['id'],'confirm':True});self.assertEqual(f['status'],'PUBLISHED')
            with self.assertRaises(Problem):self.act('form.save',{'id':f['id'],'title':'Edited','fields':f['fields']})

    def test_live_form_window_nonce_and_correlated_submission(self):
        f=self.form()
        with self.store.db() as db:self.store._put(db,self.tenant,'whatsappform',dict(f,meta_id='789',status='PUBLISHED'),f['id'])
        with patch('meta.status',return_value={'configured':True,'live':True}),patch('meta.settings',return_value=self.settings()),patch('meta.graph_request',return_value={'messages':[{'id':'wamid.form'}]}) as graph:
            d={'id':f['id'],'contact_id':self.contact['id'],'nonce':'request-1','confirm':True}
            with self.assertRaises(Problem):self.act('form.send',d)
            graph.assert_not_called()
            self.store.inbound(self.tenant,{'id':'customer-inbound','from':self.contact['phone'],'text':{'body':'Please send form'}})
            self.act('form.send',d)
            token=graph.call_args.args[4]['interactive']['action']['parameters']['flow_token']
            with self.assertRaises(Problem):self.act('form.send',d)
            event={'id':'form-submission','from':self.contact['phone'],'type':'interactive','interactive':{'nfm_reply':{'response_json':json.dumps({'flow_token':token,'question_1':'Student','question_2':'1'})}}}
            self.store.inbound(self.tenant,event);self.store.inbound(self.tenant,dict(event,id='duplicate-response'))
            answers=self.store.state(self.ctx)['growth']['form_responses'];self.assertEqual(len(answers),1);self.assertEqual(answers[0]['answers']['question_2'],'Arts')

    def test_uncertain_creation_never_blindly_retries(self):
        f=self.form()
        with patch('meta.status',return_value={'configured':True,'live':True}),patch('meta.settings',return_value=self.settings()),patch('meta.graph_request',side_effect=meta.ProviderError('Unknown result')) as graph:
            with self.assertRaises(Problem):self.act('form.create',{'id':f['id'],'confirm':True})
            with self.assertRaises(Problem):self.act('form.create',{'id':f['id'],'confirm':True})
            self.assertEqual(graph.call_count,1)
