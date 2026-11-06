"""Tenant-scoped embedding retrieval adapted from ChatbotX MIT knowledge patterns.

Opt-in provider usage only. Viewing pages and lexical searches never embed text.
"""
import hashlib
import json
import math
import time
from urllib.request import Request,build_opener
from urllib.error import HTTPError,URLError
from google_connections import NoRedirect,admin,fail

MODEL='text-embedding-3-small'
DIMENSIONS=256


def initialize(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS knowledge_vectors(tenant TEXT,document TEXT,chunk TEXT,model TEXT,digest TEXT,vector TEXT,PRIMARY KEY(tenant,chunk,model));
    CREATE TABLE IF NOT EXISTS knowledge_queries(tenant TEXT,hash TEXT,model TEXT,vector TEXT,expires INTEGER,PRIMARY KEY(tenant,hash,model));''')


def config(store,db,tenant):
    rows=store._list(db,tenant,'semanticsettings')
    return rows[0] if rows else {'enabled':False,'model':MODEL}


def allowed(tenant):
    from ai import ai_status
    status=ai_status(tenant)
    return status['enabled'] and status['configured'] and status['paid_allowed'] and status['provider_id']=='openai'


def normalized(values):
    if not isinstance(values,list) or len(values)!=DIMENSIONS or any(type(v) not in (int,float) or abs(v)>1000 or not math.isfinite(v) for v in values):fail('Invalid embedding response.',502)
    length=math.sqrt(sum(v*v for v in values))
    if not length:fail('Empty embedding response.',502)
    return [v/length for v in values]


def embed(tenant,texts):
    from ai import openai_key
    if not allowed(tenant):fail('Enable and approve the workspace OpenAI connection first.',409)
    body=json.dumps({'model':MODEL,'input':texts,'dimensions':DIMENSIONS,'encoding_format':'float'}).encode()
    try:
        req=Request('https://api.openai.com/v1/embeddings',body,{'Authorization':'Bearer '+openai_key(tenant),'Content-Type':'application/json'})
        with build_opener(NoRedirect).open(req,timeout=25) as response:
            raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:fail('Embedding response exceeds limits.',502)
            data=json.loads(raw).get('data')
        if not isinstance(data,list) or len(data)!=len(texts) or {r.get('index') for r in data}!=set(range(len(texts))):fail('Incomplete embedding response.',502)
        return [normalized(r.get('embedding')) for r in sorted(data,key=lambda r:r['index'])]
    except (HTTPError,URLError,OSError,TimeoutError,ValueError,TypeError,KeyError):fail('Embedding request could not be confirmed. No result was saved.',502)


def state(store,db,tenant):
    c=config(store,db,tenant);documents={d['id']:d for d in store._list(db,tenant,'knowledgedocument') if d['enabled']}
    counts={}
    for row in db.execute('SELECT document,digest,COUNT(*) AS count FROM knowledge_vectors WHERE tenant=? AND model=? GROUP BY document,digest',(tenant,MODEL)):
        if row['document'] in documents and row['digest']==documents[row['document']]['digest']:counts[row['document']]=row['count']
    return {'enabled':c['enabled'],'model':MODEL,'indexed':counts,'provider_ready':bool(allowed(tenant))}


def prepare_query(store,tenant,query,ctx=None):
    if not isinstance(query,str) or not 1<=len(query.strip())<=4000:return False
    digest=hashlib.sha256(query.encode()).hexdigest()
    with store.db() as db:
        if not config(store,db,tenant)['enabled'] or not allowed(tenant):return False
        if not db.execute('SELECT 1 FROM knowledge_vectors WHERE tenant=? AND model=? LIMIT 1',(tenant,MODEL)).fetchone():return False
        if db.execute('SELECT 1 FROM knowledge_queries WHERE tenant=? AND hash=? AND model=? AND expires>?',(tenant,digest,MODEL,int(time.time()))).fetchone():return True
    if ctx:admin(store,ctx)
    vector=embed(tenant,[query])[0]
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if ctx:admin(store,ctx)
        if not config(store,db,tenant)['enabled'] or not allowed(tenant):return False
        db.execute('DELETE FROM knowledge_queries WHERE expires<?',(int(time.time()),))
        db.execute('INSERT OR REPLACE INTO knowledge_queries VALUES(?,?,?,?,?)',(tenant,digest,MODEL,json.dumps(vector),int(time.time())+3600))
    return True


def rank(store,db,tenant,query,documents,rows):
    if not config(store,db,tenant)['enabled'] or not allowed(tenant):return {}
    cached=db.execute('SELECT vector FROM knowledge_queries WHERE tenant=? AND hash=? AND model=? AND expires>?',(tenant,hashlib.sha256(str(query).encode()).hexdigest(),MODEL,int(time.time()))).fetchone()
    if not cached:return {}
    vector=json.loads(cached['vector']);valid={r['id']:r for r in rows};scores={}
    for row in db.execute('SELECT * FROM knowledge_vectors WHERE tenant=? AND model=?',(tenant,MODEL)):
        if row['chunk'] not in valid or row['document'] not in documents or row['digest']!=documents[row['document']]['digest']:continue
        score=sum(a*b for a,b in zip(vector,json.loads(row['vector'])))
        if score>=0.25:scores[row['chunk']]=score
    return scores


def action(store,ctx,op,data):
    admin(store,ctx);tenant=ctx['tenant_id']
    if op=='semantic.configure':
        enabled=data.get('enabled')
        if type(enabled) is not bool:fail('Choose whether semantic retrieval is enabled.')
        if enabled and (data.get('confirm_paid') is not True or not allowed(tenant)):fail('Approve provider charges and enable the workspace OpenAI connection first.')
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE');admin(store,ctx);old=store._list(db,tenant,'semanticsettings')
            store._put(db,tenant,'semanticsettings',{'enabled':enabled,'model':MODEL,'updated':int(time.time())},old[0]['id'] if old else None)
            if not enabled:db.execute('DELETE FROM knowledge_queries WHERE tenant=?',(tenant,))
        return {'enabled':enabled}
    with store.db() as db:
        if not config(store,db,tenant)['enabled']:fail('Enable semantic retrieval first.',409)
    if data.get('confirm_paid') is not True:fail('Confirm that this real usage may incur OpenAI charges.')
    if op=='semantic.index':
        with store.db() as db:
            document=store._get(db,tenant,'knowledgedocument',data.get('document_id'))
            if not document['enabled']:fail('Enable this knowledge source first.')
            rows=[dict(r) for r in db.execute('SELECT * FROM knowledge_chunks WHERE tenant=? AND document=? ORDER BY ordinal',(tenant,document['id']))]
            indexed={r['chunk'] for r in db.execute('SELECT chunk FROM knowledge_vectors WHERE tenant=? AND document=? AND model=? AND digest=?',(tenant,document['id'],MODEL,document['digest']))}
            rows=[r for r in rows if r['id'] not in indexed][:32]
        if not rows:return {'indexed':0,'complete':True}
        vectors=embed(tenant,[r['text'] for r in rows])
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE');admin(store,ctx);current=store._get(db,tenant,'knowledgedocument',document['id'])
            if not current['enabled'] or current['digest']!=document['digest'] or not config(store,db,tenant)['enabled'] or not allowed(tenant):fail('Knowledge or authorization changed. No vectors were saved.',409)
            for row,vector in zip(rows,vectors):
                found=db.execute('SELECT text FROM knowledge_chunks WHERE tenant=? AND document=? AND id=?',(tenant,document['id'],row['id'])).fetchone()
                if not found or found['text']!=row['text']:fail('Knowledge source changed. Index again.',409)
                db.execute('INSERT OR REPLACE INTO knowledge_vectors VALUES(?,?,?,?,?,?)',(tenant,document['id'],row['id'],MODEL,document['digest'],json.dumps(vector)))
        return {'indexed':len(rows),'complete':len(indexed)+len(rows)>=document['chunks']}
    if op=='semantic.search':
        query=data.get('query','')
        if not isinstance(query,str) or not 1<=len(query.strip())<=4000:fail('Enter a question up to 4,000 characters.')
        prepare_query(store,tenant,query,ctx)
        from knowledge_documents import retrieve
        with store.db() as db:return {'passages':retrieve(store,db,tenant,query)}
    fail('Unknown knowledge operation.')
