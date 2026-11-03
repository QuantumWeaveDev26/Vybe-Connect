"""Account-wide authenticator MFA. Secrets remain in the private server database."""
import base64
import hashlib
import hmac
import json
import re
import secrets
import struct
import time
from urllib.parse import quote, urlencode


class MFAError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def totp(secret,stamp,digits=6):
    key=base64.b32decode(secret,casefold=True)
    digest=hmac.new(key,struct.pack('>Q',int(stamp)//30),hashlib.sha1).digest()
    offset=digest[-1]&15
    return str((int.from_bytes(digest[offset:offset+4],'big')&0x7fffffff)%10**digits).zfill(digits)


def code_hash(user,code):return hashlib.sha256((user+':'+code).encode()).hexdigest()


def new_recovery(user):
    codes=[secrets.token_hex(8) for _ in range(10)]
    return codes,json.dumps([code_hash(user,c) for c in codes])


def row_for(db,user):return db.execute('SELECT * FROM account_mfa WHERE user=?',(user,)).fetchone()


def status(db,user):
    row=row_for(db,user)
    return {'enabled':bool(row and row['secret']),'recovery_remaining':len(json.loads(row['recovery'])) if row and row['secret'] else 0}


def consume(db,user,code):
    """Call only within the same write transaction as the protected operation."""
    row=row_for(db,user)
    if not row or not row['secret']:return
    if not isinstance(code,str) or len(code)>64:raise MFAError('Invalid authenticator or recovery code.',401)
    code=code.strip().replace(' ','')
    if re.fullmatch(r'[0-9]{6}',code):
        counter=int(time.time())//30
        matches=[step for step in range(counter-1,counter+2) if step>row['last_counter'] and hmac.compare_digest(totp(row['secret'],step*30),code)]
        if matches:
            db.execute('UPDATE account_mfa SET last_counter=? WHERE user=?',(max(matches),user));return
    elif re.fullmatch(r'[0-9a-f]{16}',code):
        remaining=json.loads(row['recovery']);digest=code_hash(user,code)
        match=next((x for x in remaining if hmac.compare_digest(x,digest)),None)
        if match:
            remaining.remove(match);db.execute('UPDATE account_mfa SET recovery=? WHERE user=?',(json.dumps(remaining),user));return
    raise MFAError('Invalid authenticator or recovery code. Wait for a fresh code or use an unused recovery code.',401)


def action(store,ctx,operation,data):
    from store import password_hash
    user_id=ctx['user']['id'];stamp=int(time.time());password=data.get('current_password')
    if not isinstance(password,str) or not 12<=len(password)<=256:raise MFAError('Current password is incorrect.',403)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM sessions WHERE token=? AND user=? AND expires>?',(ctx.get('_session_hash',''),user_id,stamp)).fetchone():raise MFAError('Sign in again before changing security settings.',401)
        user=db.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
        if not user or not hmac.compare_digest(password_hash(password,user['salt']),user['password']):raise MFAError('Current password is incorrect.',403)
        row=row_for(db,user_id)
        if operation=='begin':
            if row and row['secret']:raise MFAError('MFA is already enabled. Disable it before enrolling another authenticator.',409)
            secret=base64.b32encode(secrets.token_bytes(20)).decode()
            db.execute("INSERT INTO account_mfa(user,secret,last_counter,recovery,pending,pending_until) VALUES(?,'',-1,'[]',?,?) ON CONFLICT(user) DO UPDATE SET pending=excluded.pending,pending_until=excluded.pending_until",(user_id,secret,stamp+600))
            return {'secret':secret,'expires':stamp+600,'uri':'otpauth://totp/'+quote('VYBE Connect:'+user['email'],safe='')+'?'+urlencode({'secret':secret,'issuer':'VYBE Connect','algorithm':'SHA1','digits':6,'period':30})}
        if operation=='confirm':
            if not row or row['secret'] or not row['pending'] or row['pending_until']<=stamp:raise MFAError('Enrollment expired or unavailable. Start again.',409)
            code=data.get('code');counter=stamp//30
            matches=[step for step in range(counter-1,counter+2) if isinstance(code,str) and re.fullmatch(r'[0-9]{6}',code.strip()) and hmac.compare_digest(totp(row['pending'],step*30),code.strip())]
            if not matches:raise MFAError('Enter a valid six-digit code from your authenticator.',401)
            codes,hashed=new_recovery(user_id)
            db.execute("UPDATE account_mfa SET secret=pending,pending='',pending_until=0,last_counter=?,recovery=? WHERE user=?",(max(matches),hashed,user_id))
            result={'enabled':True,'recovery_codes':codes,'sessions_revoked':True}
        elif operation in ['disable','recovery']:
            if not row or not row['secret']:raise MFAError('MFA is not enabled.',409)
            consume(db,user_id,data.get('code'))
            if operation=='disable':
                db.execute('DELETE FROM account_mfa WHERE user=?',(user_id,));result={'enabled':False,'sessions_revoked':True}
            else:
                codes,hashed=new_recovery(user_id);db.execute('UPDATE account_mfa SET recovery=? WHERE user=?',(hashed,user_id));result={'enabled':True,'recovery_codes':codes,'sessions_revoked':False}
        else:raise MFAError('Unknown security action.',404)
        if result['sessions_revoked']:db.execute('DELETE FROM sessions WHERE user=?',(user_id,))
        for membership in db.execute('SELECT tenant FROM members WHERE user=?',(user_id,)):
            db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(membership['tenant'],'Account security','account.mfa.'+operation,stamp))
        return result
