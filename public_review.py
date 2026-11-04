"""Token-free, read-only review data isolated from the real application store."""
import secrets
import tempfile
from pathlib import Path
from store import Store


class PublicReview:
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix='vybe-review-')
        self.store = Store(Path(self.directory.name) / 'review.db')
        token = self.store.setup('Review visitor', 'review@example.test', secrets.token_urlsafe(48), 'VYBE Connect - Review workspace')['token']
        self.context = self.store.auth(token)
        self.store.logout(token)
        self.context['review_only'] = True
        self.context.pop('_session_hash', None)
        self.seed()

    def seed(self):
        # These are explicitly labelled examples, never copied customer records.
        for name, instructions in [
            ('Example - Daily Digest', 'Summarize recorded workload and unanswered questions with supporting sources.'),
            ('Example - Inbox Triage', 'Suggest priorities and reply drafts for human review. Never send a message.'),
        ]:
            self.store.action(self.context, 'aiagent.save', {'name': name, 'instructions': instructions, 'allowed_actions': ['note', 'draft_reply']})
        self.store.action(self.context, 'knowledge.save', {'title': 'Example business policy', 'body': 'This is sample knowledge for reviewing the interface. Replace it with your approved business information after owner setup.', 'enabled': True})
        contact = self.store.action(self.context, 'contact.save', {'name': 'Example customer - review only', 'phone': '+1 202 555 0146', 'tags': ['Review sample'], 'optin': False})
        self.store.action(self.context, 'message.send', {'contact_id': contact['id'], 'body': 'Sample internal note for interface review. No message was sent to a customer.', 'note': True})
        product = self.store.action(self.context, 'commerce.product.save', {'name': 'Example welcome kit', 'sku': 'REVIEW-KIT', 'price': '499.00', 'currency': 'INR', 'stock': 10, 'enabled': True})
        self.store.action(self.context, 'commerce.order.save', {'contact_id': contact['id'], 'items': [{'product_id': product['id'], 'quantity': 1}], 'note': 'Example draft for read-only interface review. No sale or payment occurred.'})
        self.store.action(self.context, 'external-agent.save', {'name': 'Example support agent', 'url': 'https://example.com/review-webhook', 'events': ['message.received'], 'enabled': False})

    def state(self):
        state = self.store.state(self.context)
        state['review_only'] = True
        state['sandbox'] = False
        state['ai'].update(enabled=False, configured=False, paid_allowed=False)
        state['meta'].update(configured=False, live=False)
        return state

    def close(self):
        self.directory.cleanup()
