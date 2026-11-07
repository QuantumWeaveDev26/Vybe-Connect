"""Unit tests for WhatsApp interactive buttons, voice notes, CSAT, chat widget, and developer API."""
import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from server import make_server
from store import Store
import api_tokens as tokens


class TestInteractiveFeatures(unittest.TestCase):
    def setUp(self):
        os.environ['TW_SANDBOX'] = 'true'
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = Store(Path(self.tmp.name) / 'test.db')
        setup_res = self.s.setup('Admin', 'admin@example.test', 'Password123456!', 'Test Workspace')
        self.token = setup_res['token']
        self.ctx = self.s.auth(self.token)
        self.ws = self.ctx['tenant_id']

    def test_widget_message_and_history(self):
        """Test embeddable website widget message sending and history retrieval."""
        res = self.s.widget_message(self.ws, {
            'visitor_id': 'vis_123',
            'name': 'Alice Visitor',
            'phone': '15550299',
            'message': 'Hello from embeddable chat widget!'
        })
        self.assertTrue(res.get('success'))
        self.assertTrue(res.get('contact_id'))
        self.assertEqual(len(res.get('messages', [])), 1)
        self.assertEqual(res['messages'][0]['body'], 'Hello from embeddable chat widget!')
        self.assertEqual(res['messages'][0]['direction'], 'in')

        # Retrieve widget history
        hist = self.s.widget_history(self.ws, res['contact_id'])
        self.assertEqual(len(hist.get('messages', [])), 1)
        self.assertEqual(hist['messages'][0]['body'], 'Hello from embeddable chat widget!')

    def test_interactive_buttons_send_and_inbound(self):
        """Test sending message with interactive quick-reply buttons and receiving button click."""
        contact = self.s.action(self.ctx, 'contact.save', {
            'name': 'Bob Customer',
            'phone': '1987654321',
            'optin': True
        })
        cid = contact['id']

        # Send outbound message with interactive buttons
        msg = self.s.action(self.ctx, 'message.send', {
            'contact_id': cid,
            'body': 'Please choose an option:',
            'buttons': ['Track Order', 'Speak to Agent']
        })
        self.assertIn('🔘 Track Order · Speak to Agent', msg['body'])
        self.assertEqual(msg['buttons'], ['Track Order', 'Speak to Agent'])

        # Simulate inbound interactive button reply via _inbound
        with self.s.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.s._inbound(db, self.ws, {
                'id': 'wamid_btn_reply_001',
                'from': '1987654321',
                'type': 'interactive',
                'interactive': {
                    'type': 'button_reply',
                    'button_reply': {
                        'id': 'btn_track',
                        'title': 'Track Order'
                    }
                }
            }, simulated=True)

        # Verify inbound message is recorded with button title
        state = self.s.state(self.ctx)
        msgs = [m for m in state['messages'] if m['contact'] == cid]
        inbound_btn = [m for m in msgs if m['direction'] == 'in' and m['body'] == 'Track Order']
        self.assertTrue(len(inbound_btn) >= 1)

    def test_voice_note_transcription(self):
        """Test audio voice note inbound handling and auto-transcription."""
        contact = self.s.action(self.ctx, 'contact.save', {
            'name': 'Charlie Voice',
            'phone': '15550202',
            'optin': True
        })
        cid = contact['id']

        # Simulate inbound audio payload
        with self.s.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.s._inbound(db, self.ws, {
                'id': 'wamid_audio_001',
                'from': '15550202',
                'type': 'audio',
                'audio': {
                    'id': 'media_audio_123',
                    'voice': True,
                    'duration': 12,
                    'transcription': 'Hello, I would like to inquire about my delivery status.'
                }
            }, simulated=True)

        state = self.s.state(self.ctx)
        msgs = [m for m in state['messages'] if m['contact'] == cid]
        voice_msg = [m for m in msgs if '🎙️ [Voice note (12s)]' in m['body']]
        self.assertTrue(len(voice_msg) >= 1)
        self.assertIn('delivery status', voice_msg[0]['body'])

    def test_csat_survey_on_solved_and_rating_reply(self):
        """Test CSAT survey triggered on solved status, and rating parsed from inbound response."""
        contact = self.s.action(self.ctx, 'contact.save', {
            'name': 'Diana Star',
            'phone': '15550303',
            'optin': True
        })
        cid = contact['id']

        # Update chat status to solved
        self.s.action(self.ctx, 'chat.update', {
            'id': cid,
            'status': 'solved'
        })

        # Outbound survey message should have been sent
        state = self.s.state(self.ctx)
        msgs = [m for m in state['messages'] if m['contact'] == cid]
        survey = [m for m in msgs if 'rate your support experience' in m['body'].lower()]
        self.assertTrue(len(survey) >= 1, "CSAT survey message should be triggered on solved")

        # Simulate inbound customer rating '5'
        with self.s.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.s._inbound(db, self.ws, {
                'id': 'wamid_rating_005',
                'from': '15550303',
                'type': 'text',
                'text': {'body': '5 - Excellent service!'}
            }, simulated=True)

        # Check contact record has csat_score 5
        updated_contact = next(c for c in self.s.state(self.ctx)['contacts'] if c['id'] == cid)
        self.assertEqual(updated_contact.get('csat_score'), 5)

        # Check thank-you message was recorded
        msgs_after = [m for m in self.s.state(self.ctx)['messages'] if m['contact'] == cid]
        thank_you = [m for m in msgs_after if 'recorded your rating of 5/5 stars' in m['body'].lower()]
        self.assertTrue(len(thank_you) >= 1)

    def test_developer_transactional_api_send(self):
        """Test POST /api/v1/messages/send developer transactional API with Bearer token."""
        # Call api_send_message using the context
        res = self.s.api_send_message(self.ctx, {
            'phone': '15550404',
            'name': 'API Contact',
            'body': 'Your verification code is 849201',
            'buttons': ['Verify Now', 'Resend']
        })
        self.assertEqual(res['status'], 'simulated')
        self.assertTrue(res['id'])
        self.assertIn('🔘 Verify Now · Resend', res['body'])

        # Verify contact was auto-created and message exists in state
        state = self.s.state(self.ctx)
        contact = next((c for c in state['contacts'] if c['phone'] == '15550404'), None)
        self.assertIsNotNone(contact)
        msgs = [m for m in state['messages'] if m['contact'] == contact['id']]
        self.assertTrue(len(msgs) >= 1)
        self.assertIn('849201', msgs[0]['body'])


