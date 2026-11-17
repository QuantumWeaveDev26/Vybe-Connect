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
                if old and old.get('status') in ('ended','rejected'):continue
                value=dict(old or {},provider_id=identifier,status='ended' if kind=='terminate' else 'rejected',ended=int(time.time()))
                store._put(db,tenant,'voicecall',value,old.get('id') if old else None)
            elif kind=='connect' and old and old.get('direction')=='outbound':
                session=event.get('session') or {};answer=session.get('sdp','')
                if session.get('sdp_type')!='answer' or not isinstance(answer,str) or not answer.startswith('v=0') or not 1<=len(answer)<=60000:raise ServiceError('Invalid outbound call answer.')
                if old['status'] in ('submitting','dialing','unknown'):
                    old.update(provider_id=identifier,answer=answer,status='connected',connected_at=int(time.time()),updated=int(time.time()));store._put(db,tenant,'voicecall',old,old['id'])
            elif kind=='connect' and not old:
                session=event.get('session') or {};offer=session.get('sdp','');phone=event.get('from','')
                if session.get('sdp_type')!='offer' or not isinstance(offer,str) or not offer.startswith('v=0') or not 1<=len(offer)<=60000 or not isinstance(phone,str) or not re.fullmatch(r'\d{7,15}',phone):raise ServiceError('Invalid inbound call offer.')
                store._put(db,tenant,'voicecall',dict(provider_id=identifier,phone=phone,status='ringing',direction='inbound',offer=offer,created=int(time.time()),owner=''))


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
    from member_permissions import require
    with store.db() as db:
        member=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(ctx['tenant_id'],ctx['user']['id'])).fetchone()
        if not member:raise ServiceError('Workspace access changed.',403)
        ctx=dict(ctx,role=member['role'])
    if operation not in ('calls.end','calls.reject','calls.release','calls.session'):require(store,ctx,'calling')
    else:
        with store.db() as db:
            if not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(ctx['tenant_id'],ctx['user']['id'])).fetchone():raise ServiceError('Workspace access changed.',403)
    if operation=='calls.history':return history(store,ctx,data)
    if operation in ('calls.assign','calls.note'):return local_action(store,ctx,operation,data)
    if operation in ('calls.permission','calls.request-permission','calls.start'):
        from outbound_calls import action as outbound_action
        return outbound_action(store,ctx,operation,data)
    tenant=ctx['tenant_id'];user=ctx['user']['id'];stamp=int(time.time())
    if ctx['role'] not in ('admin','agent'):raise ServiceError('Teammate access required.',403)
    if not status(tenant)['ready']:raise ServiceError('Configure and explicitly enable WhatsApp calling first.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');call=store._get(db,tenant,'voicecall',data.get('id'))
        if operation not in ('calls.end','calls.reject','calls.release','calls.session'):require(store,ctx,'calling',db)
        if operation=='calls.session':
            if call.get('owner')!=user:raise ServiceError('Only the initiating teammate can read call negotiation.',403)
            return {'id':call['id'],'status':call['status'],'answer':call.get('answer',''),'ice':ice(ctx)}
        if operation=='calls.claim':
            if call['status']!='ringing' or stamp-call.get('created',0)>60:raise ServiceError('This inbound call is no longer answerable.',409)
            if call.get('owner') and call['owner']!=user and call.get('claim_until',0)>stamp:raise ServiceError('Another teammate is answering this call.',409)
            if any(c['id']!=call['id'] and c.get('owner')==user and (c.get('status') in ('submitting','dialing','accepting','connected','unknown','ending') or c.get('status')=='ringing' and c.get('claim_until',0)>stamp) for c in store._list(db,tenant,'voicecall')):raise ServiceError('Finish your current call first.',409)
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
            if outcome=='connected':current['connected_at']=int(time.time())
            if outcome in ('ended','rejected'):current['ended']=int(time.time())
            current.update(status=outcome,error=error,updated=int(time.time()));store._put(db,tenant,'voicecall',current,current['id'])
        return public(current)


def local_action(store,ctx,operation,data):
    """Route a ringing offer or save an internal note. Never contacts Meta."""
    from member_permissions import policy,require
    tenant=ctx['tenant_id'];user=ctx['user']['id'];stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        require(store,ctx,'calling',db)
        member=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(tenant,user)).fetchone()
        call=store._get(db,tenant,'voicecall',data.get('id'))
        if not member or member['role']!='admin' and call.get('owner')!=user:raise ServiceError('Only the call owner or an administrator can edit this call.',403)
        if operation=='calls.note':
            body=data.get('body')
            if not isinstance(body,str) or not 1<=len(body.strip())<=4000:raise ServiceError('Enter a call note of up to 4000 characters.')
            notes=list(call.get('notes',[]))
            if len(notes)>=100:raise ServiceError('Use up to 100 notes per call.')
            notes.append({'body':body.strip(),'author':user,'created':stamp});call['notes']=notes
        else:
            target=data.get('owner')
            if call.get('status')!='ringing' or not 0<=stamp-call.get('created',0)<=60:raise ServiceError('Only a current ringing call can be assigned.',409)
            if data.get('expected_owner')!=call.get('owner',''):raise ServiceError('Call ownership changed. Refresh first.',409)
            if not isinstance(target,str) or not policy(store,db,tenant,target)['calling']:raise ServiceError('Choose a current teammate with calling access.')
            if target==call.get('owner'):return public(call)
            if any(c['id']!=call['id'] and c.get('owner')==target and c.get('status') in ('submitting','dialing','accepting','connected','unknown','ending') for c in store._list(db,tenant,'voicecall')):raise ServiceError('That teammate already has a call.',409)
            history=list(call.get('assignments',[]))
            if len(history)>=100:raise ServiceError('Call assignment history is full.')
            history.append({'from':call.get('owner',''),'to':target,'actor':user,'created':stamp})
            call.update(owner=target,claim_until=stamp+60,assignments=history)
        call['updated']=stamp;store._put(db,tenant,'voicecall',call,call['id'])
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation+':'+call['id'],stamp))
        return public(call)


def history(store,ctx,data):
    import json
    from listing_limits import message_page_size
    from member_permissions import require
    limit=message_page_size(data.get('limit'));before=data.get('before')
    if before is not None and (type(before) is not int or not 1<=before<=9223372036854775807):raise ServiceError('Use the previous call-history cursor.')
    with store.db() as db:
        require(store,ctx,'calling',db)
        rows=db.execute("SELECT rowid,id,data FROM entities WHERE tenant=? AND kind='voicecall' AND rowid<? ORDER BY rowid DESC LIMIT ?",(ctx['tenant_id'],before if before is not None else 9223372036854775807,limit+1)).fetchall()
    values=[public(dict(json.loads(row['data']),id=row['id'])) for row in rows[:limit]]
    return {'calls':values,'next_before':rows[limit-1]['rowid'] if len(rows)>limit else None}


def recent_calls(store,db,tenant):
    import json
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='voicecall' ORDER BY rowid DESC LIMIT 100",(tenant,)).fetchall()
    active=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='voicecall' AND json_extract(data,'$.status') IN ('ringing','submitting','dialing','accepting','connected','unknown','ending') ORDER BY rowid DESC LIMIT 50",(tenant,)).fetchall()
    merged={r['id']:public(dict(json.loads(r['data']),id=r['id'])) for r in [*rows,*active]}
    return list(merged.values())
