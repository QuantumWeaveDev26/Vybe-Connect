"""Workspace-bound, expiring, hash-only tokens for the read-only public API."""
import hashlib
import json
import re
import secrets
import time

SCOPES=('contacts:read','messages:read','analytics:read')


class APIError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def initialize(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS api_tokens(
        id TEXT PRIMARY KEY,tenant TEXT NOT NULL,user TEXT NOT NULL,name TEXT NOT NULL,
        token_hash TEXT NOT NULL,scopes TEXT NOT NULL,created INTEGER NOT NULL,
        expires INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,last_used INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS api_token_tenant ON api_tokens(tenant,created);
        CREATE TABLE IF NOT EXISTS api_token_budget(token TEXT PRIMARY KEY,minute INTEGER,hits INTEGER);''')


def admin(db,ctx):
    row=db.execute('SELECT m.role FROM members m JOIN sessions s ON s.user=m.user WHERE m.tenant=? AND m.user=? AND s.token=? AND s.expires>?',
        (ctx['tenant_id'],ctx['user']['id'],ctx.get('_session_hash',''),int(time.time()))).fetchone()
    if not row or row['role']!='admin':raise APIError('Sign in as a workspace administrator.',403)


def listing(store,ctx,strict=True):
    if ctx.get('role')!='admin':
        if strict:raise APIError('Administrator access required.',403)
        return []
    with store.db() as db:
        try:admin(db,ctx)
        except APIError:
            if strict:raise
            return []
        rows=db.execute('SELECT id,name,scopes,created,expires,revoked,last_used FROM api_tokens WHERE tenant=? ORDER BY (revoked=0 AND expires>?) DESC,created DESC,id LIMIT 100',(ctx['tenant_id'],int(time.time()))).fetchall()
    return [dict(dict(row),scopes=json.loads(row['scopes'])) for row in rows]


def create(store,ctx,data):
    name=data.get('name');scopes=data.get('scopes');days=data.get('days')
    if not isinstance(name,str) or not name.strip() or len(name)>80:raise APIError('Enter a token name of 1–80 characters.')
    if not isinstance(scopes,list) or not 1<=len(scopes)<=len(SCOPES) or any(s not in SCOPES for s in scopes) or len(set(scopes))!=len(scopes):raise APIError('Select valid read-only scopes.')
    if type(days) is not int or days not in (7,30,90,365):raise APIError('Choose a supported token lifetime.')
    stamp=int(time.time());identifier=secrets.token_hex(8);token='vybe_'+identifier+'_'+secrets.token_urlsafe(32)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');admin(db,ctx)
        count=db.execute('SELECT COUNT(*) FROM api_tokens WHERE tenant=? AND revoked=0 AND expires>?',(ctx['tenant_id'],stamp)).fetchone()[0]
        if count>=25:raise APIError('Revoke an existing token before adding another.',409)
        db.execute('INSERT INTO api_tokens VALUES(?,?,?,?,?,?,?,?,0,0)',(identifier,ctx['tenant_id'],ctx['user']['id'],name.strip(),hashlib.sha256(token.encode()).hexdigest(),json.dumps(sorted(scopes)),stamp,stamp+days*86400))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(ctx['tenant_id'],ctx['user']['name'],'api_token.created:'+identifier,stamp))
    return {'id':identifier,'token':token,'expires':stamp+days*86400}


def revoke(store,ctx,data):
    identifier=data.get('id')
    if not isinstance(identifier,str) or not re.fullmatch(r'[a-f0-9]{16}',identifier):raise APIError('Choose a token to revoke.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');admin(db,ctx)
        row=db.execute('SELECT id FROM api_tokens WHERE id=? AND tenant=?',(identifier,ctx['tenant_id'])).fetchone()
        if not row:raise APIError('Token not found in this workspace.',404)
        db.execute('UPDATE api_tokens SET revoked=1 WHERE id=?',(identifier,))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(ctx['tenant_id'],ctx['user']['name'],'api_token.revoked:'+identifier,int(time.time())))
    return {'ok':True}


def authenticate(store,authorization,scope):
    match=re.fullmatch(r'Bearer (vybe_([a-f0-9]{16})_[A-Za-z0-9_-]{43})',authorization or '')
    if not match:raise APIError('A valid Bearer API token is required.',401)
    stamp=int(time.time());token,identifier=match.groups()
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT a.*,u.name AS user_name,m.role FROM api_tokens a JOIN users u ON u.id=a.user JOIN members m ON m.user=a.user AND m.tenant=a.tenant WHERE a.id=?',(identifier,)).fetchone()
        digest=hashlib.sha256(token.encode()).hexdigest()
        if not row or not secrets.compare_digest(row['token_hash'],digest) or row['revoked'] or row['expires']<=stamp or row['role']!='admin':raise APIError('API token is expired, revoked or invalid.',401)
        if scope not in json.loads(row['scopes']):raise APIError('This token does not allow the requested scope.',403)
        minute=stamp//60;budget=db.execute('SELECT minute,hits FROM api_token_budget WHERE token=?',(identifier,)).fetchone()
        if budget and budget['minute']==minute and budget['hits']>=60:raise APIError('API rate limit reached. Try again next minute.',429)
        hits=budget['hits']+1 if budget and budget['minute']==minute else 1
        db.execute('INSERT INTO api_token_budget VALUES(?,?,?) ON CONFLICT(token) DO UPDATE SET minute=excluded.minute,hits=excluded.hits',(identifier,minute,hits))
        db.execute('UPDATE api_tokens SET last_used=? WHERE id=?',(stamp,identifier))
    return {'tenant_id':row['tenant'],'user':{'id':row['user'],'name':row['user_name']},'role':'admin'}


def one(query,key,default=''):
    value=query.get(key,[default])
    if len(value)!=1:raise APIError('Use one value for '+key+'.')
    return value[0]


def records(store,ctx,kind,query):
    try:
        raw_limit=one(query,'limit','50');raw_after=one(query,'after','0')
        if not re.fullmatch(r'\d{1,3}',raw_limit) or not re.fullmatch(r'\d{1,19}',raw_after):raise ValueError()
        limit=int(raw_limit);after=int(raw_after)
        if not 1<=limit<=100 or not 0<=after<2**63:raise ValueError()
    except (ValueError,TypeError):raise APIError('Use a limit of 1–100 and the returned numeric after cursor.') from None
    with store.db() as db:
        if kind=='contacts':
            rows=db.execute("SELECT rowid AS ordinal,id,data FROM entities WHERE tenant=? AND kind='contact' AND rowid>? ORDER BY rowid LIMIT ?",(ctx['tenant_id'],after,limit+1)).fetchall()
            allowed=('name','phone','tags','attributes','optin','status','assignee','created','updated')
            items=[dict({k:v for k,v in json.loads(row['data']).items() if k in allowed},id=row['id']) for row in rows[:limit]]
        else:
            contact=one(query,'contact_id')
            if contact and not re.fullmatch(r'[a-f0-9]{16}',contact):raise APIError('Use a valid contact ID.')
            sql="SELECT rowid AS ordinal,id,contact,direction,body,status,ts,external_id FROM messages WHERE tenant=? AND rowid>? AND ((direction='in' AND status='received') OR (direction='out' AND status IN ('accepted','sent','delivered','read','failed','unknown','sending')))"
            args=[ctx['tenant_id'],after]
            if contact:sql+=' AND contact=?';args.append(contact)
            rows=db.execute(sql+' ORDER BY rowid LIMIT ?',(*args,limit+1)).fetchall()
            items=[{k:row[k] for k in ('id','contact','direction','body','status','ts','external_id')} for row in rows[:limit]]
    return {'workspace_id':ctx['tenant_id'],'data':items,'next_after':str(rows[limit-1]['ordinal']) if len(rows)>limit else None}


def read(store,authorization,path,query,workspace=None):
    routes={'/api/v1/contacts':('contacts:read','contacts'),'/api/v1/messages':('messages:read','messages'),'/api/v1/analytics':('analytics:read','analytics')}
    if path not in routes:raise APIError('Unknown public API resource.',404)
    scope,kind=routes[path];ctx=authenticate(store,authorization,scope)
    if workspace and workspace!=ctx['tenant_id'] or one(query,'workspace',ctx['tenant_id'])!=ctx['tenant_id']:raise APIError('Token is bound to a different workspace.',403)
    if kind=='analytics':return store.message_analytics(ctx,one(query,'from'),one(query,'to'))
    return records(store,ctx,kind,query)
