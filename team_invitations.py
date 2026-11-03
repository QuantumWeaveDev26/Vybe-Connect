import account_mfa
"""Hashed one-time workspace invitations. No email or external delivery."""
import hashlib
import hmac
import json
import re
import secrets
import time


class InviteError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def project(invite):
    result={key:invite[key] for key in ['id','email','role','created','expires','status']}
    if result['status']=='pending' and result['expires']<=int(time.time()):result['status']='expired'
    return result


def list_invites(store,db,ctx):
    return [project(i) for i in store._list(db,ctx['tenant_id'],'workspaceinvite')[-100:]] if ctx['role']=='admin' else []


def action(store,ctx,operation,data):
    if ctx['role']!='admin':raise InviteError('Administrator access required.',403)
    tenant=ctx['tenant_id'];stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(tenant,ctx['user']['id'])).fetchone():raise InviteError('Administrator access required.',403)
        if operation=='invite.create':
            email=data.get('email');role=data.get('role','agent');hours=data.get('hours',24)
            if not isinstance(email,str) or len(email)>200 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()):raise InviteError('Use a valid invitation email.')
            email=email.strip().lower()
            if role not in ['admin','agent'] or type(hours) is not int or not 1<=hours<=168:raise InviteError('Choose admin/agent and an expiry of 1–168 hours.')
            if db.execute('SELECT 1 FROM members m JOIN users u ON u.id=m.user WHERE m.tenant=? AND u.email=?',(tenant,email)).fetchone():raise InviteError('This account is already a workspace member.',409)
            pending=[i for i in store._list(db,tenant,'workspaceinvite') if i['status']=='pending' and i['expires']>stamp]
            if len(pending)>=50:raise InviteError('Use up to 50 pending invitations.')
            if any(i['email']==email for i in pending):raise InviteError('Revoke the pending invitation before issuing another.',409)
            token=secrets.token_urlsafe(32)
            record=store._put(db,tenant,'workspaceinvite',dict(email=email,role=role,created=stamp,expires=stamp+hours*3600,status='pending',issued_by=ctx['user']['id'],token_hash=hashlib.sha256(token.encode()).hexdigest()))
            result=dict(project(record),token=token)
        elif operation=='invite.revoke':
            old=store._get(db,tenant,'workspaceinvite',data.get('id'))
            if old['status']!='pending':raise InviteError('Only pending invitations can be revoked.',409)
            result=project(store._put(db,tenant,'workspaceinvite',dict(old,status='revoked',revoked_at=stamp),old['id']))
        else:raise InviteError('Unknown invitation action.',404)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,stamp))
    return result


def find(db,token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise InviteError('Invitation is invalid, expired or unavailable.',400)
    digest=hashlib.sha256(token.encode()).hexdigest()
    row=db.execute("SELECT id,tenant,data FROM entities WHERE kind='workspaceinvite' AND json_extract(data,'$.token_hash')=?",(digest,)).fetchone()
    if not row:raise InviteError('Invitation is invalid, expired or unavailable.',400)
    invite=dict(json.loads(row['data']),id=row['id'],tenant=row['tenant'])
    if invite['status']!='pending' or invite['expires']<=int(time.time()) or not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(invite['tenant'],invite['issued_by'])).fetchone():raise InviteError('Invitation is invalid, expired or unavailable.',400)
    return invite


def inspect(store,token):
    with store.db() as db:
        invite=find(db,token);workspace=db.execute('SELECT name FROM tenants WHERE id=?',(invite['tenant'],)).fetchone()
        if not workspace:raise InviteError('Invitation is invalid, expired or unavailable.')
        existing=bool(db.execute('SELECT 1 FROM users WHERE email=?',(invite['email'],)).fetchone())
        return dict(email=invite['email'],role=invite['role'],workspace=workspace['name'],expires=invite['expires'],existing_account=existing)


def accept(store,data):
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');invite=find(db,data.get('token'));tenant=invite.pop('tenant')
        user=db.execute('SELECT * FROM users WHERE email=?',(invite['email'],)).fetchone();password=data.get('password')
        if user:
            if not isinstance(password,str) or len(password)>256:raise InviteError('Existing account password is required.',401)
            candidate=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(user['salt']),310000).hex()
            if not hmac.compare_digest(candidate,user['password']):raise InviteError('Existing account password is incorrect.',401)
            try:account_mfa.consume(db,user['id'],data.get('code'))
            except account_mfa.MFAError as e:raise InviteError(str(e),e.code)
            user_id=user['id']
            if db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,user_id)).fetchone():raise InviteError('This account already has workspace access. Sign in normally.',409)
        else:user_id=store._new_user(db,data.get('name'),invite['email'],password)
        db.execute('INSERT INTO members VALUES(?,?,?)',(tenant,user_id,invite['role']))
        store._put(db,tenant,'workspaceinvite',dict(invite,status='accepted',accepted_by=user_id,accepted_at=int(time.time())),invite['id'])
        result=store._session(db,user_id)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'Invited account','invite.accept',int(time.time())))
    return dict(result,tenant_id=tenant)
