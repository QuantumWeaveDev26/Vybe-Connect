import json
import http.client
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from server import make_server


class PublicReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'TW_PUBLIC_REVIEW': 'true', 'TW_DEPLOYMENT': 'local', 'TW_BIND': '127.0.0.1', 'TW_AI_ENABLED': 'false'})
        self.environment.start()
        self.server = make_server(0, Path(self.directory.name) / 'real.db')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        if self.server.review: self.server.review.close()
        self.thread.join()
        self.environment.stop()
        self.directory.cleanup()

    def request(self, path, method='GET', data=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        body = json.dumps(data) if data is not None else None
        connection.request(method, path, body, {'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:' + str(self.server.server_port)})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_review_does_not_claim_owner_or_issue_a_session(self):
        status, headers, raw = self.request('/api/review/state')
        self.assertEqual(status, 200)
        state = json.loads(raw)
        self.assertTrue(state['review_only'])
        self.assertTrue(state['context']['review_only'])
        self.assertFalse(self.server.store.initialized())
        self.assertNotIn('Set-Cookie', headers)
        self.assertFalse(state['ai']['enabled'])
        self.assertFalse(state['meta']['live'])
        self.assertTrue(all(not agent.get('schedule_enabled') for agent in state['aiagents']))
        with self.server.review.store.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 0)

    def test_no_write_or_private_api_is_unlocked(self):
        self.request('/api/review/state')
        self.assertEqual(self.request('/api/state')[0], 401)
        self.assertEqual(self.request('/api/action', 'POST', {'action': 'contact.save', 'data': {'name': 'Bad', 'phone': '+12025550147'}})[0], 401)
        self.assertEqual(self.request('/api/review/action', 'POST', {'action': 'ai.run'})[0], 403)
        self.assertEqual(self.request('/api/review/unknown')[0], 404)
        self.assertFalse(self.server.store.initialized())

    def test_real_workspace_records_never_enter_review(self):
        token = self.server.store.setup('Private owner', 'owner@example.test', 'private-owner-password', 'Private client')['token']
        ctx = self.server.store.auth(token)
        self.server.store.action(ctx, 'contact.save', {'name': 'PRIVATE CLIENT RECORD', 'phone': '+12025550148'})
        status, _, raw = self.request('/api/review/state')
        self.assertEqual(status, 200)
        self.assertNotIn(b'PRIVATE CLIENT RECORD', raw)
        self.assertNotIn(ctx['tenant_id'].encode(), raw)
        self.assertNotIn(b'owner@example.test', raw)

    def test_disabled_review_is_not_public(self):
        review = self.server.review
        self.server.review = None
        try:
            self.assertEqual(self.request('/api/review/state')[0], 404)
            self.assertFalse(json.loads(self.request('/api/bootstrap')[2])['review_available'])
        finally:
            self.server.review = review

    def test_owner_route_and_production_setup_stay_protected(self):
        from dataclasses import replace
        origin = 'https://review.example.test'
        self.server.deployment = replace(self.server.deployment, production=True, public_origin=origin, authority='review.example.test', setup_token='test-only-owner-setup-token-at-least-32-characters')
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {'Host':'review.example.test', 'Origin':origin, 'Content-Type':'application/json'}
        connection.request('POST','/api/setup',json.dumps({'name':'Visitor','email':'visitor@example.test','password':'long-visitor-password','business':'Visitor'}),headers)
        response = connection.getresponse()
        self.assertEqual(response.status,403)
        response.read()
        connection.close()
        self.assertFalse(self.server.store.initialized())
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request('GET','/owner',headers={'Host':'review.example.test'})
        response = connection.getresponse()
        self.assertEqual(response.status,200)
        self.assertIn(b'VYBE Connect',response.read())
        connection.close()
