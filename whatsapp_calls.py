"""Signed inbound WhatsApp voice calls with one answering teammate and WebRTC SDP."""
import base64
import hashlib
import hmac
import os
import re
import time
from meta import settings,ProviderError
from provider_transport import request,RemoteError
from service_jobs import ServiceError


def status(tenant):
    c=settings(tenant);prefix='TW_CALLING_'+tenant.upper()+'_'
    configured=bool(c['TOKEN'] and re.fullmatch(r'\d+',c['PHONE_ID']) and re.fullmatch(r'v\d+\.\d+',c['VERSION']))
    return {'configured':configured,'enabled':os.environ.get(prefix+'ENABLED','false').lower()=='true',
            'ready':configured and os.environ.get(prefix+'ENABLED','false').lower()=='true','prefix':prefix,
            'direction':'both','outbound_ready':configured and os.environ.get(prefix+'ENABLED','false').lower()=='true' and os.environ.get(prefix+'OUTBOUND_ENABLED','false').lower()=='true','live_verified':False}


def public(call):return {k:v for k,v in call.items() if k not in ('offer','answer','answer_digest','request_digest')}


def ingest(store,tenant,events):
    if not isinstance(events,list) or len(events)>100:raise ServiceError('Invalid call event batch.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        for event in events:
            if not isinstance(event,dict):raise ServiceError('Invalid call event.')
            identifier=event.get('id','');kind=event.get('event')
            if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_./:+=-]{1,200}',identifier):raise ServiceError('Invalid call ID.')
            old=next((c for c in store._list(db,tenant,'voicecall') if c['provider_id']==identifier or c.get('direction')=='outbound' and c['id']==event.get('biz_opaque_callback_data')),None)
            if old and old.get('direction')=='outbound' and event.get('to') not in (None,old['phone']):raise ServiceError('Call recipient does not match.')
            if kind in ('terminate','reject'):
                value=dict(old or {},provider_id=identifier,status='ended' if kind=='terminate' else 'rejected',ended=int(time.time()))
                store._put(db,tenant,'voicecall',value,old.get('id') if old else None)
            elif kind=='connect' and old and old.get('direction')=='outbound':
                session=event.get('session') or {};answer=session.get('sdp','')
                if session.get('sdp_type')!='answer' or not isinstance(answer,str) or not answer.startswith('v=0') or not 1<=len(answer)<=60000:raise ServiceError('Invalid outbound call answer.')
                if old['status'] in ('submitting','dialing','unknown'):
                    old.update(provider_id=identifier,answer=answer,status='connected',updated=int(time.time()));store._put(db,tenant,'voicecall',old,old['id'])
            elif kind=='connect' and not old:
                session=event.get('session') or {};offer=session.get('sdp','');phone=event.get('from','')
                if session.get('sdp_type')!='offer' or not isinstance(offer,str) or not offer.startswith('v=0') or not 1<=len(offer)<=60000 or not isinstance(phone,str) or not re.fullmatch(r'\d{7,15}',phone):raise ServiceError('Invalid inbound call offer.')
                store._put(db,tenant,'voicecall',dict(provider_id=identifier,phone=phone,status='ringing',offer=offer,created=int(time.time()),owner=''))


def ice(ctx):
    # Coturn REST credentials expire shortly; the shared TURN secret never leaves the server.
    from urllib.parse import urlsplit
    prefix='TW_CALLING_'+ctx['tenant_id'].upper()+'_';servers=[]
    urls=[u.strip() for u in os.environ.get(prefix+'TURN_URLS','').split(',') if u.strip()]
    if urls:
        if any(not re.fullmatch(r'turns?:[A-Za-z0-9.-]+(?::\d{1,5})?(?:\?transport=(?:udp|tcp))?',u) for u in urls):raise ServiceError('Invalid TURN configuration.')
        secret=os.environ.get(prefix+'TURN_SECRET','')
        if not secret:raise ServiceError('Configure the private TURN shared secret.')
        user=str(int(time.time())+300)+':'+ctx['tenant_id']+':'+ctx['user']['id']
        credential=base64.b64encode(hmac.new(secret.encode(),user.encode(),hashlib.sha1).digest()).decode()
        servers.append({'urls':urls,'username':user,'credential':credential})
    return {'iceServers':servers}


