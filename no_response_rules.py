"""One local rule evaluation per accepted reply after a configured no-response wait."""
import json
from rule_actions import execute


def process_once(store,stamp):
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        rules=db.execute("SELECT id,tenant,data FROM entities WHERE kind='rule' AND json_extract(data,'$.event')='customer_no_response' AND json_extract(data,'$.enabled')=1 ORDER BY json_extract(data,'$.priority'),rowid").fetchall()
        for row in rules:
            rule=dict(json.loads(row['data']),id=row['id']);tenant=row['tenant'];delay=rule['wait_seconds']
            contact_row=db.execute("""SELECT c.id,c.data FROM entities c WHERE c.tenant=? AND c.kind='contact'
                AND COALESCE(json_extract(c.data,'$.automation_hold'),0)=0
                AND json_extract(c.data,'$.outgoing_watch.ordinal')>?
                AND json_extract(c.data,'$.outgoing_watch.accepted')<=?
                AND COALESCE(json_extract(c.data,'$.last_real_inbound_ordinal'),0)<=json_extract(c.data,'$.outgoing_watch.ordinal')
                AND NOT EXISTS (SELECT 1 FROM entities e WHERE e.tenant=c.tenant AND e.kind='rulenoresponse' AND json_extract(e.data,'$.rule_id')=? AND json_extract(e.data,'$.anchor_id')=json_extract(c.data,'$.outgoing_watch.message_id'))
                ORDER BY json_extract(c.data,'$.outgoing_watch.accepted'),c.id LIMIT 1""",(tenant,rule['after_message_ordinal'],stamp-delay,rule['id'])).fetchone()
            if not contact_row:continue
            contact=dict(json.loads(contact_row['data']),id=contact_row['id']);anchor=contact['outgoing_watch']
            evaluation=store._put(db,tenant,'rulenoresponse',dict(rule_id=rule['id'],contact_id=contact['id'],anchor_id=anchor['message_id'],due=anchor['accepted']+delay,processed=stamp,status='evaluating'))
            applied=execute(store,db,tenant,rule,contact,{'id':anchor['message_id'],'event_id':evaluation['id'],'event':'customer_no_response'})
            if applied:store._put(db,tenant,'rule',dict(rule,executions=rule.get('executions',0)+1),rule['id'])
            store._put(db,tenant,'rulenoresponse',dict(evaluation,status='applied' if applied else 'not_applied'),evaluation['id'])
            return True
    return False


def history(store,db,tenant):
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='rulenoresponse' ORDER BY rowid DESC LIMIT 100",(tenant,)).fetchall()
    return [dict(json.loads(row['data']),id=row['id']) for row in reversed(rows)]
