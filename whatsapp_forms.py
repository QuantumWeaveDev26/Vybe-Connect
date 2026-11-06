"""Static WhatsApp forms, official management endpoints and explicit live sending."""
import json
import re
import secrets
import time
import urllib.request
import urllib.error
from growth_services import text,admin,member
import meta


def definition(data):
    from store import Problem
    title=text(data.get('title'),'form title',30);fields=data.get('fields')
    if not isinstance(fields,list) or not 1<=len(fields)<=8:raise Problem('Add one to eight questions.')
    clean=[];children=[]
    for i,f in enumerate(fields):
        if not isinstance(f,dict):raise Problem('Use a question object.')
        label=text(f.get('label'),'question label',50);kind=f.get('type','text');key='question_'+str(i+1)
        if kind not in ('text','email','phone','choice'):raise Problem('Choose text, email, phone or choice.')
        required=f.get('required') is True;entry={'label':label,'type':kind,'required':required}
        if kind=='choice':
            options=f.get('options')
            if not isinstance(options,list) or not 2<=len(options)<=10:raise Problem('Choice questions need two to ten options.')
            entry['options']=[text(o,'option',30) for o in options]
            if len(set(entry['options']))!=len(options):raise Problem('Use distinct choices.')
            component={'type':'Dropdown','name':key,'label':label,'required':required,'data-source':[{'id':str(j),'title':v} for j,v in enumerate(entry['options'])]}
        else:component={'type':'TextInput','name':key,'label':label,'required':required,'input-type':kind,'max-chars':200}
        clean.append(entry);children.append(component)
    children.append({'type':'Footer','label':'Submit','on-click-action':{'name':'complete','payload':{'question_'+str(i+1):'${form.question_'+str(i+1)+'}' for i in range(len(clean))}}})
    return title,clean,{'version':'7.3','screens':[{'id':'DETAILS','title':title,'terminal':True,'success':True,'data':{},'layout':{'type':'SingleColumnLayout','children':[{'type':'Form','name':'form','children':children}]}}]}


def upload(tenant,flow_id,definition):
    settings=meta.settings(tenant);boundary='vybe'+secrets.token_hex(16)
    parts=[('--'+boundary+'\r\nContent-Disposition: form-data; name="name"\r\n\r\nflow.json\r\n').encode(),('--'+boundary+'\r\nContent-Disposition: form-data; name="asset_type"\r\n\r\nFLOW_JSON\r\n').encode(),('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="flow.json"\r\nContent-Type: application/json\r\n\r\n').encode(),json.dumps(definition).encode(),('\r\n--'+boundary+'--\r\n').encode()]
    request=urllib.request.Request('https://graph.facebook.com/'+settings['VERSION']+'/'+flow_id+'/assets',data=b''.join(parts),headers={'Authorization':'Bearer '+settings['TOKEN'],'Content-Type':'multipart/form-data; boundary='+boundary},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=25) as response:return json.load(response)
    except urllib.error.HTTPError as e:raise meta.ProviderError('Meta rejected the form definition (HTTP '+str(e.code)+').',True) from None
    except (OSError,ValueError):raise meta.ProviderError('Form upload result uncertain. Sync with Meta before retrying.') from None


