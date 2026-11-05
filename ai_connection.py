"""Customer-owned AI credentials. Saving does not call the provider."""
import re
import time
from embedded_signup import administrator,read_credentials,write_credentials,ConnectionError


def settings(tenant):
    if not isinstance(tenant,str) or not re.fullmatch(r'[a-f0-9]{16}',tenant):return None
    return read_credentials(tenant,'ai')


def action(store,ctx,operation,data):
    administrator(store,ctx)
    tenant=ctx['tenant_id']
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        administrator(store,ctx)
        old=settings(tenant) or {}
        changing_key=operation=='ai.connection.disconnect' or operation=='ai.connection.save' and bool(data.get('key')) and data.get('key')!=old.get('key')
        active=any(job.get('provider')=='openai' and (job.get('status')=='running' or job.get('provider_id') and job.get('status') in ('waiting','cancelling','unknown','cancel_unconfirmed')) for job in store._list(db,tenant,'aijob'))
        if changing_key and active:
            raise ConnectionError('Stop or resolve active AI conversations before changing or removing the key. You can pause new usage now.',409)
        if operation=='ai.connection.save':
            key=data.get('key','')
            if not isinstance(key,str):raise ConnectionError('Enter an OpenAI project API key.')
            key=key.strip() or old.get('key','')
            if not re.fullmatch(r'sk-[A-Za-z0-9_-]{20,512}',key):raise ConnectionError('Enter a valid OpenAI project API key. Its value is never returned.')
            model=data.get('model','')
            if not isinstance(model,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',model):raise ConnectionError('Enter a valid OpenAI model ID.')
            if type(data.get('enabled')) is not bool:raise ConnectionError('Choose whether real AI usage is enabled.')
            write_credentials(tenant,{'key':key,'model':model,'enabled':data['enabled'],'updated':int(time.time())},'ai')
        elif operation=='ai.connection.pause':
            if not old or old.get('disconnected'):raise ConnectionError('No customer AI connection is saved.',404)
            old['enabled']=False;write_credentials(tenant,old,'ai')
        elif operation=='ai.connection.disconnect':
            write_credentials(tenant,{'disconnected':True,'enabled':False},'ai')
        else:raise ConnectionError('Unknown AI connection action.')
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,int(time.time())))
    from ai import ai_status
    return ai_status(tenant)
