"""Single-use credential-bound reset links and a no-retry SMTP worker."""
import base64
import hashlib
import hmac
import re
import secrets
import time
from recovery_mail import configuration,send_recovery

PUBLIC_RESPONSE={'ok':True,'message':'If an eligible account exists, a password reset link will be emailed.'}


def fingerprint(user):return hashlib.sha256((user['email']+'|'+user['salt']+'|'+user['password']).encode()).hexdigest()


def token_for(identifier,user):
    key=configuration()['secret']
    material='teamwave-reset-v1|'+identifier+'|'+user['id']+'|'+fingerprint(user)
    signature=base64.urlsafe_b64encode(hmac.new(key.encode(),material.encode(),hashlib.sha256).digest()).decode().rstrip('=')
    return identifier+'.'+signature


def request(store,email):
    cfg=configuration();stamp=int(time.time())
    if not cfg['ready'] or not isinstance(email,str) or len(email)>200:return dict(PUBLIC_RESPONSE)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM password_resets WHERE expires<?',(stamp-7*86400,))
        user=db.execute('SELECT * FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
        if not user:return dict(PUBLIC_RESPONSE)
        recent=db.execute('SELECT COUNT(*) AS count,MAX(created) AS latest FROM password_resets WHERE user=? AND created>?',(user['id'],stamp-900)).fetchone()
        if recent['count']>=3 or recent['latest'] is not None and recent['latest']>stamp-60:return dict(PUBLIC_RESPONSE)
        identifier=secrets.token_hex(16);token=token_for(identifier,user)
        db.execute("INSERT INTO password_resets VALUES(?,?,?,?,?,?,0,0,'queued','')",(identifier,user['id'],hashlib.sha256(token.encode()).hexdigest(),fingerprint(user),stamp,stamp+900))
    return dict(PUBLIC_RESPONSE)


def complete(store,token,password):
    from store import Problem
    if not isinstance(password,str) or not 12<=len(password)<=256:raise Problem('Use a new password of 12-256 characters.')
    failure='Reset link is invalid, expired or already used. Request a new link.'
    if not configuration()['ready'] or not isinstance(token,str) or not re.fullmatch(r'[0-9a-f]{32}\.[A-Za-z0-9_-]{43}',token):raise Problem(failure)
    stamp=int(time.time());identifier=token.split('.')[0]
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        reset=db.execute('SELECT * FROM password_resets WHERE id=?',(identifier,)).fetchone()
        user=db.execute('SELECT * FROM users WHERE id=?',(reset['user'],)).fetchone() if reset else None
        if not reset or not user or reset['used'] or reset['revoked'] or reset['expires']<=stamp or not hmac.compare_digest(reset['token_hash'],hashlib.sha256(token.encode()).hexdigest()) or not hmac.compare_digest(reset['fingerprint'],fingerprint(user)) or not hmac.compare_digest(token,token_for(identifier,user)):raise Problem(failure)
        db.execute('UPDATE password_resets SET used=? WHERE id=?',(stamp,identifier))
        return store._replace_password(db,user,password,'account.password.email_recovery')


def process_once(store):
    cfg=configuration()
    if not cfg['ready']:return False
    stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("UPDATE password_resets SET mail_status='expired' WHERE mail_status='queued' AND expires<=?",(stamp,))
        reset=db.execute("SELECT * FROM password_resets WHERE mail_status='queued' ORDER BY created,id LIMIT 1").fetchone()
        if not reset:return False
        user=db.execute('SELECT * FROM users WHERE id=?',(reset['user'],)).fetchone()
        if not user or reset['used'] or reset['revoked'] or not hmac.compare_digest(reset['fingerprint'],fingerprint(user)) or not hmac.compare_digest(reset['token_hash'],hashlib.sha256(token_for(reset['id'],user).encode()).hexdigest()):
            db.execute("UPDATE password_resets SET mail_status='cancelled' WHERE id=?",(reset['id'],));return True
        token=token_for(reset['id'],user);recipient=user['email'];identifier=reset['id']
        db.execute("UPDATE password_resets SET mail_status='sending' WHERE id=?",(identifier,))
    outcome='sent';error=''
    try:send_recovery(recipient,cfg['origin']+'/#reset='+token)
    except Exception:outcome='failed_or_unknown';error='SMTP delivery failed or is uncertain. Request a new link.'
    with store.db() as db:db.execute('UPDATE password_resets SET mail_status=?,error=? WHERE id=?',(outcome,error,identifier))
    return True
