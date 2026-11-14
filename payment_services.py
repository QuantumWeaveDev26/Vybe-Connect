"""Merchant payment links and platform subscriptions use separate Razorpay accounts."""
import hashlib
import hmac
import json
import re
import time
from urllib.parse import urlsplit
from business_providers import config,status,plans,razorpay
from service_jobs import ServiceError,execute,public


def checkout_url(value):
    url=urlsplit(value if isinstance(value,str) else '')
    if url.scheme!='https' or url.hostname not in ('rzp.io','rzp.is','razorpay.com','pages.razorpay.com','rzp.co') or url.username or url.password:
        raise ValueError('Unverified Razorpay checkout URL.')
    return value


def payment_project(response,job_id,order):
    if not re.fullmatch(r'plink_[A-Za-z0-9]+',str(response.get('id',''))) or response.get('reference_id')!=job_id or response.get('amount')!=order['total_minor'] or response.get('currency')!=order['currency']:
        raise ValueError('Payment link identity/amount mismatch.')
    return {'provider_id':response['id'],'url':checkout_url(response.get('short_url')),'provider_status':response['status'],
            'amount_minor':order['total_minor'],'currency':order['currency']}


def action(store,ctx,operation,data):
    tenant=ctx['tenant_id']
    if ctx['role']!='admin':raise ServiceError('Administrator access required.',403)
    if operation=='payments.create-link':
        if not status(tenant,'payments')['ready']:raise ServiceError('Configure and enable Razorpay payments first.')
        with store.db() as db:
            order=store._get(db,tenant,'salesorder',data.get('order_id'))
            if order['status'] not in ('confirmed','fulfilled') or order['total_minor']<=0:raise ServiceError('Choose a confirmed order with a positive total.')
        payload={'amount':order['total_minor'],'currency':order['currency'],'accept_partial':False,
                 'description':'Order '+order['id'],'notify':{'sms':False,'email':False},'reminder_enable':False,
                 'notes':{'workspace_id':tenant,'order_id':order['id']}}
        return execute(store,ctx,'payments.link',order['id'],payload,
            lambda job:razorpay(tenant,'payments','POST','payment_links',dict(payload,reference_id=job)),
            lambda result,job:payment_project(result,job,order))
    if operation=='billing.subscribe':
        if not status(tenant,'billing')['ready']:raise ServiceError('Configure and enable platform subscription billing first.')
        from platform_ai import grant
        with store.db() as db:
            if grant(db,tenant)['active']:raise ServiceError('Your subscription is already active.',409)
        plan=plans().get(data.get('plan'))
        if not plan:raise ServiceError('Choose a server-configured plan.')
        remote=razorpay(tenant,'billing','GET','plans/'+plan['plan_id'])
        if remote.get('item',{}).get('amount')!=plan['amount_minor'] or remote.get('item',{}).get('currency')!=plan['currency'] or remote.get('period')!=plan['interval'] or remote.get('interval')!=1:
            raise ServiceError('The configured price does not match the Razorpay plan. Ask the platform operator to correct it.',409)
        payload={'plan_id':plan['plan_id'],'total_count':plan.get('cycles',12),'quantity':1,'customer_notify':False,'notes':{'workspace_id':tenant,'plan_key':data['plan']}}
        def project(result,job):
            if not re.fullmatch(r'sub_[A-Za-z0-9]+',str(result.get('id',''))) or result.get('plan_id')!=plan['plan_id']:raise ValueError()
            return {'provider_id':result['id'],'url':checkout_url(result.get('short_url')),'provider_status':result['status'],'plan':data['plan'],'current_end':0}
        with store.db() as db:
            previous=[j for j in store._list(db,tenant,'servicejob') if j['kind']=='billing.subscription']
        terminal=sum(j.get('result',{}).get('provider_status') in ('cancelled','completed','expired') for j in previous)
        return execute(store,ctx,'billing.subscription','workspace-'+str(terminal),payload,
            lambda job:razorpay(tenant,'billing','POST','subscriptions',dict(payload,notes=dict(payload['notes'],operation_id=job))),project)
    if operation in ('payments.cancel-link','payments.refund'):
        with store.db() as db:link=store._get(db,tenant,'servicejob',data.get('id'))
        if link['kind']!='payments.link' or not re.fullmatch(r'plink_[A-Za-z0-9]+',link.get('result',{}).get('provider_id','')):raise ServiceError('Choose a verified payment link.')
        if operation=='payments.cancel-link':
            if link['status']=='paid':raise ServiceError('A paid payment needs a refund, not link cancellation.')
            payload={}
            def project(result,identifier):
                if result.get('id')!=link['result']['provider_id'] or result.get('status')!='cancelled':raise ValueError()
                apply_resource(store,tenant,link,result,'payments')
                return {'provider_id':result['id'],'provider_status':'cancelled'}
            return execute(store,ctx,'payments.cancel',link['id'],payload,lambda identifier:razorpay(tenant,'payments','POST','payment_links/'+link['result']['provider_id']+'/cancel',payload),project)
        payment_id=link.get('result',{}).get('payment_id')
        if link['status']!='paid' or not isinstance(payment_id,str) or not re.fullmatch(r'pay_[A-Za-z0-9]+',payment_id):raise ServiceError('A captured payment ID from the signed paid webhook is required.')
        payload={'amount':link['payload']['amount'],'speed':'normal','payment_id':payment_id,'currency':link['payload']['currency']}
        def send(identifier):
            return razorpay(tenant,'payments','POST','payments/'+payment_id+'/refund',{'amount':payload['amount'],'speed':'normal','notes':{'workspace_id':tenant,'operation_id':identifier}})
        return execute(store,ctx,'payments.refund',link['id'],payload,send,lambda result,identifier:refund_projection(result,identifier,payload,tenant))
    if operation=='billing.cancel':
        with store.db() as db:subscription=store._get(db,tenant,'servicejob',data.get('id'))
        if subscription['kind']!='billing.subscription' or not re.fullmatch(r'sub_[A-Za-z0-9]+',subscription.get('result',{}).get('provider_id','')):raise ServiceError('Choose an existing subscription.')
        payload={'cancel_at_cycle_end':1}
        def cancel_project(result,identifier):
            apply_resource(store,tenant,subscription,result,'billing')
            return {'provider_id':result['id'],'provider_status':result['status'],'cancel_at_cycle_end':True}
        return execute(store,ctx,'billing.cancel',subscription['id'],payload,
            lambda identifier:razorpay(tenant,'billing','POST','subscriptions/'+subscription['result']['provider_id']+'/cancel',payload),cancel_project)
    if operation in ('payments.reconcile','billing.reconcile'):
        with store.db() as db:job=store._get(db,tenant,'servicejob',data.get('id'))
        scope='payments' if operation.startswith('payments') else 'billing'
        if job['kind']=='payments.refund' and scope=='payments':
            identifier=job.get('result',{}).get('provider_id') or data.get('provider_id')
            if not isinstance(identifier,str) or not re.fullmatch(r'rfnd_[A-Za-z0-9]+',identifier):raise ServiceError('Enter the verified refund ID.')
            resource=razorpay(tenant,'payments','GET','refunds/'+identifier)
            result=refund_projection(resource,job['id'],job['payload'],tenant)
            with store.db() as db:
                current=store._get(db,tenant,'servicejob',job['id'])
                if current.get('result',{}).get('provider_status')!='processed':
                    current.update(result=result,status='refunded' if result['provider_status']=='processed' else 'created',error='');store._put(db,tenant,'servicejob',current,current['id'])
            return public(current)
        if job['kind']!=('payments.link' if scope=='payments' else 'billing.subscription'):raise ServiceError('Choose the matching operation.')
        provider_id=job.get('result',{}).get('provider_id') or data.get('provider_id')
        pattern=r'plink_[A-Za-z0-9]+' if scope=='payments' else r'sub_[A-Za-z0-9]+'
        if not isinstance(provider_id,str) or not re.fullmatch(pattern,provider_id):raise ServiceError('Enter the verified provider resource ID to reconcile an uncertain operation.')
        resource=razorpay(tenant,scope,'GET',('payment_links/' if scope=='payments' else 'subscriptions/')+provider_id)
        apply_resource(store,tenant,job,resource,scope)
        with store.db() as db:return public(store._get(db,tenant,'servicejob',job['id']))
    raise ServiceError('Unknown payment or billing operation.',404)


