"""Deterministic local contact/conversation events without recursive rule emission."""
import json
import re
import time
from rule_actions import RuleError,execute

EVENTS={'incoming_message','contact_created','contact_updated','attribute_added','attribute_changed','conversation_opened','conversation_resolved','customer_no_response'}


def validate_trigger(event,attribute):
    if not isinstance(event,str) or event not in EVENTS:raise RuleError('Choose a supported message/contact/conversation trigger.')
    if not isinstance(attribute,str) or attribute and not re.fullmatch(r'[A-Za-z0-9_ -]{1,60}',attribute):raise RuleError('Choose a bounded custom attribute name, or leave empty for any field.')
    if attribute and event not in ['attribute_added','attribute_changed']:raise RuleError('Attribute filters require an attribute event.')


def dispatch(store,db,tenant,contact,event,fields=None,message=None):
    if contact.get('automation_hold'):return contact
    fields=fields or []
    rules=[r for r in store._list(db,tenant,'rule') if r.get('event','incoming_message')==event and r['enabled'] and (not r.get('trigger_attribute') or r['trigger_attribute'] in fields)]
    if not rules:return contact
    rules.sort(key=lambda rule:rule.get('priority',100))
    record=store._put(db,tenant,'ruleevent',dict(event=event,contact_id=contact['id'],changed_fields=sorted(fields),source_message_id=message['id'] if message else '',created=int(time.time())))
    source=dict(id=message['id'] if message else '',event=event,event_id=record['id'])
    for rule in rules:
        if execute(store,db,tenant,rule,contact,source):
            store._put(db,tenant,'rule',dict(rule,executions=rule.get('executions',0)+1),rule['id']);break
    return store._get(db,tenant,'contact',contact['id'])


def contact_change(store,db,tenant,before,after):
    if not before:return dispatch(store,db,tenant,after,'contact_created')
    fields=['name','phone','tags','optin','attributes']
    if all(json.dumps(before.get(key),sort_keys=True)==json.dumps(after.get(key),sort_keys=True) for key in fields):return after
    result=dispatch(store,db,tenant,after,'contact_updated')
    old=before.get('attributes',{});new=after.get('attributes',{})
    added=[key for key in new if key not in old]
    changed=[key for key in old if key not in new or json.dumps(old[key],sort_keys=True)!=json.dumps(new[key],sort_keys=True)]
    if added:result=dispatch(store,db,tenant,result,'attribute_added',added)
    if changed:result=dispatch(store,db,tenant,result,'attribute_changed',changed)
    return result


def status_change(store,db,tenant,before,after,message=None):
    if before.get('status')==after.get('status'):return after
    event={'open':'conversation_opened','solved':'conversation_resolved'}.get(after.get('status'))
    return dispatch(store,db,tenant,after,event,message=message) if event else after


def history(db,tenant):
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='ruleexecution' ORDER BY rowid DESC LIMIT 100",(tenant,)).fetchall()
    return [dict(json.loads(row['data']),id=row['id']) for row in reversed(rows)]
