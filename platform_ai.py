"""Platform-funded AI: verified subscriptions and atomic per-cycle request allowances."""
import json
import os
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path

def enabled():return os.environ.get('TW_PLATFORM_AI_MANAGED','false').lower()=='true'
def managed(tenant):return bool(enabled() and isinstance(tenant,str) and re.fullmatch(r'[a-f0-9]{16}',tenant) and os.environ.get('TW_AI_'+tenant.upper()+'_ALLOW_PAID','false').lower()!='true')
def path():return os.environ.get('TW_PLATFORM_AI_DB') or str(Path(os.environ.get('TW_DATA_DIR',str(Path(__file__).parent/'data')))/'teamwave.db')
def initialize(db):db.execute('CREATE TABLE IF NOT EXISTS platform_ai_usage(tenant TEXT,cycle TEXT,requests INTEGER,PRIMARY KEY(tenant,cycle))')

def grant(db,tenant):
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='servicejob' ORDER BY rowid",(tenant,)).fetchall()
    subscriptions=[(r[0],json.loads(r[1])) for r in rows if json.loads(r[1]).get('kind')=='billing.subscription']
    if not subscriptions:return {'active':False,'remaining':0,'limit':0}
    id,job=subscriptions[-1];result=job.get('result',{});end=result.get('current_end',0)
    from business_providers import plans
    key=job.get('payload',{}).get('notes',{}).get('plan_key');plan=plans().get(key)
    active=bool(plan and result.get('provider_status')=='active' and type(end) is int and end>time.time() and job.get('payload',{}).get('plan_id')==plan['plan_id'])
    if not active:return {'active':False,'remaining':0,'limit':0}
    limit=plan.get('ai_requests',50)
    if type(limit) is not int or not 1<=limit<=1000:limit=50
    cycle=id+':'+str(end);row=db.execute('SELECT requests FROM platform_ai_usage WHERE tenant=? AND cycle=?',(tenant,cycle)).fetchone();used=row[0] if row else 0
    return {'active':True,'cycle':cycle,'limit':limit,'used':used,'remaining':max(0,limit-used),'expires':end}

def entitlement(tenant):
    if not managed(tenant):return None
    try:
        with closing(sqlite3.connect('file:'+Path(path()).resolve().as_posix()+'?mode=rw',uri=True,timeout=15)) as db:return grant(db,tenant)
    except (sqlite3.Error,ValueError,TypeError):return {'active':False,'remaining':0,'limit':0}

def reserve(tenant,db_path,system,question,history):
    if not managed(tenant):return
    if os.environ.get('TW_AI_MODEL','')!='gpt-6-luna':raise ValueError('Platform AI model needs operator configuration.')
    if len((str(system)+str(question)+json.dumps(history)).encode())>30000:raise ValueError('This AI request is too large for the included allowance. Start a shorter conversation.')
    if not db_path or Path(db_path).resolve()!=Path(path()).resolve():raise ValueError('Platform AI workspace storage is unavailable.')
    with closing(sqlite3.connect(db_path,timeout=15)) as db:
        with db:
            db.execute('BEGIN IMMEDIATE');access=grant(db,tenant)
            if not access['active']:raise ValueError('Choose an active subscription to use included AI.')
            if not access['remaining']:raise ValueError('Your included AI requests are used up for this billing cycle.')
            db.execute('INSERT INTO platform_ai_usage VALUES(?,?,1) ON CONFLICT(tenant,cycle) DO UPDATE SET requests=requests+1',(tenant,access['cycle']))
