import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store, Problem


class HandoffTests(unittest.TestCase):
    def test_takeover_pauses_automation_but_keeps_inbound_and_stop_consent(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'TW_SANDBOX':'true'}):
            s=Store(Path(tmp)/'handoff.db');token=s.setup('Owner','owner@example.test','long-enough-password','A')['token'];ctx=s.auth(token)
            c=s.action(ctx,'contact.save',{'name':'Customer','phone':'919000000001','optin':True})
            s.action(ctx,'rule.save',{'name':'Welcome','keyword':'hello','reply':'Draft welcome','enabled':True})
            s.action(ctx,'chat.takeover',{'id':c['id']})
            s.action(ctx,'message.simulate',{'contact_id':c['id'],'body':'hello'})
            state=s.state(ctx)
            self.assertEqual(len(state['messages']),1)
            self.assertTrue(state['contacts'][0]['automation_hold'])
            self.assertEqual(state['contacts'][0]['assignee'],ctx['user']['id'])
            s.action(ctx,'chat.resume',{'id':c['id']})
            s.action(ctx,'message.simulate',{'contact_id':c['id'],'body':'hello again'})
            self.assertEqual(len([m for m in s.state(ctx)['messages'] if m['status']=='draft']),1)
            s.action(ctx,'chat.takeover',{'id':c['id']})
            s.action(ctx,'message.simulate',{'contact_id':c['id'],'body':'STOP'})
            self.assertFalse(s.state(ctx)['contacts'][0]['optin'])
            other=s.auth(token,s.action(ctx,'workspace.create',{'name':'Other'})['id'])
            with self.assertRaises(Problem):s.action(other,'chat.resume',{'id':c['id']})

    def test_graph_handoff_places_contact_on_human_hold(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'TW_SANDBOX':'true'}):
            s=Store(Path(tmp)/'handoff.db');ctx=s.auth(s.setup('Owner','owner@example.test','long-enough-password','A')['token'])
            c=s.action(ctx,'contact.save',{'name':'Customer','phone':'919000000001'})
            s.action(ctx,'flow.save',{'name':'Handoff','keyword':'help','reply':'Team will review.','enabled':True})
            s.action(ctx,'message.simulate',{'contact_id':c['id'],'body':'help'})
            self.assertTrue(s.state(ctx)['contacts'][0]['automation_hold'])
            s.action(ctx,'message.simulate',{'contact_id':c['id'],'body':'help again'})
            self.assertEqual(len([m for m in s.state(ctx)['messages'] if m['status']=='draft']),1)
