import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from store import Store
import ai

class BuiltinAITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name)/'test.db')
        self.ctx = self.store.auth(self.store.setup('Owner', 'owner@example.test', 'super-strong-password-123', 'Acme Corp')['token'])
        self.c = self.store.action(self.ctx, 'contact.save', {'name': 'Alice Smith', 'phone': '919876543210'})
        with self.store.db() as db:
            self.msg = self.store._message(db, self.ctx['tenant_id'], self.c['id'], 'Can you send me your pricing and catalog asap?', 'in', 'received')
        self.env_patch = patch.dict(os.environ, {'TW_AI_ENABLED': 'true', 'TW_AI_PROVIDER': 'builtin', 'TW_PLATFORM_AI_MANAGED': 'false'})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.tmp.cleanup()

    def test_all_12_presets_execute_and_produce_valid_findings_with_builtin_ai(self):
        root = Path(__file__).resolve().parents[1]
        script = "const fs=require('fs'),vm=require('vm');const c=vm.createContext({setInterval(){}});vm.runInContext(fs.readFileSync('static/assistant.js','utf8'),c);process.stdout.write(vm.runInContext('JSON.stringify(AGENT_PRESETS)',c));"
        presets = json.loads(subprocess.check_output(['node', '-e', script], cwd=root, text=True))
        self.assertEqual(len(presets), 12)

        for name, instructions in presets:
            with self.subTest(agent=name):
                agent = self.store.action(self.ctx, 'aiagent.save', {'name': name, 'instructions': instructions})
                run = self.store.action(self.ctx, 'ai.run', {'agent_id': agent['id']})
                self.assertEqual(run['status'], 'completed')
                self.assertTrue(len(run.get('summary', '')) > 0)
                state = self.store.state(self.ctx)
                findings = [f for f in state['findings'] if f['run_id'] == run['id']]
                for f in findings:
                    self.assertEqual(f['status'], 'pending')
                    reviewed = self.store.action(self.ctx, 'finding.review', {'id': f['id'], 'decision': 'approve'})
                    self.assertIn(reviewed['status'], ['applied', 'acknowledged'])

    def test_builtin_ai_chat_provides_grounded_workspace_answers(self):
        chat1 = self.store.action(self.ctx, 'ai.ask', {'question': 'How many contacts do we have?'})
        self.assertIn('Acme Corp has 1 total contact', chat1['messages'][-1]['content'])

        chat2 = self.store.action(self.ctx, 'ai.ask', {'question': 'Draft a follow-up reply for customer', 'id': chat1['id']})
        self.assertIn('draft', chat2['messages'][-1]['content'].lower())
