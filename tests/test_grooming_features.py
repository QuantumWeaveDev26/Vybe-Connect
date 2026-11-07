"""Unit tests for newly added grooming features:
- Agent collision presence & typing indicators
- Sandbox simulation (inbound message & delivery status)
- Dynamic CSV column mapping & preview
- Flow graph webhook node
- Customer AI sentiment / talk to human handoff
- WooCommerce webhook receiver
"""
import io
import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from store import Store, Problem
from flows import validate_graph, run_graph
import customer_assistant


class TestGroomingFeatures(unittest.TestCase):
    def setUp(self):
        import os
        os.environ['TW_SANDBOX'] = 'true'
        self.tmp = TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.store = Store(self.db_path)
        self.tenant_id = "0123456789abcdef"
        with self.store.db() as db:
            self.store._new_user(db, "Admin User", "admin@example.com", "SecretPass1234")
            self.store._new_user(db, "Agent Sarah", "sarah@example.com", "SecretPass1234")
            admin_id = db.execute("SELECT id FROM users WHERE email='admin@example.com'").fetchone()["id"]
            sarah_id = db.execute("SELECT id FROM users WHERE email='sarah@example.com'").fetchone()["id"]
            db.execute("INSERT INTO tenants VALUES(?, 'Acme Corp')", (self.tenant_id,))
            db.execute("INSERT INTO members VALUES(?, ?, 'admin')", (self.tenant_id, admin_id))
            db.execute("INSERT INTO members VALUES(?, ?, 'agent')", (self.tenant_id, sarah_id))
            self.admin_ctx = {'tenant_id': self.tenant_id, 'user': {'id': admin_id, 'name': 'Admin User'}, 'role': 'admin'}
            self.sarah_ctx = {'tenant_id': self.tenant_id, 'user': {'id': sarah_id, 'name': 'Agent Sarah'}, 'role': 'agent'}

    def tearDown(self):
        self.tmp.cleanup()

    def test_agent_presence_and_collision_tracking(self):
        # Admin records viewing presence on contact-100
        res = self.store.action(self.admin_ctx, 'chat.presence', {'contact_id': 'contact-100', 'status': 'viewing'})
        # Sarah should see Admin's active presence
        presences = self.store.get_active_presences(self.tenant_id, contact_id='contact-100', exclude_user=self.sarah_ctx['user']['id'])
        self.assertEqual(len(presences), 1)
        self.assertEqual(presences[0]['user_name'], 'Admin User')
        self.assertEqual(presences[0]['status'], 'viewing')

        # Admin updates status to typing
        self.store.action(self.admin_ctx, 'chat.presence', {'contact_id': 'contact-100', 'status': 'typing'})
        presences2 = self.store.get_active_presences(self.tenant_id, contact_id='contact-100', exclude_user=self.sarah_ctx['user']['id'])
        self.assertEqual(presences2[0]['status'], 'typing')

    def test_sandbox_simulate_inbound_and_status(self):
        # Simulate inbound message from customer
        res = self.store.action(self.admin_ctx, 'sandbox.simulate_inbound', {
            'phone': '+15550100',
            'body': 'Hello, I need pricing information.'
        })
        self.assertTrue(res['simulated'])
        self.assertTrue(res['external_id'].startswith('mock_in_'))

        # Check contact was created
        state = self.store.state(self.admin_ctx)
        contact = next((c for c in state['contacts'] if c['phone'] == '15550100'), None)
        self.assertIsNotNone(contact)

        # Check message was stored
        msg = next((m for m in state['messages'] if m['id'] == res['message_id']), None)
        self.assertIsNotNone(msg)
        self.assertEqual(msg['direction'], 'in')

        # Outbound message + status simulation
        out_msg = self.store.action(self.admin_ctx, 'message.send', {'contact_id': contact['id'], 'body': 'Pricing starts at $20.'})
        status_res = self.store.action(self.admin_ctx, 'sandbox.simulate_status', {'message_id': out_msg['id'], 'status': 'delivered'})
        self.assertTrue(status_res['simulated'])

        # Read back message status
        with self.store.db() as db:
            row = db.execute("SELECT status FROM messages WHERE id=?", (out_msg['id'],)).fetchone()
            self.assertEqual(row['status'], 'delivered')

    def test_dynamic_csv_import_with_mapping(self):
        csv_data = "Customer,Mobile,City,VIP\nAlice,+15550011,New York,yes\nBob,+15550012,London,no\n"
        
        # Test preview mode
        preview = self.store.action(self.admin_ctx, 'contacts.import', {'csv': csv_data, 'preview': True})
        self.assertIn('headers', preview)
        self.assertEqual(preview['headers'], ['Customer', 'Mobile', 'City', 'VIP'])
        self.assertEqual(len(preview['preview']), 2)

        # Test actual import with dynamic mapping and batch tag
        res = self.store.action(self.admin_ctx, 'contacts.import', {
            'csv': csv_data,
            'mapping': {
                'name': 'Customer',
                'phone': 'Mobile',
                'attributes': {'city': 'City', 'vip_status': 'VIP'}
            },
            'tags': ['Nov-Promo']
        })
        self.assertEqual(res['imported'], 2)
        self.assertEqual(len(res['errors']), 0)

        # Verify contact record and attributes
        state = self.store.state(self.admin_ctx)
        alice = next(c for c in state['contacts'] if c['phone'] == '15550011')
        self.assertEqual(alice['name'], 'Alice')
        self.assertIn('Nov-Promo', alice['tags'])
        self.assertEqual(alice['attributes']['city'], 'New York')

    def test_flow_webhook_node(self):
        # Valid flow with a webhook node
        graph = {
            'start': 'start_node',
            'nodes': [
                {'id': 'start_node', 'type': 'message', 'text': 'Processing your request...', 'next': 'call_api'},
                {'id': 'call_api', 'type': 'webhook', 'url': 'https://example.com/api/order', 'method': 'POST', 'save_to': 'order_status', 'next': 'team'},
                {'id': 'team', 'type': 'handoff'}
            ]
        }
        validated = validate_graph(graph)
        self.assertEqual(len(validated['nodes']), 3)

        # Run flow
        contact = {'id': 'c1', 'name': 'Charlie', 'phone': '15550099', 'attributes': {}, 'tags': []}
        c_out, messages = run_graph({'id': 'f1', 'graph': validated}, contact, 'start')
        self.assertEqual(messages, ['Processing your request...'])
        self.assertEqual(c_out['attributes']['order_status'], 'ok')

    def test_customer_ai_sentiment_and_human_handoff(self):
        # Test sentiment / talk to human pattern detection
        test_questions = [
            "Please let me speak to a human",
            "I want to talk to an agent immediately",
            "This is terrible service, I've been cheated",
            "Connect me to your representative",
            "I want to file a complaint"
        ]
        pattern = r'\b(talk to (?:an? )?(?:human|agent)|speak (?:to|with) (?:an? )?(?:human|agent)|human agent|real person|representative|executive|complaint|cheated|scam|fraud|terrible service|worst service|useless service|escalate to manager)\b'
        for q in test_questions:
            self.assertTrue(
                bool(customer_assistant.re.search(pattern, q, customer_assistant.re.IGNORECASE)),
                f"Failed to detect human sentiment in: {q}"
            )

    def test_woocommerce_webhook_ingest(self):
        from commerce_service import ingest_woocommerce_webhook
        payload = json.dumps({'id': 1001, 'status': 'processing', 'total': '99.00'}).encode('utf-8')
        headers = {
            'X-WC-Webhook-Topic': 'order.created',
            'X-WC-Webhook-ID': 'wc_evt_1001'
        }
        res = ingest_woocommerce_webhook(self.store, self.tenant_id, payload, headers)
        self.assertTrue(res['received'])
        self.assertEqual(res['provider'], 'woocommerce')
        self.assertEqual(res['topic'], 'order.created')


if __name__ == '__main__':
    unittest.main()
