"""Explicit customer/order links and bounded, read-only synced order context."""
import time
from shopify_connector import connector_status
from commerce_service import CommerceError


def order_action(store,ctx,operation,data):
    if ctx['role']!='admin':raise CommerceError('Administrator access required.',403)
    tenant=ctx['tenant_id'];stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if operation=='shopify.order.link':
            if data.get('ownership_confirmed') is not True:raise CommerceError('Confirm that you verified this order belongs to this contact.')
            order=store._get(db,tenant,'shopifyorder',data.get('order_id'))
            contact=store._get(db,tenant,'contact',data.get('contact_id'))
            if order.get('source')!='shopify_api' or order.get('shop')!=connector_status(tenant)['shop']:raise CommerceError('Choose an order synced from the current Shopify shop.')
            links=store._list(db,tenant,'customerorderlink');old=next((x for x in links if x['order_id']==order['id']),{})
            if old and old['contact_id']!=contact['id']:raise CommerceError('This order already belongs to another contact. Unlink it before changing ownership.',409)
            result=store._put(db,tenant,'customerorderlink',dict(order_id=order['id'],contact_id=contact['id'],verified_by=ctx['user']['id'],verified_at=stamp),old.get('id'))
        elif operation=='shopify.order.unlink':
            old=store._get(db,tenant,'customerorderlink',data.get('id'))
            db.execute("DELETE FROM entities WHERE tenant=? AND kind='customerorderlink' AND id=?",(tenant,old['id']));result={'removed':True}
        else:raise CommerceError('Unknown order link action.',404)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,stamp))
    return result


def customer_orders(store,db,tenant,contact):
    """Never infer ownership from text, order number, email or a model decision."""
    shop=connector_status(tenant)['shop'];stamp=int(time.time())
    if not shop:return []
    ids={x['order_id'] for x in store._list(db,tenant,'customerorderlink') if x['contact_id']==contact}
    orders=[x for x in store._list(db,tenant,'shopifyorder') if x['id'] in ids and x.get('source')=='shopify_api' and x.get('shop')==shop and type(x.get('synced')) is int and 0<=stamp-x['synced']<86400]
    orders.sort(key=lambda x:(x['synced'],x['id']),reverse=True)
    return [{k:x[k] for k in ['name','financial_status','fulfillment_status','total_price','synced'] if k in x} for x in orders[:5]]
