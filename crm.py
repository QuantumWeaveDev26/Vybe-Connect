"""Workspace CRM records. Deal values are estimates, never payment receipts."""
import time
from datetime import datetime
from pipeline import configuration as pipeline_configuration

STAGES=('new','qualified','proposal','won','lost')
CURRENCIES=('INR','USD','EUR','GBP','AED','SGD','AUD','CAD')


def text(value,label,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise ValueError(f'{label} is required (maximum {limit} characters).')
    return value.strip()


def due_timestamp(value):
    if value in ['',None,0]:return 0
    if not isinstance(value,str):raise ValueError('Due time requires an ISO date with timezone.')
    try:
        date=datetime.fromisoformat(value)
        if date.tzinfo is None or not 2000<=date.year<=2100:raise ValueError()
        return int(date.timestamp())
    except (ValueError,OverflowError):raise ValueError('Due time requires a valid ISO date with timezone (2000–2100).') from None


def member(db,tenant,value):
    if not isinstance(value,str) or value and not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,value)).fetchone():
        raise ValueError('Choose a member of this workspace.')
    return value


def crm_action(store,db,ctx,action,data):
    tenant=ctx['tenant_id']; stamp=int(time.time());kind=action.split('.')[0]
    old=store._get(db,tenant,kind,data['id']) if data.get('id') else {}
    if action=='task.complete':
        if not old:raise ValueError('Choose a task.')
        if not isinstance(data.get('completed'),bool):raise ValueError('Completed must be true or false.')
        return store._put(db,tenant,kind,dict(old,status='done' if data['completed'] else 'open',completed_at=stamp if data['completed'] else 0,updated=stamp),old['id'])
    contact_id=data.get('contact_id',old.get('contact_id',''))
    if contact_id:store._get(db,tenant,'contact',contact_id)
    owner=member(db,tenant,data.get('owner',old.get('owner',ctx['user']['id'])))
    title=text(data.get('title',old.get('title')),'Title',150)
    common=dict(old,title=title,contact_id=contact_id,owner=owner,created=old.get('created',stamp),updated=stamp)
    if kind=='deal':
        if not contact_id:raise ValueError('Choose a contact for this deal.')
        if old and contact_id!=old['contact_id'] and any(task.get('deal_id')==old['id'] for task in store._list(db,tenant,'task')):
            raise ValueError('A deal with linked tasks cannot be moved to another contact. Unlink its tasks first or create a separate deal.')
        amount=data.get('amount_minor',old.get('amount_minor',0))
        if type(amount) is not int or not 0<=amount<=9_000_000_000_000:raise ValueError('Amount must be a non-negative integer in minor currency units, up to 9,000,000,000,000.')
        stage=data.get('stage',old.get('stage','new'));currency=data.get('currency',old.get('currency','INR'))
        pipeline=pipeline_configuration(store,db,tenant)
        if not isinstance(stage,str) or stage not in {s['id'] for s in pipeline['stages']}:raise ValueError('Choose a valid sales stage.')
        if currency not in CURRENCIES:raise ValueError('Choose a supported currency.')
        closure=due_timestamp(data['closure_due']) if 'closure_due' in data else old.get('closure_due',stamp+pipeline['closure_days']*86400 if pipeline['closure_days'] else 0)
        result=dict(common,stage=stage,currency=currency,amount_minor=amount,closure_due=closure,stage_changed_at=old.get('stage_changed_at',stamp) if old.get('stage')==stage else stamp,closed_at=(old.get('closed_at',stamp) if old.get('stage')==stage else stamp) if stage in ['won','lost'] else 0)
    else:
        deal_id=data.get('deal_id',old.get('deal_id',''))
        if deal_id:
            deal=store._get(db,tenant,'deal',deal_id)
            if contact_id and contact_id!=deal['contact_id']:raise ValueError('Task contact must match its deal contact.')
            common['contact_id']=deal['contact_id']
        due=due_timestamp(data['due']) if 'due' in data else old.get('due',0)
        result=dict(common,deal_id=deal_id,due=due,status=old.get('status','open'),completed_at=old.get('completed_at',0))
    saved=store._put(db,tenant,kind,result,data.get('id'))
    if kind=='deal' and old.get('stage')!=result['stage']:store._put(db,tenant,'dealstageevent',dict(deal_id=saved['id'],from_stage=old.get('stage',''),to_stage=result['stage'],actor=ctx['user']['id'],created=stamp))
    return saved