def action(store,ctx,op,data):
    from store import Problem
    tenant=ctx['tenant_id'];op=op.removeprefix('growth.form.');stamp=int(time.time())
    if op=='save':
        title,fields,flow_json=definition(data)
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE');admin(store,db,ctx)
            old=store._get(db,tenant,'whatsappform',data['id']) if data.get('id') else {}
            if not old and len(store._list(db,tenant,'whatsappform'))>=100:raise Problem('Use up to 100 form definitions per workspace.')
            if old.get('meta_id') or old.get('operation'):raise Problem('Remote forms are immutable here. Create a new draft.',409)
            return store._put(db,tenant,'whatsappform',dict(title=title,fields=fields,definition=flow_json,status='local_draft',updated=stamp),old.get('id'))
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');admin(store,db,ctx)
        form=store._get(db,tenant,'whatsappform',data.get('id'))
        if op=='export':return form['definition']
        if op not in ('create','upload','publish','sync','send','adopt'):raise Problem('Unknown form operation.')
        if data.get('confirm') is not True:raise Problem('Confirm the Meta request before continuing.')
        if not meta.status(tenant)['configured']:raise Problem('Connect WhatsApp first.')
        if form.get('operation'):
            if op not in ('sync','adopt'):raise Problem('The previous result needs reconciliation. Sync first; do not retry blindly.',409)
            if not form.get('last_error') and stamp-form.get('operation_started',stamp)<90:raise Problem('A Meta request is still running. Wait for it to finish before syncing.',409)
        if op=='create' and form.get('meta_id'):raise Problem('This form already has a Meta ID.')
        if op=='adopt':
            if form.get('meta_id'):raise Problem('This form already has a Meta ID.')
            remote=text(data.get('meta_id'),'Meta draft form ID',50)
            if not re.fullmatch(r'\d+',remote):raise Problem('Use the numeric draft form ID from Meta.')
            if any(f.get('meta_id')==remote for f in store._list(db,tenant,'whatsappform')):raise Problem('This Meta form is already linked in this workspace.',409)
        if op not in ('create','adopt') and not re.fullmatch(r'\d+',form.get('meta_id','')):raise Problem('Create this form on Meta first.')
        if op=='upload' and form.get('status')=='PUBLISHED':raise Problem('Published forms cannot be edited.')
        if op=='publish' and (not form.get('uploaded') or form.get('validation_errors')):raise Problem('Upload a valid definition before publishing.')
        if op=='send':
            c=store._get(db,tenant,'contact',data.get('contact_id'))
            if form.get('status')!='PUBLISHED' or not meta.status(tenant)['live']:raise Problem('A published form and enabled live sending are required.')
            if not c.get('last_real_inbound') or not 0<=stamp-c['last_real_inbound']<86400 or c.get('automation_hold'):raise Problem('An active customer service window without an automation hold is required.')
            if any(r.get('form_id')==form['id'] and r.get('contact_id')==c['id'] and r.get('status') in ('submitting','unknown') for r in store._list(db,tenant,'formsend')):raise Problem('An earlier form send has an unknown result. Check Meta before sending again; syncing publication status does not reconcile message delivery.',409)
            nonce=text(data.get('nonce'),'request ID',80)
            if any(r.get('nonce')==nonce for r in store._list(db,tenant,'formsend')):raise Problem('This request has already been recorded. Check history.',409)
            dispatch=store._put(db,tenant,'formsend',dict(form_id=form['id'],contact_id=c['id'],nonce=nonce,flow_token=secrets.token_urlsafe(32),created=stamp,status='submitting'))
        marker=secrets.token_hex(16)
        store._put(db,tenant,'whatsappform',dict(form,operation=marker,operation_started=stamp,operation_kind=op,last_error=''),form['id'])
    try:
        settings=meta.settings(tenant)
        if op=='create':
            result=meta.graph_request(tenant,settings['WABA_ID'],'flows','POST',{'name':form['title'],'categories':['LEAD_GENERATION']})
            remote=str(result.get('id',''))
            if not re.fullmatch(r'\d+',remote):raise meta.ProviderError('Meta returned no valid form ID.')
            changes={'meta_id':remote,'status':'DRAFT'}
        elif op=='adopt':
            result=meta.graph_request(tenant,remote,'',query={'fields':'id,name,status,whatsapp_business_account'})
            account=result.get('whatsapp_business_account',{})
            if str(result.get('id'))!=remote or not isinstance(account,dict) or str(account.get('id'))!=settings['WABA_ID'] or result.get('name')!=form['title'] or result.get('status')!='DRAFT':raise meta.ProviderError('Choose an unpublished draft with the same name in the connected WhatsApp account.',True)
            changes={'meta_id':remote,'status':'DRAFT','uploaded':False,'validation_errors':[]}
        elif op=='upload':
            result=upload(tenant,form['meta_id'],form['definition']);errors=result.get('validation_errors',[])
            if not isinstance(errors,list):raise meta.ProviderError('Unexpected Meta validation response.')
            changes={'uploaded':result.get('success') is True and not errors,'validation_errors':errors[:20]}
        elif op=='publish':
            result=meta.graph_request(tenant,form['meta_id'],'publish','POST',{})
            if result.get('success') is not True:raise meta.ProviderError('Meta did not confirm publication.')
            changes={'status':'PUBLISHED'}
        elif op=='sync':
            result=meta.graph_request(tenant,form['meta_id'],'',query={'fields':'id,status,validation_errors'})
            if str(result.get('id'))!=form['meta_id'] or result.get('status') not in ('DRAFT','PUBLISHED','DEPRECATED','BLOCKED'):raise meta.ProviderError('Unexpected Meta form status.')
            changes={'status':result['status'],'validation_errors':result.get('validation_errors',[])[:20]}
        else:
            payload={'messaging_product':'whatsapp','to':c['phone'],'type':'interactive','interactive':{'type':'flow','body':{'text':form['title']},'action':{'name':'flow','parameters':{'flow_message_version':'3','flow_token':dispatch['flow_token'],'flow_id':form['meta_id'],'flow_cta':'Open form','flow_action':'navigate','flow_action_payload':{'screen':'DETAILS'}}}}}
            result=meta.graph_request(tenant,settings['PHONE_ID'],'messages','POST',payload)
            external=result.get('messages',[{}])[0].get('id')
            if not isinstance(external,str) or not external:raise meta.ProviderError('Meta did not return a message ID.')
            changes={}
    except (meta.ProviderError,OSError,ValueError,TypeError,IndexError,KeyError,AttributeError) as error:
        if not isinstance(error,meta.ProviderError):error=meta.ProviderError('Meta returned an invalid or uncertain response. Check Meta before retrying.')
        with store.db() as db:
            current=store._get(db,tenant,'whatsappform',form['id'])
            if current.get('operation')==marker:store._put(db,tenant,'whatsappform',dict(current,last_error=str(error),operation='' if getattr(error,'definitive',False) else marker),form['id'])
            if op=='send':
                current_dispatch=store._get(db,tenant,'formsend',dispatch['id'])
                if current_dispatch.get('status')!='completed':store._put(db,tenant,'formsend',dict(current_dispatch,status='failed' if getattr(error,'definitive',False) else 'unknown'),dispatch['id'])
        raise Problem(str(error),502) from None
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'whatsappform',form['id'])
        if current.get('operation')!=marker:raise Problem('Form operation changed. Reconcile with Meta.',409)
        final=store._put(db,tenant,'whatsappform',dict(current,**changes,operation='',operation_started=0,operation_kind='',last_error='',updated=int(time.time())),form['id'])
        if op=='send':
            current_dispatch=store._get(db,tenant,'formsend',dispatch['id'])
            store._put(db,tenant,'formsend',dict(current_dispatch,status='completed' if current_dispatch.get('status')=='completed' else 'accepted',external_id=external),dispatch['id'])
            store._message(db,tenant,c['id'],'[WhatsApp form] '+form['title'],'out','accepted',external)
        return final


