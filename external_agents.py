"""Tenant-scoped external agent events, pinned HTTPS delivery and signed draft callbacks."""
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
import re
import secrets
import socket
import ssl
import time
from urllib.parse import urlsplit
from crm import text

EVENTS={'message.received','message.status'}


class ExternalError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def endpoint(value):
    try:url=urlsplit(value)
    except (TypeError,ValueError):raise ValueError('Use a public HTTPS webhook URL.') from None
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.port not in [None,443] or len(value)>1000:raise ValueError('Use HTTPS on port 443 without credentials, query parameters or fragments.')
    if not re.fullmatch(r'[a-zA-Z0-9.-]{1,253}',url.hostname) or any(ord(c)<33 or ord(c)>126 for c in value):raise ValueError('Use an ASCII public hostname and encoded URL path.')
    try:
        if not ipaddress.ip_address(url.hostname).is_global:raise ValueError('Private or local webhook destinations are not allowed.')
    except ValueError as error:
        if re.fullmatch(r'[0-9.]+',url.hostname):raise ValueError('Private or invalid IP webhook destinations are not allowed.') from None
    return url


def configuration(tenant,agent):
    prefix='TW_WEBHOOK_'+tenant.upper()+'_';secret_name=prefix+agent['id'].upper()+'_SECRET'
    url=endpoint(agent['url']);origin='https://'+url.hostname.lower()
    allow={value.strip().rstrip('/').lower() for value in os.environ.get(prefix+'ALLOWED_ORIGINS','').split(',') if value.strip()}
    enabled=os.environ.get(prefix+'ENABLED','false').lower()=='true';key=os.environ.get(secret_name,'')
    return {'enabled':enabled,'configured':bool(key and origin in allow),'allowlisted':origin in allow,'secret_present':bool(key),'prefix':prefix,'secret_name':secret_name}


def secret(tenant,agent_id):return os.environ.get('TW_WEBHOOK_'+tenant.upper()+'_'+agent_id.upper()+'_SECRET','')


def public_agent(tenant,agent):return dict(agent,connection=configuration(tenant,agent))
def public_event(event):return {k:event[k] for k in ['id','connector_id','type','status','created','updated','attempts','http_status','error'] if k in event}


def recent_events(db,tenant):
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='webhookevent' ORDER BY rowid DESC LIMIT 100",(tenant,)).fetchall()
    return [public_event(dict(json.loads(row['data']),id=row['id'])) for row in reversed(rows)]


def action(store,ctx,operation,data):
    if ctx['role']!='admin':raise ExternalError('Administrator access required.',403)
    tenant=ctx['tenant_id'];stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if operation=='external-agent.save':
            old=store._get(db,tenant,'externalagent',data['id']) if data.get('id') else {}
            if not old and len(store._list(db,tenant,'externalagent'))>=20:raise ExternalError('Use up to 20 external agents per workspace.')
            url=text(data.get('url'),'Webhook URL',1000);endpoint(url);events=data.get('events')
            if not isinstance(events,list) or not events or any(not isinstance(e,str) or e not in EVENTS for e in events):raise ExternalError('Select supported message events.')
            if not isinstance(data.get('enabled',False),bool):raise ExternalError('Enabled must be true or false.')
            result=store._put(db,tenant,'externalagent',{'name':text(data.get('name'),'Agent name',100),'url':url,'events':sorted(set(events)),'enabled':data.get('enabled',False),'created':old.get('created',stamp),'updated':stamp},old.get('id'))
            # A URL change must not redirect already queued customer events.
            if old and old['url']!=url:
                rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='webhookevent' AND json_extract(data,'$.connector_id')=? AND json_extract(data,'$.status')='queued'",(tenant,old['id'])).fetchall()
                for row in rows:
                    event=dict(json.loads(row['data']),id=row['id']);store._put(db,tenant,'webhookevent',dict(event,status='cancelled',updated=stamp,error='Connection URL changed before dispatch.'),event['id'])
            result=public_agent(tenant,result)
        elif operation=='external-agent.retry':
            event=store._get(db,tenant,'webhookevent',data.get('id'));agent=store._get(db,tenant,'externalagent',event['connector_id'])
            if event['status'] not in ['failed','unknown']:raise ExternalError('Only failed or uncertain deliveries can be explicitly retried.')
            if not agent['enabled'] or not configuration(tenant,agent)['configured']:raise ExternalError('Enable and configure this connection before retrying.')
            if event['url']!=agent['url']:raise ExternalError('The endpoint changed. Historical customer data cannot be redirected by retrying.',409)
            result=store._put(db,tenant,'webhookevent',dict(event,status='queued',updated=stamp,error=''),event['id']);result=public_event(result)
        else:raise ExternalError('Unknown external agent action.',404)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,stamp))
    return result