class TestHTTPRoutes(unittest.TestCase):
    def setUp(self):
        os.environ['TW_SANDBOX'] = 'true'
        self.tmp = tempfile.TemporaryDirectory()
        self.server = make_server(0, Path(self.tmp.name) / 'http.db')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        res = self.server.store.setup('Admin', 'http-admin@example.test', 'Password123456!', 'HTTP Workspace')
        self.cookie = 'tw_session=' + res['token']
        self.ctx = self.server.store.auth(res['token'])
        self.ws = self.ctx['tenant_id']
        # Create an API token for transactional send
        self.api_token = tokens.create(self.server.store, self.ctx, {
            'name': 'Server Test Token',
            'days': 30,
            'scopes': ['messages:read', 'contacts:read']
        })['token']

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, method='GET', data=None, headers=None):
        port = self.server.server_address[1]
        conn = http.client.HTTPConnection('127.0.0.1', port)
        h = {'Content-Type': 'application/json', **(headers or {})}
        conn.request(method, path, json.dumps(data) if data is not None else None, h)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        try:
            body = json.loads(raw)
        except Exception:
            body = raw.decode('utf-8', errors='replace')
        return resp.status, dict(resp.getheaders()), body

    def test_widget_endpoints(self):
        """Test GET /widget.js, GET /widget-preview, POST /api/widget/message, GET /api/widget/history."""
        # 1. GET /widget.js
        code, headers, body = self.request('/widget.js')
        self.assertIn(code, (200, 201))
        self.assertIn('vybe-widget', body)

        # 2. GET /widget-preview
        code, headers, body = self.request('/widget-preview')
        self.assertIn(code, (200, 201))
        self.assertIn('Embed VYBE Connect on Any Website', body)

        # 3. POST /api/widget/message (Cross-origin from external website, no session cookie)
        code, headers, body = self.request(
            '/api/widget/message',
            method='POST',
            data={
                'workspace': self.ws,
                'name': 'External Visitor',
                'phone': '+15550999',
                'message': 'Need assistance with pricing'
            },
            headers={'Origin': 'https://external-store.example.com'}
        )
        self.assertIn(code, (200, 201))
        self.assertTrue(body.get('success'))
        contact_id = body.get('contact_id')
        self.assertTrue(contact_id)

        # 4. GET /api/widget/history
        code, headers, body = self.request(
            f'/api/widget/history?workspace={self.ws}&contact_id={contact_id}',
            headers={'Origin': 'https://external-store.example.com'}
        )
        self.assertIn(code, (200, 201))
        self.assertEqual(len(body.get('messages', [])), 1)
        self.assertEqual(body['messages'][0]['body'], 'Need assistance with pricing')

    def test_api_v1_messages_send(self):
        """Test POST /api/v1/messages/send with Bearer token authentication."""
        code, headers, body = self.request(
            '/api/v1/messages/send',
            method='POST',
            data={
                'phone': '+15550888',
                'body': 'Your order #5521 has shipped!',
                'buttons': ['Track Package', 'Help']
            },
            headers={
                'Authorization': f'Bearer {self.api_token}',
                'Origin': 'https://backend.mybrand.com'
            }
        )
        self.assertIn(code, (200, 201))
        self.assertTrue(body.get('id'))
        self.assertIn('🔘 Track Package · Help', body.get('body'))


if __name__ == '__main__':
    unittest.main()
