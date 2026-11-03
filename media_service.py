"""Private media assets and one-attempt, service-window-gated sending."""
import hashlib
import json
import re
import secrets
import time
from pathlib import Path
from meta import ProviderError,status as meta_status
from whatsapp_media import MAX_MEDIA_BYTES,SUPPORTED_TYPES,upload_media,send_media
from reply_tracking import accepted as track_accepted_reply


class MediaError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def asset_path(store,tenant,id):
    if not re.fullmatch(r'[0-9a-f]{16}',tenant) or not re.fullmatch(r'[0-9a-f]{16}',id):raise MediaError('Invalid media scope.')
    base=(store.path.parent/'media').resolve();path=(base/tenant/id).resolve()
    if not path.is_relative_to(base):raise MediaError('Invalid media path.')
    return path


def upload_for_workspace(store,ctx,filename,mime,data):
    if mime not in SUPPORTED_TYPES or not isinstance(data,bytes) or not 0<len(data)<=MAX_MEDIA_BYTES:raise MediaError('Choose a supported file up to 5 MiB.')
    try:provider_id=upload_media(ctx['tenant_id'],filename,mime,data)
    except ProviderError as error:raise MediaError(str(error),400 if error.definitive else 502) from None
    id=secrets.token_hex(8);path=asset_path(store,ctx['tenant_id'],id);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    asset={'filename':filename,'mime':mime,'kind':SUPPORTED_TYPES[mime][0],'size':len(data),'provider_id':provider_id,'owner':ctx['user']['id'],'created':int(time.time()),'status':'uploaded'}
    with store.db() as db:
        db.execute('INSERT INTO entities VALUES(?,?,?,?)',(id,ctx['tenant_id'],'media',json.dumps(asset)))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(ctx['tenant_id'],ctx['user']['name'],'media.upload',int(time.time())))
    return dict(asset,id=id)


def read_asset(store,ctx,id):
    with store.db() as db:asset=store._get(db,ctx['tenant_id'],'media',id)
    path=asset_path(store,ctx['tenant_id'],id)
    if not path.is_file() or path.stat().st_size>MAX_MEDIA_BYTES:raise MediaError('Media file is unavailable.',404)
    return path.read_bytes(),asset['mime'],asset['filename']


def send_stored_media(store,ctx,data):
    tenant=ctx['tenant_id'];stamp=int(time.time());nonce=data.get('nonce');caption=data.get('caption','')
    if not isinstance(nonce,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,100}',nonce):raise MediaError('A stable send request identifier is required.')
    if not isinstance(caption,str) or len(caption)>1024:raise MediaError('Use a caption of up to 1,024 characters.')
    fingerprint=hashlib.sha256(json.dumps([data.get('contact_id'),data.get('asset_id'),caption]).encode()).hexdigest()
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        previous=store._list(db,tenant,'mediasend')
        same=next((x for x in previous if x['nonce']==nonce),None)
        if same:
            if same['fingerprint']!=fingerprint:raise MediaError('This send identifier was already used with different content.',409)
            return same
        if any(x['fingerprint']==fingerprint and x['status'] in ['sending','unknown'] for x in previous):raise MediaError('An identical media send is pending or uncertain. Reconcile it with Meta before sending again.',409)
        contact=store._get(db,tenant,'contact',data.get('contact_id'));asset=store._get(db,tenant,'media',data.get('asset_id'))
        last=contact.get('last_real_inbound',0)
        if not last or not 0<=stamp-last<86400:raise MediaError('A real inbound WhatsApp message within 24 hours is required for this media reply.')
        if not meta_status(tenant)['live']:raise MediaError('Live WhatsApp sending is disabled.')
        if asset['kind']=='audio' and caption:raise MediaError('Audio replies do not support a caption.')
        message=store._message(db,tenant,contact['id'],'['+asset['kind']+'] '+asset['filename']+('\n'+caption if caption else ''),'out','sending')
        record=store._put(db,tenant,'mediasend',{'nonce':nonce,'fingerprint':fingerprint,'contact_id':contact['id'],'asset_id':asset['id'],'message_id':message['id'],'status':'sending','created':stamp,'owner':ctx['user']['id']})
    try:
        external=send_media(tenant,contact['phone'],asset['provider_id'],asset['kind'],caption,asset['filename'] if asset['kind']=='document' else '')
        status='accepted';error=''
    except ProviderError as failure:external=None;status='failed' if failure.definitive else 'unknown';error=str(failure)
    except Exception:external=None;status='unknown';error='Provider outcome is uncertain. Check Meta before retrying.'
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');db.execute('UPDATE messages SET status=?,external_id=? WHERE id=? AND tenant=?',(status,external,message['id'],tenant))
        if status=='accepted':track_accepted_reply(store,db,tenant,message['id'],int(time.time()))
        result=store._put(db,tenant,'mediasend',dict(record,status=status,error=error,external_id=external),record['id'])
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],'media.send.'+status,int(time.time())))
    return result
