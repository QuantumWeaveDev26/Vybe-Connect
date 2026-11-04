"""Opt-in metadata checks; never infer successful payments, delivery, media or inference."""
import base64
import hashlib
import json
import os
import time
from urllib.parse import quote
from business_providers import config
from provider_transport import request,RemoteError
from service_jobs import ServiceError


def fingerprint(tenant,provider):
    if provider in ('payments','billing','shipping'):values=config(tenant,provider)
    elif provider=='meta':
        from meta import settings
        values=settings(tenant)
    elif provider=='openai':
        from ai import openai_key,ai_status
        values={'key':openai_key(tenant),'model':ai_status(tenant)['model']}
    else:raise ServiceError('Unsupported provider.')
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()


def state(store,db,tenant):
    return [dict(provider=check['provider'],checked_at=check['checked_at'],outcome=check['outcome'],
                 scope='metadata only',current=check['fingerprint']==fingerprint(tenant,check['provider']) and int(time.time())-check['checked_at']<86400)
            for check in store._list(db,tenant,'providercheck')]


def check(store,ctx,provider):
    if ctx['role']!='admin':raise ServiceError('Administrator access required.',403)
    if os.environ.get('TW_PROVIDER_READS','false').lower()!='true':raise ServiceError('Enable TW_PROVIDER_READS on the server before making provider metadata requests.')
    tenant=ctx['tenant_id'];digest=fingerprint(tenant,provider)
    try:
        if provider in ('payments','billing'):
            c=config(tenant,provider)
            if not c['KEY_ID'] or not c['KEY_SECRET']:raise ServiceError('Configure Razorpay credentials first.')
            authorization=base64.b64encode((c['KEY_ID']+':'+c['KEY_SECRET']).encode()).decode()
            result=request('https://api.razorpay.com/v1/'+('payment_links?count=1' if provider=='payments' else 'plans?count=1'),headers={'Authorization':'Basic '+authorization})
            if result.get('entity')!='collection':raise ValueError()
        elif provider=='shipping':
            c=config(tenant,provider)
            if not c['TOKEN']:raise ServiceError('Configure Shiprocket credentials first.')
            result=request('https://apiv2.shiprocket.in/v1/external/settings/company/pickup',headers={'Authorization':'Bearer '+c['TOKEN']})
            if not isinstance(result.get('data'),dict):raise ValueError()
        elif provider=='meta':
            from meta import settings
            import re
            c=settings(tenant)
            if not c['TOKEN'] or not re.fullmatch(r'\d+',c['PHONE_ID']) or not re.fullmatch(r'v\d+\.\d+',c['VERSION']):raise ServiceError('Configure Meta token, phone ID and version first.')
            result=request('https://graph.facebook.com/'+c['VERSION']+'/'+c['PHONE_ID']+'?fields=id,display_phone_number,verified_name',headers={'Authorization':'Bearer '+c['TOKEN']})
            if result.get('id')!=c['PHONE_ID']:raise ValueError()
        elif provider=='openai':
            from ai import openai_key,ai_status
            key=openai_key(tenant);model=ai_status(tenant)['model']
            if not key or not model:raise ServiceError('Configure OpenAI key and model first.')
            result=request('https://api.openai.com/v1/models/'+quote(model,safe=''),headers={'Authorization':'Bearer '+key})
            if result.get('id')!=model:raise ValueError()
        else:raise ServiceError('Unsupported provider.')
        outcome='passed'
    except (RemoteError,ValueError):outcome='failed_or_unconfirmed'
    with store.db() as db:
        old=next((c for c in store._list(db,tenant,'providercheck') if c['provider']==provider),{})
        store._put(db,tenant,'providercheck',dict(provider=provider,checked_at=int(time.time()),outcome=outcome,fingerprint=digest),old.get('id'))
    return {'provider':provider,'outcome':outcome,'scope':'metadata only; live transaction/media/inference not verified'}
