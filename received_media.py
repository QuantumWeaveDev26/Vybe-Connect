"""Tenant-scoped received attachment metadata and explicit private downloads."""
import json
import re
import secrets
import time
from media_service import MediaError,asset_path
from whatsapp_media import SUPPORTED_TYPES,MAX_MEDIA_BYTES,_validate_file
from media_download import retrieve_media


def project(record):
    result={key:record[key] for key in ['id','message_id','contact_id','kind','filename','mime','status','created','updated','asset_id','error'] if key in record}
    if result['status']=='downloading' and record.get('claimed',0)<=int(time.time())-90:result.update(status='retry_available',error='Retrieval lease expired. An explicit retry is available.')
    return result


def state(db,tenant):
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='receivedmedia' ORDER BY rowid DESC LIMIT 200",(tenant,)).fetchall()
    return [project(dict(json.loads(row['data']),id=row['id'])) for row in reversed(rows)]


def record(store,db,tenant,message,event):
    kind=event.get('type')
    if not isinstance(kind,str) or kind not in ['image','audio','video','document']:return None
    payload=event.get(kind);payload=payload if isinstance(payload,dict) else {}
    provider_id=payload.get('id');mime=payload.get('mime_type');mime=mime.split(';',1)[0].strip().lower() if isinstance(mime,str) else ''
    valid=isinstance(provider_id,str) and bool(re.fullmatch(r'[0-9]{1,128}',provider_id)) and mime in SUPPORTED_TYPES and SUPPORTED_TYPES[mime][0]==kind
    filename=payload.get('filename');filename=filename[:120] if isinstance(filename,str) else 'Received '+kind
    checksum=payload.get('sha256');checksum=checksum if isinstance(checksum,str) and len(checksum)<=128 else ''
    return store._put(db,tenant,'receivedmedia',dict(message_id=message['id'],contact_id=message['contact'],kind=kind,filename=filename,mime=mime,provider_id=provider_id if valid else '',sha256=checksum,status='received' if valid else 'unavailable',created=int(time.time()),updated=int(time.time()),asset_id='',error='' if valid else 'Attachment format or metadata is unsupported.'))


def download(store,ctx,data):
    tenant=ctx['tenant_id'];stamp=int(time.time());path=None;claim=secrets.token_hex(16)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,ctx['user']['id'])).fetchone():raise MediaError('Workspace access denied.',403)
        item=store._get(db,tenant,'receivedmedia',data.get('id'))
        if item['status']=='downloaded':
            cached=asset_path(store,tenant,item['asset_id'])
            if cached.is_file() and cached.stat().st_size<=MAX_MEDIA_BYTES:return project(item)
        if item['status']=='unavailable':raise MediaError('This attachment format or metadata is unsupported.')
        if item['status']=='downloading' and item.get('claimed',0)>stamp-90:raise MediaError('This attachment is already being retrieved.',409)
        item=store._put(db,tenant,'receivedmedia',dict(item,status='downloading',claim=claim,claimed=stamp,error='',updated=stamp),item['id'])
    try:
        result=retrieve_media(tenant,item['provider_id'],{'mime':item['mime'],'filename':item['filename'],'sha256':item['sha256']})
        raw=result['data'];mime=result['mime'];filename=result['filename'];_validate_file(filename,mime,raw)
        if len(raw)>MAX_MEDIA_BYTES:raise ValueError('File too large.')
        asset_id=secrets.token_hex(8);path=asset_path(store,tenant,asset_id);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'receivedmedia',item['id'])
            if current.get('claim')!=claim or current['status']!='downloading':raise MediaError('Download state changed.',409)
            if not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,ctx['user']['id'])).fetchone():raise MediaError('Workspace access changed during download.',403)
            asset=dict(filename=filename,mime=mime,kind=item['kind'],size=len(raw),provider_id=item['provider_id'],owner=ctx['user']['id'],created=int(time.time()),status='downloaded',source='received',contact_id=item['contact_id'])
            db.execute('INSERT INTO entities VALUES(?,?,?,?)',(asset_id,tenant,'media',json.dumps(asset)))
            updated=store._put(db,tenant,'receivedmedia',dict(current,status='downloaded',asset_id=asset_id,filename=filename,error='',claim='',updated=int(time.time())),item['id'])
            db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],'media.receive.download',int(time.time())))
        return project(updated)
    except Exception as error:
        if path and path.is_file():path.unlink()
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'receivedmedia',item['id'])
            if current.get('claim')==claim:store._put(db,tenant,'receivedmedia',dict(current,status='failed',claim='',updated=int(time.time()),error='Attachment retrieval failed. Check access, format and size before an explicit retry.'),item['id'])
        if isinstance(error,MediaError):raise error
        raise MediaError('Received attachment could not be retrieved or published.',502) from None
