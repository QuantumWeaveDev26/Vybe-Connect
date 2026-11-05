"""Official Cloud API adapter. Credentials stay in the server environment."""
import hashlib
import hmac
import json
import os
import re
import urllib.request
import urllib.error
from urllib.parse import urlencode, urlsplit


def signature_ok(raw, signature, secret):
    return bool(secret and signature and hmac.compare_digest('sha256=' + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest(), signature))


def settings(tenant):
    from embedded_signup import credential_settings
    saved=credential_settings(tenant)
    if saved is not None:return saved
    prefix = 'TW_META_' + tenant.upper() + '_'
    return {k: os.environ.get(prefix+k, '') for k in ['TOKEN','PHONE_ID','WABA_ID','APP_SECRET','VERIFY_TOKEN','VERSION','LIVE']}


def status(tenant):
    s = settings(tenant)
    required = ['TOKEN','PHONE_ID','WABA_ID','APP_SECRET','VERIFY_TOKEN','VERSION']
    formats = {
        'PHONE_ID': (r'\d+', 'Use the numeric Phone Number ID, not the telephone number.'),
        'WABA_ID': (r'\d+', 'Use the numeric WhatsApp Business Account ID.'),
        'APP_SECRET': (r'[a-fA-F0-9]{32}', 'Copy the App Secret from Meta App settings > Basic.'),
        'VERSION': (r'v\d+\.\d+', 'Use only the Graph API version, for example v25.0, without a URL.')
    }
    invalid = {k:message for k,(pattern,message) in formats.items() if s[k] and not re.fullmatch(pattern,s[k])}
    return {'live': s['LIVE'].lower() == 'true', 'configured': all(s[k] for k in required) and not invalid, 'present': {k:bool(s[k]) for k in required}, 'invalid':invalid, 'prefix':'TW_META_'+tenant.upper()+'_'}


def send_text(tenant, phone, body):
    s=settings(tenant)
    if s['LIVE'].lower()!='true': raise ValueError('Live sending is disabled in the server environment.')
    if not s['TOKEN'] or not re.fullmatch(r'\d+',s['PHONE_ID']) or not re.fullmatch(r'v\d+\.\d+',s['VERSION']):
        raise ValueError('Configure TOKEN, PHONE_ID and VERSION on the server first.')
    payload={'messaging_product':'whatsapp','to':phone,'type':'text','text':{'body':body}}
    req=urllib.request.Request('https://graph.facebook.com/'+s['VERSION']+'/'+s['PHONE_ID']+'/messages',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+s['TOKEN'],'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=20) as response:
        result=json.load(response)
    return result['messages'][0]['id']


class ProviderError(Exception):
    def __init__(self,message,definitive=False):
        super().__init__(message);self.definitive=definitive


def graph_request(tenant,object_id,edge,method='GET',payload=None,query=None):
    s=settings(tenant)
    if not s['TOKEN'] or not re.fullmatch(r'\d+',object_id or '') or not re.fullmatch(r'v\d+\.\d+',s['VERSION']): raise ProviderError('Configure the Meta token, numeric account ID and Graph API version first.',True)
    url='https://graph.facebook.com/'+s['VERSION']+'/'+object_id+'/'+edge
    if query:url+='?'+urlencode(query)
    request=urllib.request.Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers={'Authorization':'Bearer '+s['TOKEN'],'Content-Type':'application/json'},method=method)
    try:
        with urllib.request.urlopen(request,timeout=25) as response:return json.load(response)
    except urllib.error.HTTPError as e:
        # Return provider error metadata without copying headers, tokens or customer payloads.
        try: data=json.loads(e.read(65536)); code=data.get('error',{}).get('code','unknown')
        except Exception:code='unknown'
        raise ProviderError('Meta rejected the request (HTTP '+str(e.code)+', code '+str(code)+').',400<=e.code<500) from None
    except (TimeoutError,urllib.error.URLError):raise ProviderError('The provider result is uncertain. Check Meta before retrying.') from None


def list_templates(tenant):
    s=settings(tenant)
    return graph_request(tenant,s['WABA_ID'],'message_templates',query={'fields':'id,name,status,category,language,components','limit':100})


