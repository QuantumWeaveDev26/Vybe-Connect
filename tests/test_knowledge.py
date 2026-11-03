import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store, Problem


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Store(Path(self.tmp.name) / 'knowledge.db')
        self.token = self.s.setup('Owner', 'owner@example.test', 'a-long-test-password', 'Acme')['token']
        self.ctx = self.s.auth(self.token)

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, **kw):
        return self.s.action(self.ctx, 'knowledge.save', dict(title='Returns', body='Returns accepted within 14 days.', enabled=True, **kw))

    def test_sources_persist_and_only_enabled_sources_reach_model(self):
        source = self.save()
        self.s.action(self.ctx, 'knowledge.save', dict(title='Old policy', body='Outdated.', enabled=False))
        self.assertEqual(len(Store(self.s.path).state(self.ctx)['knowledges']), 2)
        with patch('store.ask_local', return_value='According to Returns, 14 days.') as model:
            self.s.action(self.ctx, 'ai.ask', {'question': 'What is the returns policy?'})
        facts = model.call_args.args[1]['knowledge_sources']
        self.assertEqual(facts, [{'id':source['id'], 'title':'Returns', 'body':'Returns accepted within 14 days.'}])
        self.s.action(self.ctx, 'entity.delete', {'kind':'knowledge', 'id':source['id']})
        with patch('store.ask_local', return_value='No current policy supplied.') as model:
            self.s.action(self.ctx, 'ai.ask', {'question':'Policy?'})
        self.assertEqual(model.call_args.args[1]['knowledge_sources'], [])

    def test_other_workspaces_cannot_read_edit_delete_or_use_source(self):
        source = self.save()
        other_id = self.s.action(self.ctx, 'workspace.create', {'name':'Other'})['id']
        other = self.s.auth(self.token, other_id)
        self.assertEqual(self.s.state(other)['knowledges'], [])
        for action, data in [('knowledge.save', dict(source, body='Overwritten')), ('entity.delete', {'kind':'knowledge','id':source['id']})]:
            with self.assertRaises(Problem): self.s.action(other, action, data)
        with patch('store.ask_local', return_value='No sources.') as model:
            self.s.action(other, 'ai.ask', {'question':'Policy?'})
        self.assertEqual(model.call_args.args[1]['knowledge_sources'], [])

    def test_only_admin_can_change_sources_and_content_is_bounded(self):
        self.s.action(self.ctx, 'member.add', {'name':'Agent','email':'agent@example.test','password':'a-long-agent-password','role':'agent'})
        agent = self.s.auth(self.s.login('agent@example.test', 'a-long-agent-password')['token'])
        with self.assertRaises(Problem) as denied:
            self.s.action(agent, 'knowledge.save', {'title':'Bad', 'body':'Policy', 'enabled':True})
        self.assertEqual(denied.exception.code, 403)
        for data in [{'title':'','body':'A'}, {'title':'A','body':'x'*4001}, {'title':'A','body':'A','enabled':'true'}]:
            with self.assertRaises(Problem): self.s.action(self.ctx, 'knowledge.save', data)
        for i in range(8): self.save()
        with self.assertRaisesRegex(Problem, '8 sources'): self.save()