def validate_resource_identity(job,resource,scope):
    pattern=r'plink_[A-Za-z0-9]+' if scope=='payments' else r'sub_[A-Za-z0-9]+'
    if not isinstance(resource,dict) or not re.fullmatch(pattern,str(resource.get('id',''))):raise ServiceError('Invalid provider resource identity.',409)
    known=job.get('result',{}).get('provider_id')
    if known and resource['id']!=known:raise ServiceError('Provider resource differs from the recorded operation.',409)
    statuses=('created','partially_paid','paid','cancelled','expired') if scope=='payments' else ('created','authenticated','active','pending','halted','paused','cancelled','completed','expired')
    if resource.get('status') not in statuses:raise ServiceError('Unrecognized provider resource status.',409)
    if scope=='billing' and resource.get('current_end') is not None and (type(resource['current_end']) is not int or resource['current_end']<0):raise ServiceError('Invalid subscription period.',409)


def apply_resource(store,tenant,job,resource,scope):
    validate_resource_identity(job,resource,scope)
    if scope=='payments':
        expected=job['payload']
        if resource.get('reference_id')!=job['id'] or resource.get('amount')!=expected['amount'] or resource.get('currency')!=expected['currency']:raise ServiceError('Provider identity or amount does not match this workspace order.',409)
        result={'provider_id':resource['id'],'provider_status':resource['status'],'amount_minor':expected['amount'],'currency':expected['currency']}
        if resource.get('short_url'):result['url']=checkout_url(resource['short_url'])
        paid=resource.get('status')=='paid' and type(resource.get('amount_paid')) is int and resource['amount_paid']==expected['amount']
        if resource.get('status')=='paid' and not paid:raise ServiceError('Paid resource amount does not match the order.',409)
    else:
        notes=resource.get('notes') or {}
        if resource.get('plan_id')!=job['payload']['plan_id'] or notes.get('workspace_id')!=tenant or notes.get('operation_id')!=job['id']:raise ServiceError('Subscription does not belong to this workspace operation.',409)
        result={'provider_id':resource['id'],'provider_status':resource['status'],'plan':job['payload']['notes']['plan_key'],'current_end':resource.get('current_end') or 0}
        if resource.get('short_url'):result['url']=checkout_url(resource['short_url'])
        paid=False
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'servicejob',job['id'])
        if current.get('result',{}).get('provider_status')=='paid' and scope=='payments' and not paid:return
        if scope=='billing' and current.get('result',{}).get('provider_status') in ('cancelled','completed','expired') and result['provider_status'] not in ('cancelled','completed','expired'):raise ServiceError('A terminal subscription cannot be reactivated by this response.',409)
        if scope=='payments' and current.get('result',{}).get('payment_id'):result['payment_id']=current['result']['payment_id']
        current.update(result=result,status='paid' if paid else 'created',error='',updated=int(time.time()))
        store._put(db,tenant,'servicejob',current,current['id'])


