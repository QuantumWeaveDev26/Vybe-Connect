"""Opt-in metadata checks; never infer successful payments, delivery, media or inference."""
import base64
import hashlib
import hmac
import json
import os
import time
from urllib.parse import quote,urlencode
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
    return hashlib.sha256(json.dumps(dict(check_version=3 if provider=='meta' else 2,values=values),sort_keys=True).encode()).hexdigest()


def state(store,db,tenant):
    return [dict(provider=check['provider'],checked_at=check['checked_at'],outcome=check['outcome'],
                 scope='metadata only',reason=check.get('reason',''),hint=diagnostic_hint(check.get('reason','')),http_status=check.get('http_status'),provider_code=check.get('provider_code'),current=check['fingerprint']==fingerprint(tenant,check['provider']) and int(time.time())-check['checked_at']<86400)
            for check in store._list(db,tenant,'providercheck')]


def check(store,ctx,provider):
    if ctx['role']!='admin':raise ServiceError('Administrator access required.',403)
    if os.environ.get('TW_PROVIDER_READS','false').lower()!='true':raise ServiceError('Enable TW_PROVIDER_READS on the server before making provider metadata requests.')
    tenant=ctx['tenant_id'];digest=fingerprint(tenant,provider)
    stage='provider_access';http_status=None;provider_code=None
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
            if not c['TOKEN'] or not all(re.fullmatch(r'\d+',c[key]) for key in ('PHONE_ID','WABA_ID')) or not c['APP_SECRET'] or not re.fullmatch(r'v\d+\.\d+',c['VERSION']):raise ServiceError('Configure Meta token, phone ID, WABA ID, app secret and version first.')
            proof=hmac.new(c['APP_SECRET'].encode(),c['TOKEN'].encode(),hashlib.sha256).hexdigest()
            base='https://graph.facebook.com/'+c['VERSION']+'/'
            headers={'Authorization':'Bearer '+c['TOKEN']}
            def read(object_id,edge='',**query):
                return request(base+object_id+('/'+edge if edge else '')+'?'+urlencode(dict(query,appsecret_proof=proof)),headers=headers)
            stage='phone_access'
            result=read(c['PHONE_ID'],fields='id')
            if result.get('id')!=c['PHONE_ID']:stage='phone_identity';raise ValueError()
            # A responding phone is insufficient: it must belong to this WABA.
            after=None;seen=set();member=False
            for _ in range(10):
                query={'fields':'id','limit':100}
                if after:query['after']=after
                stage='waba_access'
                page=read(c['WABA_ID'],'phone_numbers',**query)
                if not isinstance(page.get('data'),list):raise ValueError()
                if any(isinstance(item,dict) and item.get('id')==c['PHONE_ID'] for item in page['data']):member=True;break
                paging=page.get('paging',{})
                after=paging.get('cursors',{}).get('after') if paging.get('next') else None
                if not isinstance(after,str) or not after or len(after)>2048 or after in seen:break
                seen.add(after)
            if not member:stage='phone_waba_membership';raise ValueError()
            stage='template_access'
            templates=read(c['WABA_ID'],'message_templates',fields='id',limit=1)
            if not isinstance(templates.get('data'),list):raise ValueError()
        elif provider=='openai':
            from ai import openai_key,ai_status
            key=openai_key(tenant);model=ai_status(tenant)['model']
            if not key or not model:raise ServiceError('Configure OpenAI key and model first.')
            result=request('https://api.openai.com/v1/models/'+quote(model,safe=''),headers={'Authorization':'Bearer '+key})
            if result.get('id')!=model:raise ValueError()
        else:raise ServiceError('Unsupported provider.')
        outcome='passed';stage=''
    except (RemoteError,ValueError) as failure:
        import re
        match=re.search(r'HTTP (\d{3})',str(failure))
        http_status=getattr(failure,'http_status',None) or (int(match[1]) if match else None)
        provider_code=getattr(failure,'provider_code',None)
        if provider=='meta' and provider_code==190:stage='meta_token_access'
        outcome='failed_or_unconfirmed'
    with store.db() as db:
        old=next((c for c in store._list(db,tenant,'providercheck') if c['provider']==provider),{})
        store._put(db,tenant,'providercheck',dict(provider=provider,checked_at=int(time.time()),outcome=outcome,fingerprint=digest,reason=stage,http_status=http_status,provider_code=provider_code),old.get('id'))
    return {'provider':provider,'outcome':outcome,'scope':'metadata only; live transaction/media/inference not verified','reason':stage,'hint':diagnostic_hint(stage),'http_status':http_status,'provider_code':provider_code}


def diagnostic_hint(reason):
    return {
        'meta_token_access':'Meta rejected the access token. Replace it privately with a valid token that has access to this WhatsApp account.',
        'phone_access':'Could not verify the configured Phone Number ID. Check token access, expiry and app permissions.',
        'phone_identity':'Meta did not return the configured Phone Number ID. Copy the numeric Phone Number ID from API Setup.',
        'waba_access':'Could not read phone numbers for the configured WABA. Check the WhatsApp Business Account ID and token access.',
        'phone_waba_membership':'The configured Phone Number ID was not found in this WABA. Copy both IDs from the same selected number in Meta API Setup.',
        'template_access':'Phone/WABA pairing passed, but templates could not be read. Check template-management permissions.',
        'provider_access':'Provider access could not be verified. Check credentials and account permissions.'
    }.get(reason,'')
