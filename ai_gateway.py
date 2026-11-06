"""Original VYBE gateway adapter. No third-party gateway implementation is copied.

Only operator-configured HTTPS Responses API destinations can receive requests.
"""
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError


def catalog():
    try:
        raw=json.loads(os.environ.get('TW_AI_GATEWAYS','{}'))
        if not isinstance(raw,dict) or len(raw)>10:raise ValueError()
        result={}
        for id,c in raw.items():
            if not re.fullmatch(r'[a-z0-9_-]{1,40}',id) or not isinstance(c,dict):raise ValueError()
            url=c.get('base_url','');p=urlsplit(url);models=c.get('models',[]);limit=c.get('requests_per_day',100)
            if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment or not p.path.endswith('/v1') or p.port not in (None,443):raise ValueError()
            if not isinstance(models,list) or not 1<=len(models)<=20 or any(not isinstance(m,str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,100}',m) for m in models):raise ValueError()
            if type(limit) is not int or not 1<=limit<=10000:raise ValueError()
            result[id]={'label':str(c.get('label',id))[:80],'base_url':url,'models':models,'requests_per_day':limit}
        return result
    except (ValueError,TypeError,AttributeError):return {}


def options():return [{'id':id,'label':c['label'],'models':c['models'],'requests_per_day':c['requests_per_day']} for id,c in catalog().items()]


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS ai_gateway_requests(id TEXT PRIMARY KEY,tenant TEXT,day TEXT,model TEXT,status TEXT,input_tokens INTEGER,output_tokens INTEGER,created INTEGER)')
    db.execute('CREATE INDEX IF NOT EXISTS gateway_daily_usage ON ai_gateway_requests(tenant,day)')


def usage(store,db,tenant):
    day=time.strftime('%Y-%m-%d',time.gmtime())
    row=db.execute('SELECT COUNT(*) AS requests,SUM(input_tokens) AS input_tokens,SUM(output_tokens) AS output_tokens FROM ai_gateway_requests WHERE tenant=? AND day=?',(tenant,day)).fetchone()
    return dict(row,day=day,timezone='UTC')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


@contextmanager
def database(path):
    db=sqlite3.connect(path,timeout=15)
    try:
        with db:yield db
    finally:db.close()


def request(tenant,path,model,system,question,history,structured=False,schema=None):
    from ai_connection import settings
    from ai import ai_status
    from openai_adapter import request_openai
    saved=settings(tenant) or {};c=catalog().get(saved.get('gateway_id'))
    status=ai_status(tenant)
    if not c or not status['enabled'] or not status['configured'] or status['provider_id']!='gateway' or model not in c['models']:raise ValueError('The approved AI gateway connection is unavailable or paused.')
    if not path:raise ValueError('A durable workspace context is required for gateway usage.')
    # Reserve before the network write. Uncertain outcomes consume quota and never retry automatically.
    id=secrets.token_hex(16);day=time.strftime('%Y-%m-%d',time.gmtime())
    with database(path) as db:
        db.execute('BEGIN IMMEDIATE')
        count=db.execute('SELECT COUNT(*) FROM ai_gateway_requests WHERE tenant=? AND day=?',(tenant,day)).fetchone()[0]
        if count>=c['requests_per_day']:raise ValueError('Your daily AI gateway request limit has been reached. It resets at 00:00 UTC.')
        db.execute('INSERT INTO ai_gateway_requests VALUES(?,?,?,?,?,?,?,?)',(id,tenant,day,model,'submitted',None,None,int(time.time())))
    def transport(payload):
        # Blocking Responses compatibility avoids assuming a gateway supports OpenAI background polling/cancellation.
        payload['background']=False;payload['store']=False
        req=Request(c['base_url']+'/responses',json.dumps(payload).encode(),{'Authorization':'Bearer '+saved['key'],'Content-Type':'application/json','Accept':'application/json'},method='POST')
        try:
            with build_opener(NoRedirect).open(req,timeout=90) as response:
                raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:raise ValueError()
            result=json.loads(raw)
            if not isinstance(result,dict):raise ValueError()
            recorded=result.get('usage') or {}
            def tokens(name):
                v=recorded.get(name)
                return v if type(v) is int and 0<=v<=100000000 else None
            with database(path) as db:db.execute('UPDATE ai_gateway_requests SET status=?,input_tokens=?,output_tokens=? WHERE id=? AND tenant=?',('responded',tokens('input_tokens'),tokens('output_tokens'),id,tenant))
            return result
        except HTTPError as error:raise ValueError('AI gateway returned HTTP '+str(error.code)+'. No automatic retry was attempted.') from None
        except (URLError,OSError,ValueError,TimeoutError):raise ValueError('AI gateway response could not be confirmed. No automatic retry was attempted.') from None
    try:
        answer=request_openai(saved['key'],model,system,question,history,structured,schema,transport=transport)
        with database(path) as db:db.execute('UPDATE ai_gateway_requests SET status=? WHERE id=? AND tenant=?',('completed',id,tenant))
        return answer
    except Exception as error:
        with database(path) as db:db.execute("UPDATE ai_gateway_requests SET status='unknown' WHERE id=? AND tenant=?",(id,tenant))
        if isinstance(error,ValueError):raise ValueError(str(error).replace('OpenAI','AI gateway')) from None
        raise ValueError('AI gateway outcome is uncertain. No automatic retry was attempted.') from None
