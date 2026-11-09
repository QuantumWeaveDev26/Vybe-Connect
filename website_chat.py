"""Visitor-owned website conversations, separate from WhatsApp identities and consent."""
import hashlib
import re
import secrets
import time


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS website_visitors(tenant TEXT,token_hash TEXT,contact TEXT,created INTEGER,expires INTEGER,PRIMARY KEY(tenant,token_hash))')


def session(db, tenant, token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        return None
    return db.execute('SELECT contact FROM website_visitors WHERE tenant=? AND token_hash=? AND expires>?',
                      (tenant, hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()


def message(store, tenant, data):
    from store import Problem, required, now
    if not isinstance(tenant, str) or not tenant:
        raise Problem('Choose a workspace for this chat.', 400)
    body = required(data.get('message'), 'Message', 4000)
    token = data.get('visitor_token')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        initialize(db)
        if not db.execute('SELECT 1 FROM tenants WHERE id=?', (tenant,)).fetchone():
            raise Problem('Workspace not found.', 404)
        visitor = session(db, tenant, token)
        if token and not visitor:
            raise Problem('This website chat session has expired. Start a new chat.', 401)
        if not visitor:
            count = db.execute('SELECT COUNT(*) FROM website_visitors WHERE tenant=? AND created>?', (tenant, now()-60)).fetchone()[0]
            if count >= 30:
                raise Problem('Chat is busy. Please try again in a minute.', 429)
            token = secrets.token_urlsafe(32)
            contact = store._put(db, tenant, 'contact', {
                'name': str(data.get('name') or 'Website visitor').strip()[:100],
                'phone': '', 'source': 'website_widget', 'channel': 'website',
                'tags': [], 'attributes': {}, 'optin': False, 'status': 'open',
                'assignee': '', 'last_inbound': now(),
            })
            db.execute('INSERT INTO website_visitors VALUES(?,?,?,?,?)',
                       (tenant, hashlib.sha256(token.encode()).hexdigest(), contact['id'], now(), now()+30*86400))
            cid = contact['id']
        else:
            cid = visitor['contact']
        hits = db.execute('SELECT COUNT(*) FROM messages WHERE tenant=? AND contact=? AND direction=? AND ts>?',
                          (tenant, cid, 'in', now()-60)).fetchone()[0]
        if hits >= 30:
            raise Problem('Please wait a minute before sending more messages.', 429)
        store._message(db, tenant, cid, body, 'in', 'received', external_id='website_'+secrets.token_hex(16))
        contact = store._get(db, tenant, 'contact', cid)
        store._put(db, tenant, 'contact', dict(contact, last_inbound=now(), status='open'), cid)
        rows = history_rows(db, tenant, cid)
    return {'success': True, 'contact_id': cid, 'visitor_token': token, 'messages': rows}


def history_rows(db, tenant, cid):
    return [dict(r) for r in reversed(db.execute("SELECT id,direction,body,ts FROM messages WHERE tenant=? AND contact=? AND direction IN ('in','out') ORDER BY ts DESC,rowid DESC LIMIT 50", (tenant,cid)).fetchall())]


def history(store, tenant, contact_id, token):
    from store import Problem
    with store.db() as db:
        initialize(db)
        visitor = session(db, tenant, token)
        if not visitor or visitor['contact'] != contact_id:
            raise Problem('A valid visitor session is required.', 401)
        return {'contact_id': contact_id, 'messages': history_rows(db, tenant, contact_id)}
