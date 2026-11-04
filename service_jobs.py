"""Durable one-shot external operations. Interrupted/uncertain writes are never retried."""
import hashlib
import json
import secrets
import time
from provider_transport import RemoteError


class ServiceError(Exception):
    def __init__(self,message,code=400): super().__init__(message); self.code=code


def public(job):
    return {key: value for key,value in job.items() if key not in ('payload','fingerprint')}


def release_failed(store,ctx,identifier):
    if ctx['role']!='admin':raise ServiceError('Administrator access required.',403)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');job=store._get(db,ctx['tenant_id'],'servicejob',identifier)
        if job['status']!='failed':raise ServiceError('Only a definitively rejected request can be released. Reconcile uncertain outcomes.',409)
        job['original_reference']=job.get('original_reference',job['reference']);job['reference']='failed-'+job['id']
        store._put(db,ctx['tenant_id'],'servicejob',job,job['id'])
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(ctx['tenant_id'],ctx['user']['name'],'service.release-failed',int(time.time())))
    return {'released':True,'automatic_retry':False}


def execute(store,ctx,kind,reference,payload,send,project):
    if ctx['role']!='admin': raise ServiceError('Administrator access required.',403)
    tenant=ctx['tenant_id'];stamp=int(time.time())
    fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        old=next((j for j in store._list(db,tenant,'servicejob') if j['kind']==kind and j['reference']==reference),None)
        if old:
            if old['fingerprint']!=fingerprint: raise ServiceError('An operation already exists with different details. Review its outcome before creating another.',409)
            return public(dict(old,status='unknown' if old['status']=='submitting' and stamp-old['created']>120 else old['status']))
        job=store._put(db,tenant,'servicejob',dict(kind=kind,reference=reference,payload=payload,fingerprint=fingerprint,
            status='submitting',created=stamp,updated=stamp,actor=ctx['user']['id'],result={},error=''))
    try:
        response=send(job['id'])
        result=project(response,job['id'])
        status='created';error=''
    except RemoteError as failure:
        result={};status='failed' if failure.definitive else 'unknown';error=str(failure)
    except Exception:
        result={};status='unknown';error='The result could not be verified. Reconcile with the provider before taking another action.'
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'servicejob',job['id'])
        # A webhook may have arrived before the HTTP response.
        if current['status']=='submitting':
            current.update(status=status,result=result,error=error,updated=int(time.time()))
            store._put(db,tenant,'servicejob',current,current['id'])
        elif result:
            merged=dict(current.get('result',{}))
            for key in ('provider_id','url'):
                if key in result and key not in merged:merged[key]=result[key]
            current['result']=merged;store._put(db,tenant,'servicejob',current,current['id'])
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],kind+':'+status,int(time.time())))
        return public(current)