def receive(store,db,tenant,contact,event):
    reply=event.get('interactive',{}).get('nfm_reply',{}) if isinstance(event.get('interactive'),dict) else {}
    raw=reply.get('response_json') if isinstance(reply,dict) else None
    if not isinstance(raw,str) or len(raw)>10000:return
    try:values=json.loads(raw)
    except ValueError:return
    if not isinstance(values,dict):return
    token=values.pop('flow_token',None)
    if not isinstance(token,str):return
    dispatch=next((s for s in store._list(db,tenant,'formsend') if s['contact_id']==contact['id'] and s.get('flow_token')==token and s.get('status') in ('accepted','sent','delivered','read','unknown','submitting') and 0<=int(time.time())-s['created']<7*86400),None)
    if not dispatch or any(r.get('dispatch_id')==dispatch['id'] for r in store._list(db,tenant,'formresponse')):return
    form=store._get(db,tenant,'whatsappform',dispatch['form_id']);answers={}
    for i,f in enumerate(form['fields']):
        key='question_'+str(i+1);v=values.get(key)
        if f['required'] and (not isinstance(v,str) or not v.strip()):return
        if v is not None and (not isinstance(v,str) or len(v)>200):return
        if f['type']=='choice' and v is not None:
            if v not in [str(j) for j in range(len(f['options']))]:return
            v=f['options'][int(v)]
        answers[key]=v
    store._put(db,tenant,'formresponse',dict(form_id=form['id'],dispatch_id=dispatch['id'],contact_id=contact['id'],answers=answers,created=int(time.time())))
    store._put(db,tenant,'formsend',dict(dispatch,status='completed',completed=int(time.time())),dispatch['id'])


def delivery(store,db,tenant,external,status):
    ranks={'accepted':0,'sent':1,'delivered':2,'read':3,'failed':4}
    if status not in ranks:return
    for item in store._list(db,tenant,'formsend'):
        if item.get('external_id')==external and item.get('status')!='completed' and ranks.get(item.get('status'),-1)<=ranks[status]:store._put(db,tenant,'formsend',dict(item,status=status),item['id'])