def enqueue(store,db,tenant,event_type,resource_id,data):
    if event_type not in EVENTS:return
    stamp=int(time.time())
    pending=db.execute("SELECT COUNT(*) FROM entities WHERE tenant=? AND kind='webhookevent' AND json_extract(data,'$.status') IN ('queued','sending')",(tenant,)).fetchone()[0]
    if pending>=1000:
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'System','webhook.outbox.full',stamp));return
    for agent in store._list(db,tenant,'externalagent'):
        config=configuration(tenant,agent)
        if not agent['enabled'] or event_type not in agent['events'] or not config['enabled'] or not config['configured']:continue
        if db.execute("SELECT 1 FROM entities WHERE tenant=? AND kind='webhookevent' AND json_extract(data,'$.connector_id')=? AND json_extract(data,'$.resource_id')=? AND json_extract(data,'$.type')=? LIMIT 1",(tenant,agent['id'],resource_id,event_type)).fetchone():continue
        id=secrets.token_hex(8);payload={'id':id,'version':1,'type':event_type,'workspace_id':tenant,'connector_id':agent['id'],'created':stamp,'data':data}
        event={'connector_id':agent['id'],'type':event_type,'resource_id':resource_id,'payload':payload,'url':agent['url'],'status':'queued','created':stamp,'updated':stamp,'attempts':0,'claimed':0,'error':''}
        db.execute('INSERT INTO entities VALUES(?,?,?,?)',(id,tenant,'webhookevent',json.dumps(event)))


class PinnedConnection(http.client.HTTPSConnection):
    def __init__(self,hostname,address):super().__init__(hostname,443,timeout=8,context=ssl.create_default_context());self.address=address
    def connect(self):
        raw=socket.create_connection((self.address,443),self.timeout)
        try:self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except BaseException:raw.close();raise


