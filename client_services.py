"""Operator-controlled client provisioning and signed-provider subscription access."""
import os
import time
from business_providers import status,plans
from service_jobs import ServiceError,public
from team_invitations import action as invitation_action


def platform_admin(ctx):
    owner=os.environ.get('TW_PLATFORM_OWNER_EMAIL','').strip().lower()
    return bool(owner and ctx['user']['email'].lower()==owner)


def state(store,db,ctx):
    tenant=ctx['tenant_id'];jobs=store._list(db,tenant,'servicejob')
    subscriptions=[job for job in jobs if job['kind']=='billing.subscription']
    current=subscriptions[-1] if subscriptions else None
    result=current.get('result',{}) if current else {}
    end=result.get('current_end',0)
    active=result.get('provider_status')=='active' and type(end) is int and end>int(time.time())
    return {'connections':{provider:status(tenant,provider) for provider in ('payments','shipping','billing')},
            'jobs':[public(j) for j in jobs[-100:] if ctx['role']=='admin' or not j['kind'].startswith('billing.')],'platform_admin':platform_admin(ctx),
            'plans':[dict({k:v for k,v in plan.items() if k!='plan_id'},key=key) for key,plan in plans().items()],
            'subscription':public(current) if current and ctx['role']=='admin' else None,'subscription_active':active,
            'billing_enforced':os.environ.get('TW_BILLING_ENFORCE','false').lower()=='true',
            'clients':store._list(db,tenant,'clientworkspace') if platform_admin(ctx) else []}


def action(store,ctx,operation,data):
    if not platform_admin(ctx) or ctx['role']!='admin':raise ServiceError('Platform operator access required.',403)
    if operation=='clients.create':
        name=data.get('name');email=data.get('email')
        import re
        if not isinstance(name,str) or not 1<=len(name.strip())<=100 or not isinstance(email,str) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()) or len(email)>200:raise ServiceError('Enter a client business name and owner email.')
        email=email.strip().lower()
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            existing=next((c for c in store._list(db,ctx['tenant_id'],'clientworkspace') if c['email']==email and c['name']==name.strip()),None)
            if existing:client=existing
            else:
                from secrets import token_hex
                tenant=token_hex(8)
                db.execute('INSERT INTO tenants VALUES(?,?)',(tenant,name.strip()))
                db.execute('INSERT INTO members VALUES(?,?,?)',(tenant,ctx['user']['id'],'admin'))
                client=store._put(db,ctx['tenant_id'],'clientworkspace',dict(tenant_id=tenant,name=name.strip(),email=email,created=int(time.time())))
        # Invitation creation is separately transactional; retries reuse the client.
        target=dict(ctx,tenant_id=client['tenant_id'])
        invitation=invitation_action(store,target,'invite.create',{'email':email,'role':'admin','hours':24})
        return {'client':client,'invitation':invitation}
    raise ServiceError('Unknown client service action.',404)


def enforce(store,ctx,operation):
    if os.environ.get('TW_BILLING_ENFORCE','false').lower()!='true' or platform_admin(ctx) or ctx.get('review_only'):return
    # Keep billing, account security, exports and read access available for recovery.
    if operation.startswith(('billing.','invite.','notification.','feedback.')) or operation in ('calls.end','calls.reject','calls.release','services.release-failed'):return
    with store.db() as db:current=state(store,db,ctx)
    if not current['subscription_active']:raise ServiceError('An active verified subscription is required for workspace changes.',402)
