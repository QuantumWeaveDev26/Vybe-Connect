"""Operator-only Meta webhook setup. Environment secrets never enter logs."""
import hashlib,hmac,json,os,re,secrets,urllib.request,urllib.error
from urllib.parse import urlencode,urlsplit

class SetupError(Exception):
    def __init__(self,stage,http_status=None,provider_code=None):
        self.stage=stage;self.http_status=http_status;self.provider_code=provider_code

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None

class MetaSetup:
    def __init__(self,tenant,app_id,environ=None):
        env=os.environ if environ is None else environ;p='TW_META_'+tenant.upper()+'_'
        self.tenant=tenant;self.app_id=app_id;self.token=env.get(p+'TOKEN','');self.secret=env.get(p+'APP_SECRET','');self.verify=env.get(p+'VERIFY_TOKEN','');self.version=env.get(p+'VERSION','');self.waba=env.get(p+'WABA_ID','')
        origin=env.get('TW_PUBLIC_ORIGIN','').rstrip('/');url=urlsplit(origin)
        if not all(re.fullmatch(r'\d+',v or '') for v in (app_id,self.waba)) or not re.fullmatch(r'[a-f0-9]{16}',tenant) or not re.fullmatch(r'v\d+\.\d+',self.version) or not self.token or not self.secret or not self.verify:raise SetupError('configuration')
        if url.scheme!='https' or not url.hostname or url.path or url.query or url.fragment or url.username or url.password:raise SetupError('callback_origin')
        self.callback=origin+'/webhook/'+tenant;self.app_token=app_id+'|'+self.secret
        self.base='https://graph.facebook.com/'+self.version+'/'
        self.opener=urllib.request.build_opener(NoRedirect)
    def graph(self,edge,stage,method='GET',data=None,query=None,app=False):
        if not re.fullmatch(r'(?:\d+(?:/(?:subscriptions|subscribed_apps))?|debug_token)',edge):raise SetupError('unsupported_operation')
        token=self.app_token if app else self.token;params=dict(query or {})
        params['appsecret_proof']=hmac.new(self.secret.encode(),token.encode(),hashlib.sha256).hexdigest()
        request=urllib.request.Request(self.base+edge+'?'+urlencode(params),method=method,data=urlencode(data).encode() if data is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/x-www-form-urlencoded'})
        try:
            with self.opener.open(request,timeout=25) as response:raw=response.read(1024*1024+1)
            if len(raw)>1024*1024:raise ValueError()
            result=json.loads(raw)
            if not isinstance(result,dict):raise ValueError()
            return result
        except urllib.error.HTTPError as error:
            code=None
            try:
                value=json.loads(error.read(65536)).get('error',{}).get('code')
                if type(value) is int:code=value
            except Exception:pass
            raise SetupError(stage,error.code,code) from None
        except (ValueError,OSError,urllib.error.URLError):raise SetupError(stage) from None
    def callback_check(self):
        challenge=secrets.token_hex(16)
        request=urllib.request.Request(self.callback+'?'+urlencode({'hub.mode':'subscribe','hub.verify_token':self.verify,'hub.challenge':challenge}))
        try:
            with self.opener.open(request,timeout=20) as response:body=response.read(256).decode()
            if body!=challenge:raise SetupError('callback_challenge')
        except Exception:raise SetupError('callback_challenge') from None
    @staticmethod
    def subscription(data):
        rows=data.get('data')
        if not isinstance(rows,list) or data.get('paging',{}).get('next'):raise SetupError('subscription_shape')
        return next((r for r in rows if isinstance(r,dict) and r.get('object')=='whatsapp_business_account'),None)
    @staticmethod
    def app_ids(data):
        rows=data.get('data')
        if not isinstance(rows,list) or data.get('paging',{}).get('next'):raise SetupError('waba_subscription_shape')
        return {str(r.get('whatsapp_business_api_data',{}).get('id')) for r in rows if isinstance(r,dict)}
    def run(self,apply=False):
        debug=self.graph('debug_token','token_debug',query={'input_token':self.token},app=True).get('data',{})
        if debug.get('is_valid') is not True or str(debug.get('app_id'))!=self.app_id:raise SetupError('token_app_mismatch')
        required={'whatsapp_business_management','whatsapp_business_messaging'}
        if not required.issubset(set(debug.get('scopes',[]))):raise SetupError('token_permissions')
        existing=self.subscription(self.graph(self.app_id+'/subscriptions','app_subscription_read',app=True))
        if existing and existing.get('callback_url') not in (None,'',self.callback):raise SetupError('existing_callback_conflict')
        before=self.graph(self.waba+'/subscribed_apps','waba_subscription_read');before_ids=self.app_ids(before)
        for row in before['data']:
            if str(row.get('whatsapp_business_api_data',{}).get('id'))==self.app_id and row.get('override_callback_uri') not in (None,'',self.callback):raise SetupError('existing_override_conflict')
        fields={f.get('name') if isinstance(f,dict) else f for f in (existing or {}).get('fields',[])};fields.discard(None);fields.add('messages')
        if any(not isinstance(f,str) or not re.fullmatch(r'[a-z_]+',f) for f in fields):raise SetupError('existing_field_shape')
        self.callback_check()
        result={'callback_challenge_passed':True,'token_app_matched':True,'required_permissions_present':True,'token_expires_at':debug.get('expires_at') if type(debug.get('expires_at')) is int else None,'existing_waba_subscription':self.app_id in before_ids,'applied':False}
        if not apply:return result
        if not existing or existing.get('active') is not True or existing.get('callback_url')!=self.callback or 'messages' not in {f.get('name') if isinstance(f,dict) else f for f in existing.get('fields',[])}:
            response=self.graph(self.app_id+'/subscriptions','app_subscription_write','POST',{'object':'whatsapp_business_account','callback_url':self.callback,'verify_token':self.verify,'fields':','.join(sorted(fields))},app=True)
            if response.get('success') is not True:raise SetupError('app_subscription_write_unconfirmed')
        if self.app_id not in before_ids:
            response=self.graph(self.waba+'/subscribed_apps','waba_subscription_write','POST',{})
            if response.get('success') is not True:raise SetupError('waba_subscription_write_unconfirmed')
        current=self.subscription(self.graph(self.app_id+'/subscriptions','app_subscription_readback',app=True))
        ids=self.app_ids(self.graph(self.waba+'/subscribed_apps','waba_subscription_readback'))
        names={f.get('name') if isinstance(f,dict) else f for f in (current or {}).get('fields',[])}
        if not current or current.get('callback_url')!=self.callback or current.get('active') is not True or not fields.issubset(names) or self.app_id not in ids or not before_ids.issubset(ids):raise SetupError('setup_readback_unconfirmed')
        return dict(result,applied=True,callback_active=True,messages_subscribed=True,waba_subscribed=True,other_subscriptions_preserved=True)

def main():
    try:
        setup=MetaSetup(os.environ.get('META_SETUP_TENANT',''),os.environ.get('META_SETUP_APP_ID',''))
        result=setup.run(os.environ.get('META_SETUP_APPLY','false').lower()=='true')
        print('META_SETUP_RESULT '+json.dumps(result),flush=True)
    except SetupError as e:print('META_SETUP_RESULT '+json.dumps({'success':False,'stage':e.stage,'http_status':e.http_status,'provider_code':e.provider_code}),flush=True)
    except Exception:print('META_SETUP_RESULT '+json.dumps({'success':False,'stage':'unexpected_error'}),flush=True)
if __name__=='__main__':main()
