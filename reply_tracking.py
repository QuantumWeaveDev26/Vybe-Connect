"""Record accepted outbound anchors without interpreting drafts or delivery upgrades."""
import json
import business_hours


def accepted(store,db,tenant,message_id,stamp):
    message=db.execute("SELECT rowid AS ordinal,contact,status FROM messages WHERE tenant=? AND id=? AND direction='out'",(tenant,message_id)).fetchone()
    if not message or message['status'] not in ['accepted','sent','delivered','read']:return False
    row=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='contact' AND id=?",(tenant,message['contact'])).fetchone()
    if not row:return False
    contact=dict(json.loads(row['data']),id=row['id']);previous=contact.get('outgoing_watch',{})
    business_hours.accepted(store,db,tenant,contact['id'],message_id,stamp)
    if contact.get('automation_hold') or previous.get('ordinal',0)>=message['ordinal']:return False
    store._put(db,tenant,'contact',dict(contact,outgoing_watch={'message_id':message_id,'ordinal':message['ordinal'],'accepted':stamp}),contact['id'])
    return True
