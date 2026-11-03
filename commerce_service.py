"""Read-only Shopify sync; signed webhook bodies never mutate catalog records directly."""
import hashlib
import json
import re
import time
from shopify_connector import connector_status,fetch_products,fetch_orders,verify_shopify_webhook


class CommerceError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def sync_shopify(store,ctx,kind,cursor=None):
    if ctx['role']!='admin':raise CommerceError('Administrator access required.',403)
    if kind not in ['products','orders']:raise CommerceError('Choose products or orders.')
    result=(fetch_products if kind=='products' else fetch_orders)(ctx['tenant_id'],limit=25,cursor=cursor)
    if not result.get('ok'):raise CommerceError('Shopify sync failed: '+str(result.get('error',{}).get('code','provider_error'))+'.',502)
    tenant=ctx['tenant_id'];entity='shopifyproduct' if kind=='products' else 'shopifyorder';stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');records=store._list(db,tenant,entity)
        for item in result['items']:
            old=next((r for r in records if r['provider_id']==item['id'] and r['shop']==result['shop']),None)
            values={k:v for k,v in item.items() if k!='id'}
            store._put(db,tenant,entity,dict(values,provider_id=item['id'],shop=result['shop'],synced=stamp,source='shopify_api'),old['id'] if old else None)
        previous=next((r for r in store._list(db,tenant,'integration') if r.get('provider')=='shopify' and r.get('shop')==result['shop']),{})
        connection=dict(previous,provider='shopify',shop=result['shop'],api_version=result['api_version'],**{kind+'_last_sync':stamp,kind+'_page_info':result['page_info']})
        store._put(db,tenant,'integration',connection,previous.get('id'))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],'shopify.sync.'+kind,stamp))
    return {'synced':len(result['items']),'page_info':result['page_info'],'kind':kind}


def commerce_state(store,db,tenant):
    status=connector_status(tenant);shop=status.get('shop')
    connection=next((r for r in store._list(db,tenant,'integration') if r.get('provider')=='shopify' and r.get('shop')==shop),{})
    events=[dict(row) for row in db.execute("SELECT event_id,topic,created FROM integration_events WHERE tenant=? AND provider='shopify' ORDER BY created DESC LIMIT 30",(tenant,))]
    return {'status':status,'connection':connection,'products':[r for r in store._list(db,tenant,'shopifyproduct') if r['shop']==shop],'orders':[r for r in store._list(db,tenant,'shopifyorder') if r['shop']==shop],'order_links':store._list(db,tenant,'customerorderlink'),'events':events}


def ingest_shopify_webhook(store,tenant,raw,headers):
    if not verify_shopify_webhook(tenant,raw,headers):raise CommerceError('Invalid Shopify webhook signature or scope.',403)
    normalized={str(k).lower():v for k,v in headers.items()};id=normalized.get('x-shopify-webhook-id','');topic=normalized.get('x-shopify-topic','')
    if not isinstance(id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',id):raise CommerceError('A valid Shopify webhook identifier is required.')
    try:payload=json.loads(raw)
    except (ValueError,TypeError):raise CommerceError('Invalid webhook JSON.') from None
    resource=payload.get('id') if isinstance(payload,dict) else None
    if type(resource) is not int or resource<=0:raise CommerceError('A numeric resource ID is required.')
    digest=hashlib.sha256(raw).hexdigest();stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM tenants WHERE id=?',(tenant,)).fetchone():raise CommerceError('Unknown workspace.',404)
        previous=db.execute('SELECT digest,topic FROM integration_events WHERE tenant=? AND provider=? AND event_id=?',(tenant,'shopify',id)).fetchone()
        if previous:
            if previous['digest']!=digest or previous['topic']!=topic:raise CommerceError('Webhook identifier was reused with different content or topic.',409)
            return {'received':True,'duplicate':True}
        db.execute('INSERT INTO integration_events VALUES(?,?,?,?,?,?)',(tenant,'shopify',id,digest,topic,stamp))
    # Shopify's HMAC covers the raw body, not delivery headers. Trusted read sync
    # with the configured shop token verifies data before local catalog changes.
    return {'received':True,'duplicate':False,'requires_sync':True}
