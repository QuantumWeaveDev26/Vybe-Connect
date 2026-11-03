import tempfile
import unittest
from pathlib import Path
from store import Store,Problem


class RuleEventTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'events.db');token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
    def tearDown(self):self.tmp.cleanup()
    def rule(self,event,actions=None,**extra):return self.s.action(self.ctx,'rule.save',dict({'name':'Event rule','event':event,'enabled':True,'actions':actions or [{'type':'tag','value':'Matched'}]},**extra))
    def contact(self,**extra):return self.s.action(self.ctx,'contact.save',dict({'name':'Buyer','phone':'919000000001'},**extra))
    def test_contact_creation_runs_once_and_does_not_match_ordinary_messages(self):
        self.rule('contact_created',[{'type':'task','value':'Review new contact'}]);contact=self.contact();self.contact(id=contact['id'])
        self.s.inbound(self.ctx['tenant_id'],{'id':'hello','from':'919000000001','text':{'body':'hello'}})
        self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_attribute_added_and_changed_filter_uses_exact_changed_field(self):
        contact=self.contact();self.rule('attribute_added',trigger_attribute='service');self.contact(id=contact['id'],attributes={'other':'value'})
        self.assertNotIn('Matched',self.s.state(self.ctx)['contacts'][0]['tags'])
        self.contact(id=contact['id'],attributes={'other':'value','service':'Design'});self.assertIn('Matched',self.s.state(self.ctx)['contacts'][0]['tags'])
        self.rule('attribute_changed',[{'type':'task','value':'Service changed'}],trigger_attribute='service')
        self.contact(id=contact['id'],attributes={'other':'value','service':'Design'});self.assertEqual(self.s.state(self.ctx)['tasks'],[])
        self.contact(id=contact['id'],attributes={'other':'value','service':'Support'});self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_rules_do_not_recursively_emit_contact_update_events(self):
        self.rule('contact_created',[{'type':'attribute','field':'from_rule','value':'true'}]);self.rule('attribute_added',[{'type':'task','value':'Must not recurse'}])
        self.contact();state=self.s.state(self.ctx);self.assertEqual(state['tasks'],[]);self.assertEqual(state['contacts'][0]['attributes']['from_rule'],'true')
    def test_status_transitions_trigger_only_when_status_changes(self):
        contact=self.contact();self.rule('conversation_resolved',[{'type':'task','value':'Resolution review'}])
        for _ in range(2):self.s.action(self.ctx,'chat.update',{'id':contact['id'],'status':'solved'})
        self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_human_takeover_suppresses_contact_events(self):
        contact=self.contact();self.rule('contact_updated',[{'type':'task','value':'Must not create'}]);self.s.action(self.ctx,'chat.takeover',{'id':contact['id']});self.contact(id=contact['id'],name='Changed')
        self.assertEqual(self.s.state(self.ctx)['tasks'],[])
    def test_new_real_inbound_contact_event_is_deduplicated(self):
        self.rule('contact_created',[{'type':'task','value':'Welcome review'}]);event={'id':'real_new_contact','from':'919000000001','text':{'body':'Hello'}}
        self.s.inbound(self.ctx['tenant_id'],event);self.s.inbound(self.ctx['tenant_id'],event);self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_invalid_trigger_and_attribute_filter_rejected(self):
        for event in ['call_received','',None]:
            with self.assertRaises(Problem):self.rule(event)
        with self.assertRaises(Problem):self.rule('attribute_changed',trigger_attribute='bad.path')
    def test_execution_history_contains_no_private_source_values(self):
        self.rule('contact_updated');contact=self.contact();self.contact(id=contact['id'],name='PRIVATE VALUE')
        history=self.s.state(self.ctx)['rule_executions'];self.assertEqual(history[-1]['event'],'contact_updated');self.assertNotIn('PRIVATE VALUE',str(history))
    def test_typed_attribute_change_is_not_hidden_by_python_boolean_equality(self):
        contact=self.contact(attributes={'value':True});self.rule('attribute_changed',[{'type':'task','value':'Typed value changed'}],trigger_attribute='value')
        self.contact(id=contact['id'],attributes={'value':1});self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_real_inbound_reopens_once_without_replaying_for_followup_messages(self):
        contact=self.contact();self.s.action(self.ctx,'chat.update',{'id':contact['id'],'status':'solved'});self.rule('conversation_opened',[{'type':'task','value':'Reopened review'}])
        for id in ['one','one','two']:self.s.inbound(self.ctx['tenant_id'],{'id':id,'from':'919000000001','text':{'body':'Hello'}})
        self.assertEqual(len(self.s.state(self.ctx)['tasks']),1)
    def test_csv_import_does_not_trigger_contact_creation_automation(self):
        self.rule('contact_created',[{'type':'task','value':'Must not run from import'}]);self.s.action(self.ctx,'contacts.import',{'csv':'name,phone\nImported,919000000001\n'})
        self.assertEqual(self.s.state(self.ctx)['tasks'],[])
    def test_initial_custom_attributes_do_not_emit_a_second_added_event(self):
        self.rule('attribute_added',[{'type':'task','value':'Only future additions'}]);self.contact(attributes={'service':'Design'})
        self.assertEqual(self.s.state(self.ctx)['tasks'],[])
