"""Workspace-owned catalogue and manual orders; no payments or provider writes."""
import re
import time
from decimal import Decimal, InvalidOperation
from commerce_service import CommerceError

CURRENCIES = {'INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD', 'AUD', 'CAD'}


def text(value, label, maximum=120):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise CommerceError('Enter a valid ' + label + '.')
    return value.strip()


def integer(value, label, maximum=1000000):
    if type(value) is not int or not 0 <= value <= maximum:
        raise CommerceError(label + ' must be a whole number between 0 and ' + str(maximum) + '.')
    return value


def money(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{1,9}(?:\.\d{1,2})?', value):
        raise CommerceError('Use a nonnegative price with at most two decimal places.')
    try:
        return int(Decimal(value) * 100)
    except (InvalidOperation, ValueError):
        raise CommerceError('Enter a valid unit price.') from None


def version(record, data):
    if type(data.get('version')) is not int or data['version'] != record['version']:
        raise CommerceError('This record changed. Refresh before saving.', 409)


def state(store, db, tenant):
    return {'products': store._list(db, tenant, 'catalogproduct'),
            'orders': store._list(db, tenant, 'salesorder'),
            'events': store._list(db, tenant, 'commerceevent')[-200:]}


def action(store, ctx, operation, data):
    if ctx['role'] != 'admin':
        raise CommerceError('Administrator access required for commerce changes.', 403)
    tenant = ctx['tenant_id']
    stamp = int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if operation == 'commerce.product.save':
            old = store._get(db, tenant, 'catalogproduct', data['id']) if data.get('id') else {}
            if old: version(old, data)
            sku = text(data.get('sku'), 'SKU', 60)
            if any(p['sku'].casefold() == sku.casefold() and p['id'] != old.get('id') for p in store._list(db, tenant, 'catalogproduct')):
                raise CommerceError('This SKU already exists in this workspace.', 409)
            currency = data.get('currency')
            if currency not in CURRENCIES: raise CommerceError('Choose a supported currency.')
            enabled = data.get('enabled', True)
            if type(enabled) is not bool: raise CommerceError('Availability must be true or false.')
            values = dict(name=text(data.get('name'), 'product name'), sku=sku, currency=currency,
                          unit_price_minor=money(data.get('price')), stock=integer(data.get('stock'), 'Stock'),
                          enabled=enabled, version=old.get('version', 0) + 1, updated=stamp)
            result = store._put(db, tenant, 'catalogproduct', values, old.get('id'))
        elif operation == 'commerce.order.save':
            old = store._get(db, tenant, 'salesorder', data['id']) if data.get('id') else {}
            if old:
                version(old, data)
                if old['status'] != 'draft': raise CommerceError('Only draft orders can be edited.', 409)
            contact = store._get(db, tenant, 'contact', data.get('contact_id'))
            items = data.get('items')
            if not isinstance(items, list) or not 1 <= len(items) <= 50:
                raise CommerceError('Choose between 1 and 50 product lines.')
            lines, ids, currency = [], set(), None
            for item in items:
                if not isinstance(item, dict): raise CommerceError('Use valid order lines.')
                product = store._get(db, tenant, 'catalogproduct', item.get('product_id'))
                if not product['enabled']: raise CommerceError('An order product is unavailable.')
                quantity = integer(item.get('quantity'), 'Quantity', 10000)
                if quantity == 0 or product['id'] in ids: raise CommerceError('Use one positive-quantity line per product.')
                ids.add(product['id'])
                if currency and currency != product['currency']: raise CommerceError('All order lines must use the same currency.')
                currency = product['currency']
                lines.append(dict(product_id=product['id'], name=product['name'], sku=product['sku'],
                                  quantity=quantity, unit_price_minor=product['unit_price_minor']))
            note = data.get('note', '')
            if not isinstance(note, str) or len(note) > 2000: raise CommerceError('Use an order note up to 2000 characters.')
            total = sum(x['quantity'] * x['unit_price_minor'] for x in lines)
            if total > 9000000000000: raise CommerceError('Order total exceeds the supported limit.')
            result = store._put(db, tenant, 'salesorder', dict(contact_id=contact['id'], items=lines,
                currency=currency, total_minor=total,
                status='draft', note=note.strip(), created=old.get('created', stamp), updated=stamp,
                version=old.get('version', 0) + 1), old.get('id'))
        elif operation == 'commerce.order.transition':
            old = store._get(db, tenant, 'salesorder', data.get('id'))
            target = data.get('status')
            if target not in {'confirmed', 'fulfilled', 'cancelled'}: raise CommerceError('Choose a valid order status.')
            # A repeated submission cannot consume or release inventory twice.
            if target == old['status']: return old
            version(old, data)
            allowed = {'draft': {'confirmed', 'cancelled'}, 'confirmed': {'fulfilled', 'cancelled'}}
            if target not in allowed.get(old['status'], set()): raise CommerceError('This order cannot make that transition.', 409)
            if target == 'cancelled':
                jobs=store._list(db,tenant,'servicejob')
                for payment in [j for j in jobs if j['kind']=='payments.link' and j['reference']==old['id']]:
                    refunded=any(j['kind']=='payments.refund' and j['reference']==payment['id'] and j.get('result',{}).get('provider_status')=='processed' for j in jobs)
                    if payment['status'] not in ('failed',) and payment.get('result',{}).get('provider_status') not in ('cancelled','expired') and not refunded:
                        raise CommerceError('Cancel/reconcile the payment link or complete its refund before cancelling this order.',409)
                if any(j['kind']=='shipping.order' and j['reference']==old['id'] and j['status']!='failed' and j.get('result',{}).get('provider_status')!='cancelled' for j in jobs):
                    raise CommerceError('A shipment is booked or uncertain. Resolve it with the courier before cancelling local stock.',409)
            if target == 'confirmed':
                store._get(db, tenant, 'contact', old['contact_id'])
                for line in old['items']:
                    product = store._get(db, tenant, 'catalogproduct', line['product_id'])
                    if not product['enabled'] or product['stock'] < line['quantity']:
                        raise CommerceError('Insufficient stock or unavailable product: ' + line['name'], 409)
                    product.update(stock=product['stock'] - line['quantity'], version=product['version'] + 1, updated=stamp)
                    store._put(db, tenant, 'catalogproduct', product, product['id'])
            if target == 'cancelled' and old['status'] == 'confirmed':
                for line in old['items']:
                    product = store._get(db, tenant, 'catalogproduct', line['product_id'])
                    product.update(stock=product['stock'] + line['quantity'], version=product['version'] + 1, updated=stamp)
                    store._put(db, tenant, 'catalogproduct', product, product['id'])
            result = store._put(db, tenant, 'salesorder', dict(old, status=target, version=old['version'] + 1, updated=stamp), old['id'])
        else:
            raise CommerceError('Unknown commerce operation.', 404)
        store._put(db, tenant, 'commerceevent', dict(operation=operation, record_id=result['id'],
                       actor=ctx['user']['name'], created=stamp, status=result.get('status', ''), version=result['version']))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',
                   (tenant, ctx['user']['name'], operation, stamp))
        return result
