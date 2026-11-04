import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class AgentPresetCatalogTests(unittest.TestCase):
    def test_every_visible_preset_saves_and_runs_with_its_original_instructions(self):
        root=Path(__file__).resolve().parents[1]
        script="const fs=require('fs'),vm=require('vm');const c=vm.createContext({setInterval(){}});vm.runInContext(fs.readFileSync('static/assistant.js','utf8'),c);process.stdout.write(vm.runInContext('JSON.stringify(AGENT_PRESETS)',c));"
        presets=json.loads(subprocess.check_output(['node','-e',script],cwd=root,text=True))
        self.assertEqual(len(presets),12);self.assertEqual(len({p[0] for p in presets}),12)
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'catalog.db');ctx=store.auth(store.setup('Owner','catalog@example.test','isolated-test-password','Catalog')['token'])
            other=store.auth(store.login('catalog@example.test','isolated-test-password')['token'],store.action(ctx,'workspace.create',{'name':'Other'})['id'])
            for name,instructions in presets:
                with self.subTest(agent=name):
                    agent=store.action(ctx,'aiagent.save',{'name':name,'instructions':instructions})
                    self.assertFalse(agent.get('schedule_enabled',False))
                    with patch('store.ask_local',return_value=json.dumps({'summary':'No supporting conversations in this workspace.','findings':[]})) as model:
                        run=store.action(ctx,'ai.run',{'agent_id':agent['id']})
                    self.assertEqual(run['status'],'completed');self.assertEqual(model.call_count,1)
                    supplied=model.call_args.args[1]['agent']
                    self.assertEqual(supplied['name'],name);self.assertEqual(supplied['instructions'],instructions)
                    self.assertEqual(supplied['permissions'],'read_only')
                    with self.assertRaises(Problem):store.action(other,'ai.run',{'agent_id':agent['id']})
            state=store.state(ctx)
            self.assertEqual(len(state['aiagents']),12);self.assertEqual(len(state['airuns']),12)
            self.assertEqual(state['messages'],[]);self.assertEqual(state['queue'],[]);self.assertEqual(state['findings'],[])
