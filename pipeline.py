"""Workspace-specific deal stages, preserving canonical open/won/lost identities."""
import json
import re
import time

DEFAULTS=[{'id':id,'label':label} for id,label in [('new','New'),('qualified','Qualified'),('proposal','Proposal'),('won','Won'),('lost','Lost')]]


def configuration(store,db,tenant):
    values=store._list(db,tenant,'pipelineconfig')
    return values[0] if values else {'stages':[dict(stage) for stage in DEFAULTS],'closure_days':0}


def state(store,db,tenant):
    result=configuration(store,db,tenant)
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='dealstageevent' ORDER BY rowid DESC LIMIT 100",(tenant,)).fetchall()
    return dict(result,events=[dict(json.loads(row['data']),id=row['id']) for row in rows])


def save(store,db,ctx,data):
    if ctx['role']!='admin':raise ValueError('Administrator access required.')
    stages=data.get('stages');days=data.get('closure_days',0)
    if not isinstance(stages,list) or not 3<=len(stages)<=20:raise ValueError('Configure three to twenty sales stages.')
    if any(not isinstance(stage,dict) or set(stage)!={'id','label'} or not isinstance(stage['id'],str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}',stage['id']) or not isinstance(stage['label'],str) or not stage['label'].strip() or len(stage['label'])>60 for stage in stages):raise ValueError('Use valid stage identifiers and names up to 60 characters.')
    ids=[stage['id'] for stage in stages]
    if len(set(ids))!=len(ids) or not {'new','won','lost'}<=set(ids):raise ValueError('Keep distinct New, Won and Lost stages.')
    if type(days) is not int or not 0<=days<=365:raise ValueError('Default closure days must be a whole number from 0 to 365.')
    if any(deal['stage'] not in ids for deal in store._list(db,ctx['tenant_id'],'deal')):raise ValueError('Move existing deals before removing a stage.')
    old=configuration(store,db,ctx['tenant_id'])
    return store._put(db,ctx['tenant_id'],'pipelineconfig',{'stages':[{'id':stage['id'],'label':stage['label'].strip()} for stage in stages],'closure_days':days,'updated':int(time.time())},old.get('id'))