def action(store,ctx,operation,data):
    if operation in ('calls.permission','calls.request-permission','calls.start'):
        from outbound_calls import action as outbound_action
        return outbound_action(store,ctx,operation,data)
    tenant=ctx['tenant_id'];user=ctx['user']['id'];stamp=int(time.time())
    if ctx['role'] not in ('admin','agent'):raise ServiceError('Teammate access required.',403)
    if not status(tenant)['ready']:raise ServiceError('Configure and explicitly enable WhatsApp calling first.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');call=store._get(db,tenant,'voicecall',data.get('id'))
        if operation=='calls.session':
            if call.get('owner')!=user:raise ServiceError('Only the initiating teammate can read call negotiation.',403)
            return {'id':call['id'],'status':call['status'],'answer':call.get('answer',''),'ice':ice(ctx)}
        if operation=='calls.claim':
            if call['status']!='ringing' or stamp-call.get('created',0)>60:raise ServiceError('This inbound call is no longer answerable.',409)
            if call.get('owner') and call['owner']!=user and call.get('claim_until',0)>stamp:raise ServiceError('Another teammate is answering this call.',409)
            call.update(owner=user,claim_until=stamp+60);store._put(db,tenant,'voicecall',call,call['id'])
            return {'id':call['id'],'offer':call['offer'],'ice':ice(ctx)}
        if operation=='calls.release':
            if call.get('owner')==user and call['status']=='ringing':
                call.update(owner='',claim_until=0);store._put(db,tenant,'voicecall',call,call['id'])
            return public(call)
        if call.get('owner')!=user and ctx['role']!='admin':raise ServiceError('Only the answering teammate can control this call.',403)
        if operation=='calls.accept':
            answer=data.get('sdp')
            if call.get('owner')!=user or call['status']!='ringing' or call.get('claim_until',0)<stamp or stamp-call.get('created',0)>60:raise ServiceError('Call claim expired or another action already started.',409)
            if not isinstance(answer,str) or not answer.startswith('v=0') or not 1<=len(answer)<=60000:raise ServiceError('Use a valid WebRTC answer.')
            call.update(status='accepting',answer_digest=hashlib.sha256(answer.encode()).hexdigest())
            payload={'messaging_product':'whatsapp','call_id':call['provider_id'],'action':'accept','session':{'sdp_type':'answer','sdp':answer}}
        elif operation in ('calls.reject','calls.end'):
            if call['status'] in ('ended','rejected'):return public(call)
            if call['status']=='ending':return public(call)
            call['status']='ending'
            payload={'messaging_product':'whatsapp','call_id':call['provider_id'],'action':'reject' if operation=='calls.reject' else 'terminate'}
        else:raise ServiceError('Unknown call action.',404)
        store._put(db,tenant,'voicecall',call,call['id'])
    try:
        c=settings(tenant)
        try:result=request('https://graph.facebook.com/'+c['VERSION']+'/'+c['PHONE_ID']+'/calls','POST',payload,{'Authorization':'Bearer '+c['TOKEN']})
        except RemoteError as failure:raise ProviderError(str(failure),failure.definitive) from None
        if result.get('success') is not True:raise ProviderError('Call action result is uncertain.')
        outcome='connected' if operation=='calls.accept' else 'rejected' if operation=='calls.reject' else 'ended';error=''
    except ProviderError as failure:
        outcome='failed' if failure.definitive else 'unknown';error=str(failure)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'voicecall',call['id'])
        if current['status'] in ('accepting','ending'):
            current.update(status=outcome,error=error,updated=int(time.time()));store._put(db,tenant,'voicecall',current,current['id'])
        return public(current)