def send_webhook(value,raw,headers):
    url=endpoint(value);addresses=socket.getaddrinfo(url.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Webhook DNS must resolve only to public IP addresses.')
    connection=PinnedConnection(url.hostname,addresses[0][4][0])
    try:
        connection.request('POST',url.path or '/',body=raw,headers={'Content-Type':'application/json','User-Agent':'TeamWave-Webhooks/1',**headers})
        response=connection.getresponse();response.read(4096);return response.status
    finally:connection.close()


def process_once(store):
    stamp=int(time.time());chosen=None
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');records=db.execute("SELECT id,tenant,data FROM entities WHERE kind='webhookevent' AND json_extract(data,'$.status') IN ('queued','sending') ORDER BY rowid").fetchall()
        for row in records:
            event=dict(json.loads(row['data']),id=row['id']);tenant=row['tenant']
            if event['status']=='sending' and event.get('claimed',0)<stamp-60:store._put(db,tenant,'webhookevent',dict(event,status='unknown',updated=stamp,error='Worker interrupted after dispatch began. No automatic retry.'),event['id']);continue
            if event['status']!='queued':continue
            agent=store._get(db,tenant,'externalagent',event['connector_id']);config=configuration(tenant,agent)
            if not agent['enabled'] or event['url']!=agent['url'] or event['type'] not in agent['events']:
                store._put(db,tenant,'webhookevent',dict(event,status='cancelled',updated=stamp,error='Connection disabled or changed before dispatch.'),event['id']);continue
            if not config['enabled'] or not config['configured']:continue
            event=store._put(db,tenant,'webhookevent',dict(event,status='sending',claimed=stamp,updated=stamp,attempts=event['attempts']+1),event['id']);chosen=tenant,event;break
    if not chosen:return False
    tenant,event=chosen;raw=json.dumps(event['payload'],ensure_ascii=False,separators=(',',':')).encode();timestamp=str(stamp)
    signature='sha256='+hmac.new(secret(tenant,event['connector_id']).encode(),timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    try:
        code=send_webhook(event['url'],raw,{'X-TeamWave-Event-ID':event['id'],'X-TeamWave-Timestamp':timestamp,'X-TeamWave-Signature':signature})
        status='delivered' if 200<=code<300 else 'failed';error='' if status=='delivered' else 'Receiver returned HTTP '+str(code)+'. Inspect the receiver before an explicit retry.'
    except ValueError:code=None;status='failed';error='Webhook destination validation failed. No redirect or private-network delivery is permitted.'
    except Exception:code=None;status='unknown';error='Delivery outcome is uncertain. Inspect the receiver before an explicit retry.'
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'webhookevent',event['id'])
        if current['status']=='sending' and current['attempts']==event['attempts']:store._put(db,tenant,'webhookevent',dict(current,status=status,http_status=code,error=error,updated=int(time.time())),event['id'])
    return True


def callback(store,tenant,agent_id,raw,headers):
    if not isinstance(raw,bytes) or not 0<len(raw)<=65536:raise ExternalError('Invalid callback body.',413)
    normalized={str(k).lower():v for k,v in headers.items()};timestamp=normalized.get('x-teamwave-timestamp','');signature=normalized.get('x-teamwave-signature','');key=secret(tenant,agent_id)
    if not key or not isinstance(timestamp,str) or not re.fullmatch(r'[0-9]{1,12}',timestamp) or abs(int(time.time())-int(timestamp))>300:raise ExternalError('Invalid or expired callback signature.',403)
    expected='sha256='+hmac.new(key.encode(),timestamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    if not isinstance(signature,str) or not re.fullmatch(r'sha256=[0-9a-f]{64}',signature) or not hmac.compare_digest(expected,signature):raise ExternalError('Invalid callback signature.',403)
    try:data=json.loads(raw)
    except (ValueError,TypeError):raise ExternalError('Invalid callback JSON.') from None
    if not isinstance(data,dict):raise ExternalError('Callback must be a JSON object.')
    body=text(data.get('body'),'Reply draft',4096);reply_id=text(data.get('reply_id'),'Reply identifier',100);digest=hashlib.sha256(raw).hexdigest();stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');agent=store._get(db,tenant,'externalagent',agent_id);config=configuration(tenant,agent)
        if not agent['enabled'] or not config['enabled'] or not config['configured']:raise ExternalError('This agent connection is disabled.',403)
        event=store._get(db,tenant,'webhookevent',data.get('event_id'))
        if event['connector_id']!=agent_id or event['type']!='message.received' or event['url']!=agent['url'] or event['status']=='cancelled' or 'message.received' not in agent['events']:raise ExternalError('The callback event is outside this agent scope.',403)
        previous=next((r for r in store._list(db,tenant,'externalreply') if r['connector_id']==agent_id and r['reply_id']==reply_id),None)
        if previous:
            if previous['digest']!=digest:raise ExternalError('Reply identifier was reused with different content.',409)
            return {'message_id':previous['message_id'],'status':'draft','duplicate':True}
        contact=store._get(db,tenant,'contact',event['payload']['data']['contact_id'])
        if contact.get('automation_hold'):raise ExternalError('This conversation is under human handling.',409)
        message=store._message(db,tenant,contact['id'],body,'out','draft')
        store._put(db,tenant,'externalreply',{'connector_id':agent_id,'reply_id':reply_id,'event_id':event['id'],'digest':digest,'message_id':message['id'],'created':stamp})
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'External agent','external-agent.reply-draft',stamp))
    return {'message_id':message['id'],'status':'draft','duplicate':False}
