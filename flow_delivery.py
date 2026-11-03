"""Durable once-claimed WhatsApp text transport for live graph checkpoints."""
import json
import os
import time
from meta import status as meta_status,send_text,send_template,ProviderError
from whatsapp_media import send_media
from flow_resources import unchanged
from reply_tracking import accepted


def now():return int(time.time())
def ready(tenant):
    status=meta_status(tenant)
    return status['configured'] and status['live'] and os.environ.get('TW_META_'+tenant.upper()+'_FLOW_SEND','false').lower()=='true'


def enqueue(store,db,tenant,flow,contact,body,resources=None):
    session=contact['flow_session'];node=session['node_id'];resource=(resources or {}).get(node);payload=session.pop('delivery_payload',{})
    job=store._put(db,tenant,'flowsend',dict(flow_id=flow['id'],version=flow.get('version',0),contact_id=contact['id'],body=body,status='queued',created=now(),updated=now(),inbound_ordinal=contact.get('last_real_inbound_ordinal',0),message_id='',lease_until=0,node_id=node,resource=resource,payload=payload,recipient_phone=contact['phone'],recipient_name=contact['name']))
    contact['flow_session'].update(send_id=job['id'])


def matches(contact,job):return contact.get('flow_session',{}).get('send_id')==job['id']


def valid(store,db,tenant,flow,contact,job,stamp):
    return (flow and flow.get('enabled') and flow.get('delivery_mode')=='live' and flow.get('version',0)==job['version'] and
            matches(contact,job) and not contact.get('automation_hold') and contact.get('last_real_inbound_ordinal',0)==job['inbound_ordinal'] and
            contact['phone']==job.get('recipient_phone') and unchanged(store,db,tenant,flow,job) and
            (bool(contact.get('optin')) if (job.get('resource') or {}).get('kind')=='template' else 0<=stamp-contact.get('last_real_inbound',0)<86400) and ready(tenant) and
            db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(tenant,flow.get('owner',''))).fetchone())


def pause(store,db,tenant,contact,job,reason):
    if not matches(contact,job):return
    contact=dict(contact,status='pending',automation_hold=True,flow_last_event={'status':'blocked','flow_id':job['flow_id'],'reason':reason,'updated':now()});contact.pop('flow_session',None);contact.pop('outgoing_watch',None)
    store._put(db,tenant,'contact',contact,contact['id']);store._message(db,tenant,contact['id'],reason,'note','internal')


def process_once(store):
    stamp=now()
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        # In-flight rows must not starve unrelated queued contacts.
        rows=db.execute("SELECT id,tenant,data FROM entities WHERE kind='flowsend' AND (json_extract(data,'$.status')='queued' OR (json_extract(data,'$.status')='sending' AND json_extract(data,'$.lease_until')<?)) ORDER BY rowid LIMIT 1",(stamp,)).fetchall()
        if not rows:return False
        row=rows[0];tenant=row['tenant'];job=dict(json.loads(row['data']),id=row['id']);contact=store._get(db,tenant,'contact',job['contact_id']);flow=next((f for f in store._list(db,tenant,'flow') if f['id']==job['flow_id']),None)
        if job['status']=='sending':
            store._put(db,tenant,'flowsend',dict(job,status='unknown',updated=stamp),job['id']);db.execute("UPDATE messages SET status='unknown' WHERE tenant=? AND id=?",(tenant,job['message_id']))
            pause(store,db,tenant,contact,job,'Chatbot worker interrupted. Reconcile its unknown submission with Meta; automatic retry is disabled.');return True
        if not valid(store,db,tenant,flow,contact,job,stamp):
            store._put(db,tenant,'flowsend',dict(job,status='cancelled',updated=stamp),job['id']);pause(store,db,tenant,contact,job,'Chatbot sending cancelled because its conversation, flow, access or runtime changed.');return True
        message=store._message(db,tenant,contact['id'],job['body'],'out','sending');job=store._put(db,tenant,'flowsend',dict(job,status='sending',message_id=message['id'],lease_until=stamp+90,updated=stamp),job['id'])
    try:
        resource=job.get('resource') or {}
        if resource.get('kind')=='media':external=send_media(tenant,contact['phone'],resource['provider_id'],resource['media_kind'],job['payload'].get('caption',''),resource['filename'] if resource['media_kind']=='document' else '')
        elif resource.get('kind')=='template':external=send_template(tenant,contact['phone'],resource['template'],job['recipient_name'])
        else:external=send_text(tenant,contact['phone'],job['body'])
        if not isinstance(external,str) or not external.strip() or len(external)>512:raise ValueError('Provider response did not identify an accepted message.')
        outcome='accepted'
    except ProviderError as error:external=None;outcome='failed' if error.definitive else 'unknown'
    except Exception:external=None;outcome='unknown'
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'flowsend',job['id'])
        if current['status']!='sending':
            store._put(db,tenant,'flowsend',dict(current,late_outcome=outcome,external_id=external,updated=now()),job['id'])
            if external:db.execute('UPDATE messages SET external_id=? WHERE tenant=? AND id=?',(external,tenant,job['message_id']))
            return True
        db.execute('UPDATE messages SET status=?,external_id=? WHERE tenant=? AND id=?',(outcome,external,tenant,job['message_id']))
        store._put(db,tenant,'flowsend',dict(current,status=outcome,updated=now(),external_id=external),job['id'])
        contact=store._get(db,tenant,'contact',job['contact_id']);flow=next((f for f in store._list(db,tenant,'flow') if f['id']==job['flow_id']),None)
        if outcome=='accepted':
            accepted(store,db,tenant,job['message_id'],now());contact=store._get(db,tenant,'contact',contact['id'])
            if valid(store,db,tenant,flow,contact,job,now()):store._run_flow(db,tenant,contact,flow,'',True,delivered=True)
            else:pause(store,db,tenant,contact,job,'Chatbot submission accepted, but continuation cancelled after conversation or policy changed.')
        else:pause(store,db,tenant,contact,job,'Chatbot submission '+outcome+'. Review Meta before sending again; automatic retry is disabled.')
    return True


def history(db,tenant):
    return [dict(json.loads(row['data']),id=row['id']) for row in db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='flowsend' ORDER BY rowid DESC LIMIT 50",(tenant,))]
