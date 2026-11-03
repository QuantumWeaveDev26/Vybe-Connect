import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class AiTests(unittest.TestCase):
    def test_selected_contact_is_not_excluded_by_global_twenty_contact_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp)/'ai.db');ctx=s.auth(s.setup('Owner','owner@example.test','long-enough-password','A')['token'])
            selected=None
            for i in range(21):
                c=s.action(ctx,'contact.save',{'name':'Customer '+str(i),'phone':str(919000000000+i)})
                if i==0:selected=c
                with s.db() as db:s._message(db,ctx['tenant_id'],c['id'],'Question '+str(i),'in','received',ts=100+i)
            with patch('store.ask_local',return_value='The selected customer asked Question 0.') as model:
                s.action(ctx,'ai.ask',{'question':'Summarize this chat','contact_id':selected['id']})
            context=model.call_args.args[1]
            self.assertEqual(len(context['recent_conversations']),1)
            self.assertEqual(context['recent_conversations'][0]['messages'][0]['body'],'Question 0')

    def test_chat_keeps_agent_identity_and_selected_contact_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp)/'ai.db');ctx=s.auth(s.setup('Owner','owner@example.test','long-enough-password','A')['token'])
            c=s.action(ctx,'contact.save',{'name':'Buyer','phone':'919000000001'})
            other=s.action(ctx,'contact.save',{'name':'Other','phone':'919000000002'})
            with s.db() as db:
                s._message(db,ctx['tenant_id'],c['id'],'Pricing please','in','received')
                s._message(db,ctx['tenant_id'],other['id'],'Different customer','in','received')
            agent=s.action(ctx,'aiagent.save',{'name':'Triage','instructions':'Analyze workload.'})
            with patch('store.ask_local',return_value='Buyer asked for pricing.') as model:
                chat=s.action(ctx,'ai.ask',{'question':'Summarize this chat','agent_id':agent['id'],'contact_id':c['id'],'mode':'summary'})
            context=model.call_args.args[1]
            self.assertEqual([x['contact_id'] for x in context['recent_conversations']],[c['id']])
            self.assertEqual(chat['agent_id'],agent['id'])
            with patch('store.ask_local',return_value='Answer'):
                with self.assertRaisesRegex(Problem,'new chat'):s.action(ctx,'ai.ask',{'id':chat['id'],'question':'Switch agent','agent_id':''})

    def test_agent_analysis_receives_real_conversations_without_sending(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp)/'ai.db');ctx=s.auth(s.setup('Owner','owner@example.test','long-enough-password','A')['token'])
            c=s.action(ctx,'contact.save',{'name':'Buyer','phone':'919000000001'})
            with s.db() as db:s._message(db,ctx['tenant_id'],c['id'],'Can I buy this today?','in','received',ts=100)
            a=s.action(ctx,'aiagent.save',{'name':'Buying intent','instructions':'Suggest contacts for human review.'})
            with patch('store.ask_local',return_value='Buyer may be interested. Review before contacting.') as model:
                s.action(ctx,'ai.ask',{'question':'Find buying intent.','agent_id':a['id']})
            conversation=model.call_args.args[1]['recent_conversations'][0]
            self.assertEqual(conversation['contact_name'],'Buyer')
            self.assertEqual(conversation['messages'][0]['body'],'Can I buy this today?')
            self.assertEqual(len(s.state(ctx)['messages']),1)
            self.assertEqual(s.state(ctx)['queue'],[])

    def test_ai_unconfigured_returns_error_instead_of_canned_answer(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'TW_AI_ENABLED':'false'}):
            s=Store(Path(tmp)/'ai.db');ctx=s.auth(s.setup('Owner','owner@example.test','long-enough-password','A')['token'])
            with self.assertRaisesRegex(Problem,'not configured'):s.action(ctx,'ai.ask',{'question':'What is my reply rate?'})

    def test_ai_history_is_private_to_user_within_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp)/'ai.db');owner=s.auth(s.setup('Owner','owner@example.test','long-enough-password','A')['token'])
            with patch('store.ask_local',return_value='There are no delivered messages yet.'):
                s.action(owner,'ai.ask',{'question':'What was delivered?'})
            s.action(owner,'member.add',{'name':'Agent','email':'agent@example.test','password':'another-long-password','role':'agent'})
            agent=s.auth(s.login('agent@example.test','another-long-password')['token'])
            self.assertEqual(s.state(agent)['aichats'],[])
