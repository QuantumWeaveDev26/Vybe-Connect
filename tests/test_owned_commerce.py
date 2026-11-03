import tempfile
import threading
import unittest
from pathlib import Path
from store import Store, Problem


class OwnedCommerceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'commerce.db')
        self.ctx = self.store.auth(self.store.setup('Owner', 'owner@example.test', 'test-password-long', 'Business')['token'])
        self.contact = self.act('contact.save', name='Customer', phone='+12025550146')

    def tearDown(self): self.tmp.cleanup()
    def act(self, action, **data): return self.store.action(self.ctx, action, data)
    def product(self, **overrides):
        return self.act('commerce.product.save', **dict(dict(name='Product', sku='SKU-1', price='12.50', currency='INR', stock=3, enabled=True), **overrides))
    def order(self, product, quantity=2):
        return self.act('commerce.order.save', contact_id=self.contact['id'], items=[{'product_id': product['id'], 'quantity': quantity}])
    def transition(self, order, status):
        return self.act('commerce.order.transition', id=order['id'], version=order['version'], status=status)
    def inventory(self): return self.store.state(self.ctx)['owned_commerce']['products'][0]['stock']

    def test_order_prices_are_snapshots_and_transitions_update_stock_once(self):
        p = self.product(); order = self.order(p)
        self.assertEqual(order['total_minor'], 2500)
        self.product(id=p['id'], version=p['version'], price='99.00')
        confirmed = self.transition(order, 'confirmed')
        self.assertEqual(confirmed['total_minor'], 2500)
        self.assertEqual(self.inventory(), 1)
        self.transition(order, 'confirmed'); self.assertEqual(self.inventory(), 1)
        cancelled = self.transition(confirmed, 'cancelled'); self.assertEqual(self.inventory(), 3)
        self.transition(cancelled, 'cancelled'); self.assertEqual(self.inventory(), 3)
        with self.assertRaises(Problem): self.transition(cancelled, 'confirmed')

    def test_concurrent_confirmation_does_not_oversell(self):
        p = self.product(); orders = [self.order(p), self.order(p)]
        barrier = threading.Barrier(2); outcomes = []
        def confirm(order):
            barrier.wait()
            try: self.transition(order, 'confirmed'); outcomes.append('confirmed')
            except Problem as error: outcomes.append(error.code)
        threads = [threading.Thread(target=confirm, args=(o,)) for o in orders]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertCountEqual(outcomes, ['confirmed', 409]); self.assertEqual(self.inventory(), 1)

    def test_insufficient_second_line_rolls_back_first_line(self):
        a = self.product(); b = self.product(sku='SKU-2', stock=0)
        o = self.act('commerce.order.save', contact_id=self.contact['id'], items=[{'product_id': a['id'], 'quantity': 1}, {'product_id': b['id'], 'quantity': 1}])
        with self.assertRaises(Problem): self.transition(o, 'confirmed')
        self.assertEqual(self.inventory(), 3)

    def test_version_and_validation_guards(self):
        p = self.product()
        with self.assertRaises(Problem): self.product(id=p['id'], version=0)
        with self.assertRaises(Problem): self.product(sku='sku-1')
        with self.assertRaises(Problem): self.product(sku='new', price='1.001')
        with self.assertRaises(Problem): self.product(sku='new', stock=True)
        with self.assertRaises(Problem): self.order(p, 0)
        with self.assertRaises(Problem): self.order(p, True)

    def test_fulfilled_orders_cannot_restore_stock_or_be_edited(self):
        o = self.transition(self.order(self.product()), 'confirmed')
        o = self.transition(o, 'fulfilled')
        with self.assertRaises(Problem): self.transition(o, 'cancelled')
        with self.assertRaises(Problem): self.act('commerce.order.save', id=o['id'], version=o['version'], contact_id=self.contact['id'], items=o['items'])
        self.assertEqual(self.inventory(), 1)

    def test_workspace_and_role_boundaries(self):
        p = self.product(); other = self.act('workspace.create', name='Other')
        ctx = dict(self.ctx, tenant_id=other['id'])
        with self.assertRaises(Problem): self.store.action(ctx, 'commerce.order.save', {'contact_id': self.contact['id'], 'items': [{'product_id': p['id'], 'quantity': 1}]})
        with self.assertRaises(Problem) as failure: self.store.action(dict(self.ctx, role='agent'), 'commerce.product.save', {})
        self.assertEqual(failure.exception.code, 403)