def rich_text_fields(template):
    result={}
    for key in ['header','footer']:
        value=template.get(key,'')
        if not isinstance(value,str) or len(value)>60 or '{{' in value:raise ValueError(key.title()+' supports up to 60 characters without variables in this editor.')
        result[key]=value.strip()
    buttons=template.get('buttons',[])
    if not isinstance(buttons,list) or len(buttons)>3:raise ValueError('This editor supports up to three static action buttons.')
    clean=[]
    for button in buttons:
        if not isinstance(button,dict):raise ValueError('Each action button must be an object.')
        kind=button.get('type');text=button.get('text')
        if kind not in ['QUICK_REPLY','URL','PHONE_NUMBER'] or not isinstance(text,str) or not text.strip() or len(text)>25:raise ValueError('Use a supported button type and 1–25 characters of button text.')
        entry={'type':kind,'text':text.strip()}
        if kind=='URL':
            value=button.get('url','');url=urlsplit(value)
            if url.scheme!='https' or not url.hostname or url.username or url.password or '{{' in value or len(value)>2000:raise ValueError('Website buttons require a static HTTPS URL with no credentials.')
            entry['url']=value
        if kind=='PHONE_NUMBER':
            value=button.get('phone_number','')
            if not isinstance(value,str) or not re.fullmatch(r'\+[1-9]\d{6,14}',value):raise ValueError('Phone buttons require an international +country-code number.')
            entry['phone_number']=value
        clean.append(entry)
    result['buttons']=clean
    return result


def submit_template(tenant,template):
    try:rich=rich_text_fields(template)
    except ValueError as e:raise ProviderError(str(e),True)
    body=template['body'].replace('{{name}}','{{1}}')
    variables=re.findall(r'\{\{(.*?)\}\}',body)
    if any(v!='1' for v in variables):raise ProviderError('This editor currently supports only {{name}} or {{1}} as the body variable.',True)
    if template['category']=='AUTHENTICATION':raise ProviderError('Authentication templates require the OTP template editor, which is not implemented yet.',True)
    if len(body)>1024:raise ProviderError('Template body must be at most 1,024 characters.',True)
    component={'type':'BODY','text':body}
    if variables:component['example']={'body_text':[['Customer']]}
    components=[]
    if rich['header']:components.append({'type':'HEADER','format':'TEXT','text':rich['header']})
    components.append(component)
    if rich['footer']:components.append({'type':'FOOTER','text':rich['footer']})
    if rich['buttons']:components.append({'type':'BUTTONS','buttons':rich['buttons']})
    return graph_request(tenant,settings(tenant)['WABA_ID'],'message_templates','POST',{'name':template['name'],'language':template['language'],'category':template['category'],'components':components})


def send_template(tenant,phone,template,name):
    if template.get('category')=='AUTHENTICATION':raise ProviderError('Authentication templates require a dedicated OTP sender; campaign name personalization is not an OTP code.',True)
    if settings(tenant)['LIVE'].lower()!='true':raise ProviderError('Live sending is disabled.',True)
    components=template.get('components',[])
    for component in components:
        if component.get('type')=='CAROUSEL' or component.get('type')=='HEADER' and (component.get('format')!='TEXT' or '{{' in component.get('text','')):raise ProviderError('This sender does not yet support media headers, dynamic headers or carousels.',True)
        if component.get('type')=='BUTTONS' and any('{{' in str(b.get('url','')) for b in component.get('buttons',[])):raise ProviderError('Dynamic URL button parameters are not yet supported.',True)
    body=template.get('body','')
    variables=set(re.findall(r'\{\{\s*(.*?)\s*\}\}',body))
    if variables-{'1','name'}:raise ProviderError('This template needs unsupported body variables.',True)
    message={'name':template['name'],'language':{'code':template['language']}}
    if variables:message['components']=[{'type':'body','parameters':[{'type':'text','text':name}]}]
    result=graph_request(tenant,settings(tenant)['PHONE_ID'],'messages','POST',{'messaging_product':'whatsapp','to':phone,'type':'template','template':message})
    return result['messages'][0]['id']
