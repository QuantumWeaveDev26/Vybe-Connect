"""Customer-owned Google OAuth and adapters. Adapted from MIT ChatbotX patterns.

See third_party/chatbotx/NOTICE.md. No provider calls occur while viewing state.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
from urllib.parse import urlencode,quote,urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
import credential_vault
import embedded_signup as vault

SCOPES={'google_sheets':['https://www.googleapis.com/auth/spreadsheets'],
        'google_calendar':['https://www.googleapis.com/auth/calendar.events','https://www.googleapis.com/auth/calendar.events.freebusy']}
LOCK=threading.RLock()
CALLBACK='/oauth/google/callback'


def fail(message,code=400):
    from store import Problem
    raise Problem(message,code)


def admin(store,ctx):
    try:vault.administrator(store,ctx)
    except vault.ConnectionError as e:fail(str(e),e.code)


def configuration():
    origin=os.environ.get('TW_PUBLIC_ORIGIN','').rstrip('/');p=urlsplit(origin)
    client=os.environ.get('TW_GOOGLE_CLIENT_ID','');secret=os.environ.get('TW_GOOGLE_CLIENT_SECRET','')
    ready=bool(os.environ.get('TW_GOOGLE_ENABLED','false').lower()=='true' and client.endswith('.apps.googleusercontent.com') and secret and p.scheme=='https' and p.hostname and not p.path and not p.query and not p.fragment and not p.username and not p.password and credential_vault.keys())
    return {'ready':ready,'client_id':client,'secret':secret,'redirect':origin+CALLBACK}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def request(url,token='',data=None,method=None,form=False):
    if not any(url.startswith(base) for base in ('https://oauth2.googleapis.com/token','https://openidconnect.googleapis.com/v1/userinfo','https://sheets.googleapis.com/v4/spreadsheets/','https://www.googleapis.com/calendar/v3/')):fail('Unsupported Google endpoint.')
    headers={'Accept':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    raw=None
    if data is not None:
        raw=(urlencode(data) if form else json.dumps(data)).encode();headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
    try:
        with build_opener(NoRedirect).open(Request(url,raw,headers,method=method),timeout=20) as response:
            body=response.read(1024*1024+1)
            if len(body)>1024*1024:fail('Google response is too large.',502)
            return json.loads(body) if body else {}
    except HTTPError as e:
        # Never expose provider bodies, authorization codes, tokens or account data.
        fail('Google rejected the request (HTTP '+str(e.code)+'). Reconnect if access has expired.',502)
    except (URLError,TimeoutError,OSError,ValueError):fail('Google request could not be confirmed. Check the connection before retrying.',502)


def state(store,db,tenant):
    result={'setup_ready':configuration()['ready'],'connections':[],'jobs':[]}
    for kind in SCOPES:
        c=vault.read_credentials(tenant,kind)
        result['connections'].append({'kind':kind,'connected':bool(c and not c.get('disconnected') and c.get('refresh_token')),'email':c.get('email','') if c and not c.get('disconnected') else ''})
    result['jobs']=store._list(db,tenant,'googlejob')[-50:]
    return result


def start(store,ctx,kind):
    admin(store,ctx);c=configuration()
    if kind not in SCOPES:fail('Choose Google Sheets or Calendar.')
    if not c['ready']:fail('Google connection setup is required by the platform owner.',503)
    state=secrets.token_urlsafe(32);cookie=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    encrypted=credential_vault.seal({'tenant':ctx['tenant_id'],'verifier':verifier},ctx['tenant_id'],kind)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');admin(store,ctx)
        attempts=store._list(db,ctx['tenant_id'],'googleauth')
        for old in attempts:
            if old['expires']<time.time() or old.get('used'):db.execute("DELETE FROM entities WHERE tenant=? AND kind='googleauth' AND id=?",(ctx['tenant_id'],old['id']))
        store._put(db,ctx['tenant_id'],'googleauth',{'state':hashlib.sha256(state.encode()).hexdigest(),'cookie':hashlib.sha256(cookie.encode()).hexdigest(),'session':ctx['_session_hash'],'user':ctx['user']['id'],'kind':kind,'expires':int(time.time())+600,'used':False,'verifier':encrypted})
    params={'client_id':c['client_id'],'redirect_uri':c['redirect'],'response_type':'code','scope':' '.join(['openid','email']+SCOPES[kind]),'state':state,'access_type':'offline','prompt':'consent','code_challenge':challenge,'code_challenge_method':'S256'}
    return {'authorize_url':'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(params),'_flow_cookie':'tw_google_flow='+cookie+'; Path='+CALLBACK+'; HttpOnly; SameSite=Lax; Secure; Max-Age=600'}


def callback(store,query,cookie):
    value=query.get('state',[''])[0];code=query.get('code',[''])[0]
    if not value or len(value)>200 or not cookie or len(cookie)>200:fail('Google authorization expired. Start again.',403)
    digest=hashlib.sha256(value.encode()).hexdigest()
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        rows=db.execute("SELECT tenant,id,data FROM entities WHERE kind='googleauth'").fetchall()
        match=next(((r,json.loads(r['data'])) for r in rows if json.loads(r['data']).get('state')==digest),None)
        if not match:fail('Google authorization expired. Start again.',403)
        row,a=match;tenant=row['tenant'];kind=a['kind']
        if a['used'] or a['expires']<time.time() or not secrets.compare_digest(a['cookie'],hashlib.sha256(cookie.encode()).hexdigest()):fail('Google authorization expired. Start again.',403)
        ctx={'tenant_id':tenant,'user':{'id':a['user']},'role':'admin','_session_hash':a['session']};admin(store,ctx)
        store._put(db,tenant,'googleauth',dict(a,used=True,verifier={}),row['id'])
    if not code or len(code)>4096 or query.get('error'):fail('Google authorization was not completed.')
    c=configuration()
    if not c['ready']:fail('Google platform configuration is unavailable.',503)
    verifier=credential_vault.unseal(a['verifier'],tenant,kind)['verifier']
    tokens=request('https://oauth2.googleapis.com/token',data={'client_id':c['client_id'],'client_secret':c['secret'],'redirect_uri':c['redirect'],'grant_type':'authorization_code','code':code,'code_verifier':verifier},form=True)
    if not isinstance(tokens.get('access_token'),str) or not isinstance(tokens.get('refresh_token'),str) or not set(SCOPES[kind]).issubset(set(tokens.get('scope','').split())):fail('Google did not grant the required offline access. Reconnect and approve the requested permissions.')
    identity=request('https://openidconnect.googleapis.com/v1/userinfo',tokens['access_token'])
    if not identity.get('sub') or identity.get('email_verified') is not True:fail('Google could not verify the connected account.')
    with LOCK:
        admin(store,ctx)
        with store.db() as db:
            latest=store._get(db,tenant,'googleauth',row['id'])
            if latest.get('cancelled'):fail('This Google connection was cancelled. Start again.',409)
        vault.write_credentials(tenant,{'refresh_token':tokens['refresh_token'],'access_token':tokens['access_token'],'expires':int(time.time())+min(int(tokens.get('expires_in',3600)),3600),'email':identity.get('email',''),'account':identity['sub'],'generation':secrets.token_hex(16)},kind)
    return {'connected':True}


def credentials(tenant,kind):
    c=configuration()
    if not c['ready']:fail('Google platform setup is required.',503)
    with LOCK:
        saved=vault.read_credentials(tenant,kind)
        if not saved or saved.get('disconnected') or not saved.get('refresh_token'):fail('Connect your Google account first.',409)
        if saved.get('expires',0)<time.time()+60:
            tokens=request('https://oauth2.googleapis.com/token',data={'client_id':c['client_id'],'client_secret':c['secret'],'grant_type':'refresh_token','refresh_token':saved['refresh_token']},form=True)
            if not isinstance(tokens.get('access_token'),str):fail('Reconnect your Google account.',409)
            saved.update(access_token=tokens['access_token'],expires=int(time.time())+min(int(tokens.get('expires_in',3600)),3600));vault.write_credentials(tenant,saved,kind)
        return saved


def resource(value,label):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_@.\-]{1,200}',value):fail('Enter a valid '+label+'.')
    return value


def write_job(store,ctx,kind,saved,data,operation,payload,send):
    """Persist intent before a non-idempotent write; uncertain results cannot retry."""
    if data.get('confirm') is not True:fail('Confirm this Google write.')
    nonce=data.get('nonce')
    if not isinstance(nonce,str) or not re.fullmatch(r'[A-Za-z0-9-]{16,80}',nonce):fail('Reopen this action to generate a unique request.')
    tenant=ctx['tenant_id'];digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    identity=hashlib.sha256((saved['generation']+operation+nonce).encode()).hexdigest()
    with LOCK,store.db() as db:
        db.execute('BEGIN IMMEDIATE');admin(store,ctx)
        current=vault.read_credentials(tenant,kind)
        if not current or current.get('generation')!=saved['generation']:fail('Google connection changed. Reopen this action.',409)
        existing=next((j for j in store._list(db,tenant,'googlejob') if j['identity']==identity),None)
        if existing:
            if existing['digest']!=digest:fail('This request ID was already used for different data.',409)
            return existing
        if operation=='calendar.create':
            for j in store._list(db,tenant,'googlejob'):
                p=j.get('payload',{})
                if j['generation']==saved['generation'] and j['operation']=='calendar.create' and j['status'] in ('pending','unknown','confirmed') and p.get('calendar_id')==payload['calendar_id'] and payload['start']<p.get('end','') and payload['end']>p.get('start',''):fail('A booking already occupies this slot or awaits confirmation.',409)
        job=store._put(db,tenant,'googlejob',{'identity':identity,'digest':digest,'operation':operation,'generation':saved['generation'],'payload':payload,'status':'pending','created':int(time.time())})
    try:
        result=send(identity)
        # A successful response must identify the provider resource before success is recorded.
        if operation=='sheet.append' and not result.get('updates',{}).get('updatedRange'):fail('Google did not confirm the appended row.',502)
        if operation=='calendar.create' and result.get('id')!='b'+identity:fail('Google did not confirm the booking.',502)
    except Exception:
        with store.db() as db:store._put(db,tenant,'googlejob',dict(job,status='unknown',updated=int(time.time())),job['id'])
        fail('Google write outcome is unknown. Inspect the destination before creating another request.',502)
    with store.db() as db:return store._put(db,tenant,'googlejob',dict(job,status='confirmed',resource_id=result.get('id',''),updated=int(time.time())),job['id'])


def period(start,end):
    from datetime import datetime,timezone
    try:
        a=datetime.fromisoformat(start.replace('Z','+00:00'));b=datetime.fromisoformat(end.replace('Z','+00:00'))
        if a.tzinfo is None or b.tzinfo is None or not 0<(b-a).total_seconds()<=7*86400:raise ValueError()
        return a.astimezone(timezone.utc),b.astimezone(timezone.utc)
    except (AttributeError,ValueError,TypeError):fail('Use timezone-aware start/end times within seven days.')


def action(store,ctx,op,data):
    admin(store,ctx);kind=data.get('kind');tenant=ctx['tenant_id']
    if op=='google.start':return start(store,ctx,kind)
    if kind not in SCOPES:fail('Choose a Google service.')
    if op=='google.disconnect':
        with LOCK:
            admin(store,ctx)
            with store.db() as db:
                for attempt in store._list(db,tenant,'googleauth'):
                    if attempt['kind']==kind:store._put(db,tenant,'googleauth',dict(attempt,cancelled=True,used=True,verifier={}),attempt['id'])
            vault.write_credentials(tenant,{'disconnected':True},kind)
        return {'disconnected':True}
    saved=credentials(tenant,kind)
    if op=='google.sheet.append' and kind=='google_sheets':
        sheet=resource(data.get('spreadsheet_id'),'spreadsheet ID');area=data.get('range','A:C')
        if not isinstance(area,str) or not 1<=len(area)<=100:fail('Enter a sheet range.')
        with store.db() as db:contact=store._get(db,tenant,'contact',data.get('contact_id'))
        payload={'spreadsheet_id':sheet,'range':area,'contact_id':contact['id'],'name':contact['name'],'phone':contact['phone']}
        # RAW prevents spreadsheet formula execution from customer-controlled names.
        return write_job(store,ctx,kind,saved,data,'sheet.append',payload,lambda _:request('https://sheets.googleapis.com/v4/spreadsheets/'+sheet+'/values/'+quote(area,safe='')+':append?valueInputOption=RAW&insertDataOption=INSERT_ROWS',saved['access_token'],{'values':[[contact['name'],contact['phone'],'yes' if contact['optin'] else 'no']]}))
    if op=='google.calendar.create' and kind=='google_calendar':
        calendar=resource(data.get('calendar_id','primary'),'calendar ID');a,b=period(data.get('start'),data.get('end'))
        if a.timestamp()<time.time() or not 900<=(b-a).total_seconds()<=8*3600:fail('Choose a future booking of 15 minutes to eight hours.')
        with store.db() as db:contact=store._get(db,tenant,'contact',data.get('contact_id'))
        start=a.isoformat();end=b.isoformat()
        busy=request('https://www.googleapis.com/calendar/v3/freeBusy',saved['access_token'],{'timeMin':start,'timeMax':end,'items':[{'id':calendar}]}).get('calendars',{}).get(calendar,{})
        if busy.get('errors') or 'busy' not in busy:fail('Google could not confirm availability.',502)
        if busy['busy']:fail('This calendar is busy during the selected time.',409)
        payload={'calendar_id':calendar,'start':start,'end':end,'contact_id':contact['id']}
        return write_job(store,ctx,kind,saved,data,'calendar.create',payload,lambda identity:request('https://www.googleapis.com/calendar/v3/calendars/'+quote(calendar,safe='')+'/events?sendUpdates=none',saved['access_token'],{'id':'b'+identity,'summary':'VYBE appointment · '+contact['name'],'start':{'dateTime':start},'end':{'dateTime':end}}))
    if op in ('google.calendar.reconcile','google.calendar.cancel') and kind=='google_calendar':
        with store.db() as db:job=store._get(db,tenant,'googlejob',data.get('id'))
        if job['operation']!='calendar.create' or job['generation']!=saved['generation']:fail('This booking belongs to a different Google connection.',409)
        url='https://www.googleapis.com/calendar/v3/calendars/'+quote(job['payload']['calendar_id'],safe='')+'/events/b'+job['identity']
        if op.endswith('cancel'):
            if data.get('confirm') is not True or job['status']!='confirmed':fail('Confirm cancellation of a verified booking.')
            admin(store,ctx)
            request(url+'?sendUpdates=none',saved['access_token'],method='DELETE');status='cancelled'
        else:
            result=request(url,saved['access_token'])
            if result.get('id')!='b'+job['identity']:fail('Google did not confirm this booking.',502)
            status='cancelled' if result.get('status')=='cancelled' else 'confirmed'
        with store.db() as db:return store._put(db,tenant,'googlejob',dict(job,status=status,updated=int(time.time())),job['id'])
    if op=='google.sheet.read' and kind=='google_sheets':
        sheet=resource(data.get('spreadsheet_id'),'spreadsheet ID');area=data.get('range','A1:C201')
        if not isinstance(area,str) or not 1<=len(area)<=100:fail('Enter a sheet range.')
        result=request('https://sheets.googleapis.com/v4/spreadsheets/'+sheet+'/values/'+quote(area,safe='')+'?'+urlencode({'majorDimension':'ROWS'}),saved['access_token'])
        rows=result.get('values',[])
        if not isinstance(rows,list) or len(rows)>201:fail('Select a range with at most 200 contact rows and one header.')
        admin(store,ctx)
        if not data.get('import'):return {'rows':rows,'range':result.get('range',area)}
        if data.get('confirm') is not True:fail('Confirm the contact import.')
        if not rows or not all(isinstance(r,list) for r in rows):fail('The sheet is empty.')
        header=[str(x).strip().lower() for x in rows[0]]
        if 'name' not in header or 'phone' not in header:fail('The first row must contain name and phone columns.')
        from store import phone_number
        entries=[]
        for row in rows[1:]:
            if not any(str(v).strip() for v in row):continue
            try:name=str(row[header.index('name')]).strip();phone=phone_number(str(row[header.index('phone')]))
            except (IndexError,ValueError):fail('Each contact row needs a valid name and international phone number.')
            if not name or len(name)>100:fail('Contact names must contain 1–100 characters.')
            entries.append((name,phone))
        with LOCK,store.db() as db:
            db.execute('BEGIN IMMEDIATE');admin(store,ctx);current=vault.read_credentials(tenant,kind)
            if not current or current.get('generation')!=saved['generation']:fail('Google connection changed. Read the sheet again.',409)
            contacts={c['phone']:c for c in store._list(db,tenant,'contact')};created=0
            for name,phone in entries:
                if phone in contacts:continue
                contacts[phone]=store._contact(db,tenant,{'name':name,'phone':phone,'optin':False});created+=1
        return {'created':created,'skipped':len(entries)-created}
    if op=='google.calendar.availability' and kind=='google_calendar':
        calendar=resource(data.get('calendar_id','primary'),'calendar ID');start=data.get('start');end=data.get('end')
        period(start,end)
        result=request('https://www.googleapis.com/calendar/v3/freeBusy',saved['access_token'],{'timeMin':start,'timeMax':end,'items':[{'id':calendar}]})
        entry=result.get('calendars',{}).get(calendar,{})
        if entry.get('errors') or 'busy' not in entry:fail('Google could not read this calendar.',502)
        admin(store,ctx);return {'busy':entry['busy'],'start':start,'end':end}
    fail('Unsupported Google action.')
