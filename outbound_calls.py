"""Explicit outbound calling; durable attempts and provider permission checks."""
import hashlib
import os
import re
import time
from urllib.parse import urlencode
from meta import settings
from provider_transport import request,RemoteError
from service_jobs import ServiceError


def remote(tenant,edge,method='GET',payload=None,query=None):
    import hmac
    c=settings(tenant)
    if not c['TOKEN'] or not re.fullmatch(r'\d+',c['PHONE_ID']) or not re.fullmatch(r'v\d+\.\d+',c['VERSION']):raise ServiceError('Configure Meta calling credentials first.')
    params=dict(query or {})
    if c['APP_SECRET']:params['appsecret_proof']=hmac.new(c['APP_SECRET'].encode(),c['TOKEN'].encode(),hashlib.sha256).hexdigest()
    url='https://graph.facebook.com/'+c['VERSION']+'/'+c['PHONE_ID']+'/'+edge+('?' + urlencode(params) if params else '')
    return request(url,method,payload,{'Authorization':'Bearer '+c['TOKEN']})


def permission(tenant,phone):
    result=remote(tenant,'call_permissions',query={'user_wa_id':phone})
    info=result.get('permission',{});actions=result.get('actions',[])
    if not isinstance(info,dict) or not isinstance(actions,list):raise ServiceError('Call permission could not be verified.')
    allowed=lambda name:any(isinstance(a,dict) and a.get('action_name')==name and a.get('can_perform_action') is True for a in actions)
    valid=info.get('status')=='permanent' or info.get('status')=='temporary' and type(info.get('expiration_time')) in (int,float) and info['expiration_time']>time.time()
    return {'status':str(info.get('status','unknown'))[:30],'expires':info.get('expiration_time'), 'can_call':bool(valid and allowed('start_call')),'can_request':allowed('send_call_permission_request')}


def action(store,ctx,operation,data):
    from whatsapp_calls import status,public,ice
    t=ctx['tenant_id'];owner=ctx['user']['id'];stamp=int(time.time())
    if ctx['role'] not in ('admin','agent'):raise ServiceError('Teammate access required.',403)
    if not status(t)['outbound_ready']:raise ServiceError('Outbound calling is disabled. Verify Meta eligibility and enable its server gate first.')
    with store.db() as db:contact=store._get(db,t,'contact',data.get('contact_id'))
    phone=contact['phone']
    if operation=='calls.permission':return dict(permission(t,phone),ice=ice(ctx))
    key=data.get('request_id','')
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9-]{16,80}',key):raise ServiceError('A unique request ID is required.')
    kind='callpermission' if operation=='calls.request-permission' else 'voicecall'
    offer=data.get('sdp','')
    text=data.get('text','May our team call you about your request?')
    if operation=='calls.start' and (not isinstance(offer,str) or not offer.startswith('v=0') or len(offer)>60000):raise ServiceError('Use a valid WebRTC offer.')
    if operation=='calls.request-permission':
        if settings(t)['LIVE'].lower()!='true':raise ServiceError('WhatsApp message sending is disabled.')
        if not isinstance(text,str) or not 1<=len(text)<=1024:raise ServiceError('Use a short call-permission message.')
        if not 0<=stamp-contact.get('last_inbound',0)<86400:raise ServiceError('A permission request requires an active 24-hour customer-service window.')
    digest=hashlib.sha256((offer if operation=='calls.start' else text).encode()).hexdigest()
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        old=next((c for c in store._list(db,t,kind) if c.get('request_id')==key),None)
        if old:
            if old.get('owner')!=owner or old.get('phone')!=phone or old.get('request_digest')!=digest:raise ServiceError('Request ID already belongs to another call.',409)
            return public(old)
        if operation=='calls.start' and any(c.get('owner')==owner and c.get('status') in ('submitting','dialing','ringing','accepting','connected','unknown','ending') for c in store._list(db,t,'voicecall')):raise ServiceError('Finish the current call or reconcile its outcome first.',409)
        attempt=store._put(db,t,kind,dict(request_id=key,request_digest=digest,owner=owner,phone=phone,contact_id=contact['id'],provider_id='',direction='outbound',status='submitting',created=stamp))
    try:
        p=permission(t,phone)
        if not p['can_call' if operation=='calls.start' else 'can_request']:raise RemoteError('The customer has not granted calling permission or the provider limit is reached.',True)
        if operation=='calls.start':
            result=remote(t,'calls','POST',{'messaging_product':'whatsapp','to':phone,'action':'connect','session':{'sdp_type':'offer','sdp':offer},'biz_opaque_callback_data':attempt['id']})
            identifier=result.get('calls',[{}])[0].get('id');outcome='dialing'
        else:
            result=remote(t,'messages','POST',{'messaging_product':'whatsapp','to':phone,'type':'interactive','interactive':{'type':'call_permission_request','body':{'text':text},'action':{'name':'call_permission_request'}}})
            identifier=result.get('messages',[{}])[0].get('id');outcome='sent'
        if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_./:+=-]{1,200}',identifier):raise RemoteError('Provider outcome is uncertain. Do not repeat this request.')
        error=''
    except RemoteError as e:identifier='';outcome='failed' if e.definitive else 'unknown';error=str(e)
    except Exception:identifier='';outcome='unknown';error='Call outcome could not be confirmed. Do not repeat this request.'
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,t,kind,attempt['id'])
        if current['status']=='submitting':current.update(status=outcome,error=error)
        if identifier:current['provider_id']=identifier
        current['updated']=int(time.time());store._put(db,t,kind,current,current['id'])
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(t,ctx['user']['name'],operation+':'+current['status'],stamp))
        return public(current)
