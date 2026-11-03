"""Read-only Meta media retrieval with restricted, pinned HTTPS downloads."""
import base64
import hashlib
import hmac
import ipaddress
import json
import re
import socket
import time
from urllib.parse import urlsplit,urlencode
from external_agents import PinnedConnection
from meta import ProviderError
from whatsapp_media import _configuration,_configured,_filename,_validate_file,SUPPORTED_TYPES,MAX_MEDIA_BYTES


def digest(value):
    if not isinstance(value,str):raise ValueError('Invalid digest.')
    if re.fullmatch(r'[a-fA-F0-9]{64}',value):return bytes.fromhex(value)
    if len(value)!=44:raise ValueError('Invalid digest.')
    result=base64.b64decode(value,validate=True)
    if len(result)!=32:raise ValueError('Invalid digest.')
    return result


def download_target(value):
    url=urlsplit(value)
    if url.scheme!='https' or url.hostname!='lookaside.fbsbx.com' or url.username or url.password or url.port not in [None,443] or url.fragment or not url.path.startswith('/whatsapp_business/attachments/') or len(value)>6000 or any(ord(c)<33 or ord(c)>126 for c in value):raise ValueError('Unsupported Meta media destination.')
    return url.hostname,url.path+('?' + url.query if url.query else '')


def read_https(host,path,token,maximum):
    addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Public media host required.')
    connection=PinnedConnection(host,addresses[0][4][0])
    try:
        connection.request('GET',path,headers={'Authorization':'Bearer '+token,'Accept-Encoding':'identity','User-Agent':'TeamWave-Media/1'})
        response=connection.getresponse()
        if response.status!=200 or response.getheader('Content-Encoding','identity').lower() not in ['','identity']:raise ValueError('Media provider did not return a direct supported response.')
        content_type=response.getheader('Content-Type','').split(';',1)[0].strip().lower();parts=[];size=0;deadline=time.monotonic()+20
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError('Media response deadline exceeded.')
            if connection.sock:connection.sock.settimeout(min(8,remaining))
            part=response.read1(min(65536,maximum+1-size))
            if not part:break
            parts.append(part);size+=len(part)
            if size>maximum:raise ValueError('Media response exceeds limits.')
        return content_type,b''.join(parts)
    finally:connection.close()


def retrieve_media(tenant,provider_id,expected):
    try:
        settings=_configuration(tenant)
        if not _configured(settings) or not isinstance(provider_id,str) or not re.fullmatch(r'[0-9]{1,128}',provider_id):raise ValueError('Media credentials or identifier are unavailable.')
        mime,raw=read_https('graph.facebook.com','/'+settings['VERSION']+'/'+provider_id+'?'+urlencode({'phone_number_id':settings['PHONE_ID']}),settings['TOKEN'],65536)
        if mime!='application/json':raise ValueError('Invalid metadata response.')
        info=json.loads(raw)
        if not isinstance(info,dict) or info.get('id')!=provider_id:raise ValueError('Media identity mismatch.')
        mime=info.get('mime_type','').split(';',1)[0].strip().lower();size=info.get('file_size');claimed=digest(info.get('sha256'))
        if mime not in SUPPORTED_TYPES or type(size) is not int or not 0<size<=MAX_MEDIA_BYTES:raise ValueError('Unsupported media format/size.')
        if expected.get('mime') and expected['mime']!=mime:raise ValueError('Webhook/metadata MIME mismatch.')
        if expected.get('sha256') and not hmac.compare_digest(digest(expected['sha256']),claimed):raise ValueError('Webhook/metadata digest mismatch.')
        host,path=download_target(info.get('url'));actual_mime,data=read_https(host,path,settings['TOKEN'],MAX_MEDIA_BYTES)
        if actual_mime!=mime or len(data)!=size or not hmac.compare_digest(hashlib.sha256(data).digest(),claimed):raise ValueError('Media bytes do not match verified metadata.')
        fallback='received-'+provider_id+SUPPORTED_TYPES[mime][1][0];name=expected.get('filename') or fallback
        try:
            _filename(name)
            if not name.lower().endswith(SUPPORTED_TYPES[mime][1]):name=fallback
        except ProviderError:name=fallback
        _validate_file(name,mime,data)
        return {'data':data,'mime':mime,'filename':name}
    except Exception:raise ProviderError('Received attachment could not be verified or downloaded. Check Meta access and retry explicitly.') from None