def webhook(store,tenant,scope,raw,headers):
    c=config(tenant,scope);normalized={str(k).lower():v for k,v in headers.items()}
    signature=normalized.get('x-razorpay-signature','')
    if scope not in ('payments','billing') or not c['WEBHOOK_SECRET'] or not hmac.compare_digest(hmac.new(c['WEBHOOK_SECRET'].encode(),raw,hashlib.sha256).hexdigest(),signature):raise ServiceError('Invalid Razorpay webhook signature.',403)
    body=json.loads(raw)
    if not isinstance(body,dict):raise ServiceError('A webhook object is required.')
    if body.get('account_id')!=c['ACCOUNT_ID'] or not c['ACCOUNT_ID']:raise ServiceError('Razorpay account mismatch.',403)
    event_id=normalized.get('x-razorpay-event-id','')
    if not isinstance(event_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}',event_id):raise ServiceError('A valid event ID is required.')
    refund=(body.get('payload',{}).get('refund') or {}).get('entity')
    if scope=='payments' and isinstance(refund,dict):
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            digest=hashlib.sha256(raw).hexdigest()
            prior=next((e for e in store._list(db,tenant,'serviceevent') if e['scope']==scope and e['event_id']==event_id),None)
            if prior:
                if prior['digest']!=digest:raise ServiceError('Event ID reused with different content.',409)
                return {'received':True,'duplicate':True}
            job=next((j for j in store._list(db,tenant,'servicejob') if j['kind']=='payments.refund' and j['id']==(refund.get('notes') or {}).get('operation_id')),None)
            if not job:raise ServiceError('Unknown scoped refund.',404)
            result=refund_projection(refund,job['id'],job['payload'],tenant)
            if job.get('result',{}).get('provider_status')!='processed':
                job.update(result=result,status='refunded' if result['provider_status']=='processed' else 'created',error='');store._put(db,tenant,'servicejob',job,job['id'])
            store._put(db,tenant,'serviceevent',dict(scope=scope,event_id=event_id,digest=digest,created=int(time.time()),job_id=job['id']))
        return {'received':True,'duplicate':False}
    resource=(body.get('payload',{}).get('payment_link' if scope=='payments' else 'subscription') or {}).get('entity')
    if not isinstance(resource,dict):return {'received':True,'ignored':True}
    with store.db() as db:
        jobs=store._list(db,tenant,'servicejob')
        job=next((j for j in jobs if j['kind']==('payments.link' if scope=='payments' else 'billing.subscription') and
            (resource.get('reference_id')==j['id'] if scope=='payments' else (resource.get('notes') or {}).get('operation_id')==j['id'])),None)
    if not job:raise ServiceError('Unknown scoped Razorpay resource.',404)
    digest=hashlib.sha256(raw).hexdigest();stamp=body.get('created_at')
    if type(stamp) is not int:raise ServiceError('Invalid event timestamp.')
    # Serialize event ingestion and resource projection using the store lock below.
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        prior=next((e for e in store._list(db,tenant,'serviceevent') if e['scope']==scope and e['event_id']==event_id),None)
        if prior:
            if prior['digest']!=digest:raise ServiceError('Event ID reused with different content.',409)
            return {'received':True,'duplicate':True}
        current=store._get(db,tenant,'servicejob',job['id'])
        # Validate without network; never grant access from a redirect callback.
        validate_resource_identity(current,resource,scope)
        if scope=='payments':
            expected=current['payload']
            if resource.get('reference_id')!=job['id'] or resource.get('amount')!=expected['amount'] or resource.get('currency')!=expected['currency']:raise ServiceError('Payment amount or reference mismatch.',409)
        else:
            if resource.get('plan_id')!=current['payload']['plan_id'] or (resource.get('notes') or {}).get('workspace_id')!=tenant:raise ServiceError('Subscription scope mismatch.',409)
        previous=current.get('result',{}).get('provider_status','')
        ranks={'created':0,'authenticated':1,'active':2,'pending':3,'halted':4,'paused':5,'cancelled':6,'completed':6,'expired':6}
        advances=stamp>current.get('event_created',0) or stamp==current.get('event_created',0) and ranks.get(resource.get('status'),0)>=ranks.get(previous,0)
        if scope=='billing' and previous in ('cancelled','completed','expired') and resource.get('status') not in ('cancelled','completed','expired'):advances=False
        if advances:

            result=dict(current.get('result',{}),provider_id=resource['id'],provider_status=resource['status'])
            if scope=='billing':result.update(plan=current['payload']['notes']['plan_key'],current_end=resource.get('current_end') or 0)
            paid=scope=='payments' and resource.get('status')=='paid' and type(resource.get('amount_paid')) is int and resource['amount_paid']==current['payload']['amount']
            payment=(body.get('payload',{}).get('payment') or {}).get('entity',{})
            if paid and isinstance(payment,dict) and re.fullmatch(r'pay_[A-Za-z0-9]+',str(payment.get('id',''))) and payment.get('status')=='captured' and payment.get('amount')==current['payload']['amount'] and payment.get('currency')==current['payload']['currency']:result['payment_id']=payment['id']
            if current.get('status')!='paid' or paid:
                current.update(result=result,status='paid' if paid else 'created',event_created=stamp,updated=int(time.time()),error='')
                store._put(db,tenant,'servicejob',current,current['id'])
        store._put(db,tenant,'serviceevent',dict(scope=scope,event_id=event_id,digest=digest,created=stamp,job_id=job['id']))
    return {'received':True,'duplicate':False}


def refund_projection(resource,identifier,payload,tenant):
    notes=resource.get('notes') or {}
    if not re.fullmatch(r'rfnd_[A-Za-z0-9]+',str(resource.get('id',''))) or resource.get('payment_id')!=payload['payment_id'] or resource.get('amount')!=payload['amount'] or resource.get('currency')!=payload['currency'] or notes.get('workspace_id')!=tenant or notes.get('operation_id')!=identifier or resource.get('status') not in ('pending','processed','failed'):
        raise ServiceError('Refund identity, amount or workspace mismatch.',409)
    return {'provider_id':resource['id'],'provider_status':resource['status'],'payment_id':payload['payment_id'],'amount_minor':payload['amount'],'currency':payload['currency']}
