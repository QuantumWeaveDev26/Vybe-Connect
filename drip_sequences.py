"""Durable approved-template drip runs over the existing outbound queue."""
import hashlib
import json
import re
import secrets
from crm import text
from meta import status as meta_status


class DripError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def action(store,ctx,action,data,stamp):
    if ctx['role']!='admin':raise DripError('Administrator access required.',403)
    tenant=ctx['tenant_id']
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if action=='sequence.save':
            if data.get('id'):store._get(db,tenant,'sequence',data['id'])
            steps=data.get('steps')
            if not isinstance(steps,list) or not 1<=len(steps)<=8:raise DripError('Use one to eight template steps.')
            normalized=[];total=0
            for index,step in enumerate(steps):
                if not isinstance(step,dict):raise DripError('Each step needs a template and wait duration.')
                wait=step.get('wait_seconds')
                if type(wait) is not int or wait<(0 if index==0 else 60):raise DripError('Use a nonnegative first wait and at least 60 seconds between later steps.')
                total+=wait
                if total>2592000:raise DripError('Total sequence duration cannot exceed 30 days.')
                template=store._get(db,tenant,'template',step.get('template_id'))
                normalized.append({'template_id':template['id'],'wait_seconds':wait})
            result=store._put(db,tenant,'sequence',{'name':text(data.get('name'),'Sequence name',150),'steps':normalized,'status':'draft','updated':stamp},data.get('id'))
        elif action=='sequence.launch':
            nonce=data.get('nonce');ids=data.get('contact_ids')
            if not isinstance(nonce,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,100}',nonce):raise DripError('A stable launch identifier is required.')
            if not isinstance(ids,list) or not 1<=len(ids)<=100 or any(not isinstance(id,str) for id in ids):raise DripError('Choose one to 100 opted-in contacts.')
            ids=sorted(set(ids));fingerprint=hashlib.sha256(json.dumps([data.get('id'),ids]).encode()).hexdigest()
            previous=next((r for r in store._list(db,tenant,'sequencerun') if r['nonce']==nonce),None)
            if previous:
                if previous['fingerprint']!=fingerprint:raise DripError('This launch identifier was used for another audience or sequence.',409)
                return previous
            sequence=store._get(db,tenant,'sequence',data.get('id'))
            if not isinstance(sequence['steps'],list):raise DripError('Edit this legacy sequence into template steps before launch.')
            connection=meta_status(tenant)
            if not connection['live'] or not connection.get('configured'):raise DripError('Live Meta sending and complete connection settings are required before launch.')
            contacts=[store._get(db,tenant,'contact',id) for id in ids]
            if any(not c['optin'] for c in contacts):raise DripError('Every recipient must have marketing consent.')
            templates=[store._get(db,tenant,'template',step['template_id']) for step in sequence['steps']]
            if any(t.get('status')!='APPROVED' or not t.get('meta_id') for t in templates):raise DripError('Every step requires a Meta-approved template.')
            result=store._put(db,tenant,'sequencerun',{'sequence_id':sequence['id'],'name':sequence['name'],'steps':sequence['steps'],'nonce':nonce,'fingerprint':fingerprint,'status':'active','owner':ctx['user']['id'],'created':stamp,'audience':len(contacts),'campaign_ids':[]})
            due=stamp
            for index,(step,template) in enumerate(zip(sequence['steps'],templates)):
                due+=step['wait_seconds']
                campaign=store._put(db,tenant,'campaign',{'name':sequence['name']+' · Step '+str(index+1),'template_id':template['id'],'status':'queued','audience':len(contacts),'created':stamp,'drip_run':result['id'],'drip_step':index,'mode':'live','simulated':0})
                result['campaign_ids'].append(campaign['id'])
                for contact in contacts:db.execute('INSERT INTO outbound VALUES(?,?,?,?,?,?,?,?,?,?)',(secrets.token_hex(8),tenant,campaign['id'],contact['id'],json.dumps(template),'queued',due,0,'',None))
            result=store._put(db,tenant,'sequencerun',result,result['id'])
        else:
            run=store._get(db,tenant,'sequencerun',data.get('id'));campaigns=run['campaign_ids'];marks=','.join('?' for _ in campaigns)
            if action=='sequence.pause':
                if run['status']!='active':raise DripError('Only active runs can be paused.')
                db.execute(f"UPDATE outbound SET status='paused' WHERE tenant=? AND campaign IN ({marks}) AND status='queued'",[tenant]+campaigns);status='paused'
            elif action=='sequence.resume':
                if run['status']!='paused':raise DripError('Only paused runs can be resumed.')
                db.execute(f"UPDATE outbound SET status='queued' WHERE tenant=? AND campaign IN ({marks}) AND status='paused'",[tenant]+campaigns);status='active'
            elif action=='sequence.cancel':
                db.execute(f"UPDATE outbound SET status='cancelled',error='Sequence cancelled before submission.' WHERE tenant=? AND campaign IN ({marks}) AND status IN ('queued','paused')",[tenant]+campaigns);status='cancelled'
            else:raise DripError('Unknown sequence action.',404)
            result=store._put(db,tenant,'sequencerun',dict(run,status=status,updated=stamp),run['id'])
            for campaign in campaigns:store._update_campaign_queue(db,{'tenant':tenant,'campaign':campaign})
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],action,stamp))
    return result


