"""Workspace-bound WhatsApp authorization. No messaging or paid verification calls.

Access tokens live in private server files, not entity JSON or public API state.
These files require encrypted host storage/backups for encryption at rest.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit
import urllib.request
import urllib.error


class ConnectionError(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def configuration():
    p = 'TW_META_PLATFORM_'
    values = {k: os.environ.get(p+k, '') for k in ('APP_ID','APP_SECRET','CONFIG_ID','VERSION','VERIFY_TOKEN')}
    origin = os.environ.get('TW_PUBLIC_ORIGIN','').rstrip('/')
    parsed = urlsplit(origin)
    valid = (all(re.fullmatch(r'\d+', values[k]) for k in ('APP_ID','CONFIG_ID'))
             and re.fullmatch(r'[a-fA-F0-9]{32}',values['APP_SECRET'])
             and re.fullmatch(r'v\d+\.\d+',values['VERSION'])
             and 32 <= len(values['VERIFY_TOKEN']) <= 256
             and parsed.scheme == 'https' and parsed.hostname and not parsed.path
             and not parsed.query and not parsed.fragment and not parsed.username and not parsed.password)
    values.update(origin=origin, ready=bool(valid and os.environ.get(p+'ENABLED','false').lower()=='true'))
    return values


def credential_path(tenant):
    if not re.fullmatch(r'[a-f0-9]{16}',tenant or ''):
        raise ConnectionError('Invalid workspace.',403)
    root = Path(os.environ.get('TW_DATA_DIR',str(Path(__file__).parent/'data')))/'meta-credentials'
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    if root.is_symlink(): raise ConnectionError('Credential storage is unavailable.',503)
    if os.name != 'nt': root.chmod(0o700)
    return root/(tenant+'.json')


def read_credentials(tenant):
    path=credential_path(tenant)
    if not path.exists():return None
    if path.is_symlink():raise ConnectionError('Credential storage is unavailable.',503)
    if os.name != 'nt' and path.stat().st_mode & 0o077:
        raise ConnectionError('Credential file permissions are unsafe.',503)
    try:
        result=json.loads(path.read_text())
        if not isinstance(result,dict) or result.get('tenant')!=tenant:raise ValueError()
        return result
    except (ValueError,OSError):raise ConnectionError('Credential storage is unavailable.',503) from None


def write_credentials(tenant,values):
    path=credential_path(tenant);tmp=path.with_name(tenant+'.'+secrets.token_hex(8)+'.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(dict(values,tenant=tenant),stream);stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()


def credential_settings(tenant):
    # Ignore non-workspace legacy identifiers used by local adapter contracts.
    if not re.fullmatch(r'[a-f0-9]{16}',tenant or ''):return None
    saved=read_credentials(tenant)
    if saved is None:return None
    c=configuration();keys=('TOKEN','PHONE_ID','WABA_ID','APP_SECRET','VERIFY_TOKEN','VERSION','LIVE')
    if saved.get('disconnected'):return {k:'' for k in keys}
    result={k:saved.get(k,'') for k in keys}
    result.update(APP_SECRET=c['APP_SECRET'],VERIFY_TOKEN=c['VERIFY_TOKEN'])
    expires=saved.get('expires_at',0)
    if expires and expires<=int(time.time()):result['LIVE']='false'
    return result


def initialize(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS whatsapp_auth_attempts (
        state TEXT PRIMARY KEY,tenant TEXT,user TEXT,session TEXT,expires INTEGER,used INTEGER DEFAULT 0);
      CREATE TABLE IF NOT EXISTS whatsapp_connections (
        tenant TEXT PRIMARY KEY,waba TEXT UNIQUE,phone TEXT UNIQUE,status TEXT,
        display_phone TEXT,display_name TEXT,expires INTEGER,updated INTEGER);
    ''')


def administrator(store,ctx):
    if ctx.get('role')!='admin' or not ctx.get('_session_hash'):
        raise ConnectionError('Workspace administrator access required.',403)
    with store.db() as db:
        row=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(ctx['tenant_id'],ctx['user']['id'])).fetchone()
        session=db.execute('SELECT 1 FROM sessions WHERE token=? AND user=? AND expires>?',(ctx['_session_hash'],ctx['user']['id'],int(time.time()))).fetchone()
        if not row or row['role']!='admin' or not session:
            raise ConnectionError('Sign in again as a workspace administrator.',403)


def state(store,ctx):
    c=configuration()
    with store.db() as db:
        row=db.execute('SELECT status,display_phone,display_name,expires,updated FROM whatsapp_connections WHERE tenant=?',(ctx['tenant_id'],)).fetchone()
    result=dict(row) if row else {'status':'not_connected'}
    if result['status'].startswith('connecting:'):result['status']='connecting'
    if result.get('expires') and result['expires']<=int(time.time()):result['status']='expired'
    result['signup_available']=c['ready'];result['can_manage']=ctx.get('role')=='admin'
    if row and row['status']=='connected':
        saved=read_credentials(ctx['tenant_id'])
        result['sending_enabled']=bool(saved and saved.get('LIVE')=='true' and result['status']!='expired')
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def graph(c,edge,token='',payload=None,query=None):
    if not re.fullmatch(r'(?:oauth/access_token|debug_token|\d+(?:/(?:phone_numbers|subscribed_apps))?)',edge):
        raise ConnectionError('Unsupported Meta operation.')
    params=dict(query or {})
    if token:params['appsecret_proof']=hmac.new(c['APP_SECRET'].encode(),token.encode(),hashlib.sha256).hexdigest()
    headers={'Content-Type':'application/x-www-form-urlencoded'}
    if token:headers['Authorization']='Bearer '+token
    url='https://graph.facebook.com/'+c['VERSION']+'/'+edge
    if params:url+='?'+urlencode(params)
    request=urllib.request.Request(url,data=urlencode(payload).encode() if payload is not None else None,headers=headers,method='POST' if payload is not None else 'GET')
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=25) as response:
            raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError()
        result=json.loads(raw)
        if not isinstance(result,dict) or 'error' in result:raise ValueError()
        return result
    except urllib.error.HTTPError as error:
        raise ConnectionError('Meta rejected the connection (HTTP '+str(error.code)+'). Check account access and app approval, then reconnect.',502) from None
    except (OSError,ValueError,urllib.error.URLError):
        raise ConnectionError('Meta connection could not be confirmed. Reconnect to check again.',502) from None


def begin(store,ctx):
    administrator(store,ctx);c=configuration()
    if not c['ready']:raise ConnectionError('Customer WhatsApp signup is not configured by the platform operator yet.',503)
    token=secrets.token_urlsafe(32);timestamp=int(time.time())
    with store.db() as db:
        db.execute('DELETE FROM whatsapp_auth_attempts WHERE expires<?',(timestamp,))
        db.execute('UPDATE whatsapp_auth_attempts SET used=1 WHERE tenant=? AND user=?',(ctx['tenant_id'],ctx['user']['id']))
        db.execute('INSERT INTO whatsapp_auth_attempts VALUES(?,?,?,?,?,0)',(hashlib.sha256(token.encode()).hexdigest(),ctx['tenant_id'],ctx['user']['id'],ctx['_session_hash'],timestamp+600))
    return {'state':token,'app_id':c['APP_ID'],'config_id':c['CONFIG_ID'],'version':c['VERSION'],'expires':timestamp+600}


def finish(store,ctx,data):
    administrator(store,ctx);c=configuration()
    if not c['ready']:raise ConnectionError('Customer signup is unavailable.',503)
    for key,pattern,limit in [('state',r'[A-Za-z0-9_-]+',128),('code',r'[^\s\x00-\x1f]+',4096),('waba_id',r'\d+',30),('phone_number_id',r'\d+',30)]:
        if not isinstance(data.get(key),str) or len(data[key])>limit or not re.fullmatch(pattern,data[key]):raise ConnectionError('Complete the Meta signup window before connecting.')
    tenant=ctx['tenant_id'];waba=data['waba_id'];phone=data['phone_number_id'];timestamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        count=db.execute('UPDATE whatsapp_auth_attempts SET used=1 WHERE state=? AND tenant=? AND user=? AND session=? AND used=0 AND expires>?',(hashlib.sha256(data['state'].encode()).hexdigest(),tenant,ctx['user']['id'],ctx['_session_hash'],timestamp)).rowcount
        if count!=1:raise ConnectionError('Signup expired or was already used. Start a new connection.',409)
    # Codes are one-time; do not retry an uncertain exchange with the same code.
    exchange=graph(c,'oauth/access_token',payload={'client_id':c['APP_ID'],'client_secret':c['APP_SECRET'],'code':data['code']})
    token=exchange.get('access_token')
    if not isinstance(token,str) or not 20<=len(token)<=8192:raise ConnectionError('Meta did not return a valid access token.',502)
    debug=graph(c,'debug_token',token=c['APP_ID']+'|'+c['APP_SECRET'],query={'input_token':token}).get('data',{})
    if debug.get('is_valid') is not True or str(debug.get('app_id'))!=c['APP_ID'] or not {'whatsapp_business_management','whatsapp_business_messaging'}.issubset(set(debug.get('scopes',[]))):
        raise ConnectionError('Meta authorization is missing required WhatsApp access.',403)
    expirations=[debug.get('expires_at',0),debug.get('data_access_expires_at',0)]
    if any(type(e) is not int or e<0 for e in expirations):raise ConnectionError('Meta returned an invalid authorization expiry.',502)
    expires=min((e for e in expirations if e),default=0)
    if type(expires) is not int or expires<0 or expires and expires<=timestamp:raise ConnectionError('Meta authorization has expired.',403)
    phones=graph(c,waba+'/phone_numbers',token=token,query={'fields':'id,display_phone_number,verified_name','limit':100})
    selected=next((p for p in phones.get('data',[]) if str(p.get('id'))==phone),None)
    if not selected:raise ConnectionError('The authorized number does not belong to this WhatsApp account.',403)
    for key,value in os.environ.items():
        match=re.fullmatch(r'TW_META_([A-F0-9]{16})_(WABA_ID|PHONE_ID)',key)
        if match and match[1].lower()!=tenant and value==(waba if match[2]=='WABA_ID' else phone):
            raise ConnectionError('This account belongs to an existing operator-managed workspace.',409)
    # Reserve unique account/number bindings before changing webhook delivery.
    # Provider requests must not hold SQLite's global writer lock.
    reservation='connecting:'+secrets.token_hex(16)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        conflict=db.execute('SELECT tenant FROM whatsapp_connections WHERE (waba=? OR phone=?) AND tenant<>?',(waba,phone,tenant)).fetchone()
        if conflict:raise ConnectionError('This WhatsApp account is already connected to another workspace.',409)
        existing=db.execute('SELECT waba,phone,status,updated FROM whatsapp_connections WHERE tenant=?',(tenant,)).fetchone()
        if existing and existing['status'].startswith('connecting:') and existing['updated']>timestamp-300:
            raise ConnectionError('A connection is already being verified. Wait before trying again.',409)
        if existing and existing['status']!='disconnected' and (existing['waba']!=waba or existing['phone']!=phone):
            raise ConnectionError('Disconnect the current WhatsApp account before changing numbers.',409)
        # Pause existing credentials during reconnection; never re-enable old sending.
        old=read_credentials(tenant)
        if old and not old.get('disconnected'):
            old['LIVE']='false';write_credentials(tenant,old)
        db.execute('INSERT INTO whatsapp_connections VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(tenant) DO UPDATE SET waba=excluded.waba,phone=excluded.phone,status=excluded.status,updated=excluded.updated',(tenant,waba,phone,reservation,'','',expires,timestamp))
    try:
        callback=c['origin']+'/webhook/'+tenant
        response=graph(c,waba+'/subscribed_apps',token=token,payload={'override_callback_uri':callback,'verify_token':c['VERIFY_TOKEN']})
        if response.get('success') is not True:raise ConnectionError('Meta did not confirm the webhook subscription.',502)
        subscriptions=graph(c,waba+'/subscribed_apps',token=token)
        subscribed=next((s for s in subscriptions.get('data',[]) if str(s.get('whatsapp_business_api_data',{}).get('id'))==c['APP_ID']),None)
        if not subscribed or subscribed.get('override_callback_uri')!=callback:
            raise ConnectionError('Webhook callback verification is incomplete. Reconnect before using this number.',502)
    except Exception:
        with store.db() as db:
            db.execute("UPDATE whatsapp_connections SET status='needs_reconnect' WHERE tenant=? AND status=?",(tenant,reservation))
        raise
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        current=db.execute('SELECT status FROM whatsapp_connections WHERE tenant=?',(tenant,)).fetchone()
        if not current or current['status']!=reservation:raise ConnectionError('Connection was cancelled. Start again if needed.',409)
        # Session or admin membership may have been revoked during provider requests.
        row=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(tenant,ctx['user']['id'])).fetchone()
        session=db.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?',(ctx['_session_hash'],int(time.time()))).fetchone()
        if not row or row['role']!='admin' or not session:raise ConnectionError('Sign in again before connecting.',403)
        saved={'TOKEN':token,'PHONE_ID':phone,'WABA_ID':waba,'VERSION':c['VERSION'],'LIVE':'false','expires_at':expires}
        write_credentials(tenant,saved)
        db.execute('INSERT INTO whatsapp_connections VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(tenant) DO UPDATE SET waba=excluded.waba,phone=excluded.phone,status=excluded.status,display_phone=excluded.display_phone,display_name=excluded.display_name,expires=excluded.expires,updated=excluded.updated',(tenant,waba,phone,'connected',str(selected.get('display_phone_number',''))[:100],str(selected.get('verified_name',''))[:200],expires,timestamp))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],'whatsapp.connected',timestamp))
    return state(store,ctx)


def action(store,ctx,operation,data):
    administrator(store,ctx)
    if operation=='whatsapp.begin':return begin(store,ctx)
    if operation=='whatsapp.finish':return finish(store,ctx,data)
    if operation not in ('whatsapp.disconnect','whatsapp.sending'):raise ConnectionError('Unknown WhatsApp connection action.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM whatsapp_connections WHERE tenant=?',(ctx['tenant_id'],)).fetchone()
        if not row:raise ConnectionError('No customer connection exists in this workspace.',404)
        saved=read_credentials(ctx['tenant_id'])
        if operation=='whatsapp.disconnect':
            write_credentials(ctx['tenant_id'],{'disconnected':True})
            db.execute("UPDATE whatsapp_connections SET waba=NULL,phone=NULL,status='disconnected',updated=? WHERE tenant=?",(int(time.time()),ctx['tenant_id']))
            db.execute('UPDATE whatsapp_auth_attempts SET used=1 WHERE tenant=?',(ctx['tenant_id'],))
        else:
            if type(data.get('enabled')) is not bool:raise ConnectionError('Choose whether sending is enabled.')
            if not saved or saved.get('disconnected') or row['status']!='connected' or row['expires'] and row['expires']<=int(time.time()):raise ConnectionError('Reconnect WhatsApp before enabling sending.',409)
            saved['LIVE']='true' if data['enabled'] else 'false';write_credentials(ctx['tenant_id'],saved)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(ctx['tenant_id'],ctx['user']['name'],operation,int(time.time())))
    return state(store,ctx)
