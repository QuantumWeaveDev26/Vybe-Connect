"""Advance one due chatbot wait atomically; produces local drafts only."""
import json


def cancel_sessions(store,db,tenant,flow,stamp):
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='contact' AND json_extract(data,'$.flow_session.flow_id')=?",(tenant,flow)).fetchall()
    for row in rows:
        contact=dict(json.loads(row['data']),id=row['id']);contact.pop('flow_session',None)
        store._put(db,tenant,'contact',dict(contact,flow_last_event={'status':'cancelled','reason':'Flow settings changed','updated':stamp}),row['id'])


def process_once(store,stamp):
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT id,tenant,data FROM entities WHERE kind='contact' AND json_extract(data,'$.flow_session.mode')='wait' AND json_extract(data,'$.flow_session.due')<=? ORDER BY json_extract(data,'$.flow_session.due'),id LIMIT 1",(stamp,)).fetchone()
        if not row:return False
        tenant=row['tenant'];contact=dict(json.loads(row['data']),id=row['id']);session=contact['flow_session']
        flow=next((f for f in store._list(db,tenant,'flow') if f['id']==session['flow_id']),None)
        if contact.get('automation_hold') or not flow or not flow['enabled'] or session.get('version',0)!=flow.get('version',0):
            contact.pop('flow_session',None);store._put(db,tenant,'contact',dict(contact,flow_last_event={'status':'cancelled','reason':'Flow access or conversation control changed','updated':stamp}),contact['id'])
            outcome='cancelled'
        else:
            outcome='continued' if store._run_flow(db,tenant,contact,flow,'',True,timer=True) else 'blocked'
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'Chatbot timer','flow.wait.'+outcome,stamp))
    return True