def eligible(store,db,job,stamp):
    campaign=store._get(db,job['tenant'],'campaign',job['campaign'])
    if not campaign.get('drip_run'):return True
    run=store._get(db,job['tenant'],'sequencerun',campaign['drip_run'])
    if run['status']!='active':return False
    index=campaign['drip_step']
    if not index:return True
    previous=db.execute('SELECT status FROM outbound WHERE tenant=? AND campaign=? AND contact=?',(job['tenant'],run['campaign_ids'][index-1],job['contact'])).fetchone()
    if previous and previous['status'] in ['accepted','sent','delivered','read']:return True
    if not previous or previous['status'] in ['failed','unknown','skipped','cancelled']:after_submit(store,db,job,'failed',stamp)
    return False


def after_submit(store,db,job,status,stamp):
    campaign=store._get(db,job['tenant'],'campaign',job['campaign'])
    if not campaign.get('drip_run'):return
    run=store._get(db,job['tenant'],'sequencerun',campaign['drip_run']);index=campaign['drip_step'];later=run['campaign_ids'][index+1:]
    if status in ['failed','unknown','skipped','cancelled']:
        # Include this row if it has not been submitted: eligibility may have
        # discovered a failed predecessor before claiming the current step.
        affected=run['campaign_ids'][index:];marks=','.join('?' for _ in affected)
        db.execute(f"UPDATE outbound SET status='cancelled',error='A preceding sequence step was not accepted; no automatic retry.' WHERE tenant=? AND contact=? AND campaign IN ({marks}) AND status IN ('queued','paused')",[job['tenant'],job['contact']]+affected)
        for id in affected:store._update_campaign_queue(db,{'tenant':job['tenant'],'campaign':id})
    elif status=='accepted' and later:
        db.execute('UPDATE outbound SET due=MAX(due,?) WHERE tenant=? AND contact=? AND campaign=? AND status IN (\'queued\',\'paused\')',(stamp+run['steps'][index+1]['wait_seconds'],job['tenant'],job['contact'],later[0]))


def run_state(store,db,tenant):
    result=[]
    for run in store._list(db,tenant,'sequencerun'):
        marks=','.join('?' for _ in run['campaign_ids'])
        counts={r['status']:r['n'] for r in db.execute(f'SELECT status,COUNT(*) AS n FROM outbound WHERE tenant=? AND campaign IN ({marks}) GROUP BY status',[tenant]+run['campaign_ids'])}
        result.append(dict(run,counts=counts,finished=not any(counts.get(s,0) for s in ['queued','sending','paused'])))
    return result
