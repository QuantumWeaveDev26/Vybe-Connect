"""Single-page public HTTPS knowledge ingestion with atomic explicit refresh."""
import hashlib
import ipaddress
import os
import re
import secrets
import socket
import time
from html.parser import HTMLParser
from external_agents import PinnedConnection,endpoint
from knowledge_documents import KnowledgeError
from crm import text

MAX_BYTES=1048576


class PageText(HTMLParser):
    excluded={'script','style','noscript','iframe','svg','template','form','nav','footer'}
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.blocked=[]
    def handle_starttag(self,tag,attrs):
        if tag in self.excluded:self.blocked.append(tag)
        elif not self.blocked and tag in {'p','div','h1','h2','h3','li','br','tr'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in self.blocked:
            position=len(self.blocked)-1-self.blocked[::-1].index(tag);self.blocked=self.blocked[:position]
        elif not self.blocked and tag in {'p','div','h1','h2','h3','li','tr'}:self.parts.append('\n')
    def handle_data(self,value):
        if not self.blocked:self.parts.append(value)


def extract_page(mime,raw):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_BYTES:raise ValueError('Website response exceeds the size limit.')
    if mime not in ['text/html','text/plain']:raise ValueError('Use a public UTF-8 HTML or text page.')
    try:content=raw.decode('utf-8-sig')
    except UnicodeError:raise ValueError('Use a UTF-8 page.') from None
    if mime=='text/html':
        parser=PageText();parser.feed(content);parser.close();content=''.join(parser.parts)
    content='\n'.join(re.sub(r'[ \t]+',' ',line).strip() for line in content.splitlines());content=re.sub(r'\n{3,}','\n\n',content).strip()
    if not content or len(content)>120000 or any(ord(c)<32 and c not in '\r\n\t' for c in content):raise ValueError('Page must contain 1–120,000 readable characters.')
    return content


def fetch_page(value):
    url=endpoint(value);addresses=socket.getaddrinfo(url.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Only public website addresses are supported.')
    connection=PinnedConnection(url.hostname,addresses[0][4][0])
    try:
        connection.request('GET',url.path or '/',headers={'Accept':'text/html,text/plain','Accept-Encoding':'identity','User-Agent':'TeamWave-Knowledge/1'})
        response=connection.getresponse()
        if response.status!=200 or response.getheader('Content-Encoding','identity').lower() not in ['identity','']:raise ValueError('Use a direct uncompressed page returning HTTP 200.')
        mime=response.getheader('Content-Type','').split(';',1)[0].strip().lower()
        if mime not in ['text/html','text/plain']:raise ValueError('Unsupported page format.')
        parts=[];size=0;deadline=time.monotonic()+15
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError('Website response exceeded its read deadline.')
            if connection.sock:connection.sock.settimeout(min(8,remaining))
            part=response.read1(min(65536,MAX_BYTES+1-size))
            if not part:break
            parts.append(part);size+=len(part)
            if size>MAX_BYTES:raise ValueError('Website response exceeds the size limit.')
        raw=b''.join(parts)
        return mime,raw
    finally:connection.close()


def allowed(tenant,value):
    try:url=endpoint(value)
    except ValueError:raise KnowledgeError('Use a public HTTPS URL on port 443 without credentials, queries or fragments.') from None
    origin='https://'+url.hostname.lower()
    origins={v.strip().rstrip('/').lower() for v in os.environ.get('TW_KNOWLEDGE_WEB_'+tenant.upper()+'_ALLOWED_ORIGINS','').split(',') if v.strip()}
    if origin not in origins:raise KnowledgeError('Allow this exact website origin in the workspace server configuration before fetching.',403)
    return url._replace(netloc=url.hostname.lower(),path=url.path or '/').geturl()


def website_action(store,ctx,operation,data):
    if ctx['role']!='admin':raise KnowledgeError('Administrator access required.',403)
    tenant=ctx['tenant_id'];old=None
    with store.db() as db:
        if operation in ['knowledge.website.refresh','knowledge.website.preview']:
            old=store._get(db,tenant,'knowledgedocument',data.get('id'))
            if old.get('format')!='website':raise KnowledgeError('Choose an indexed website source.')
            if operation=='knowledge.website.preview':
                chunks=db.execute('SELECT text FROM knowledge_chunks WHERE tenant=? AND document=? ORDER BY ordinal LIMIT 3',(tenant,old['id'])).fetchall()
                return {'title':old['title'],'url':old['url'],'text':'\n\n'.join(r['text'] for r in chunks),'truncated':old['chunks']>3}
            url=allowed(tenant,old['url']);title=old['title']
        elif operation=='knowledge.website.add':
            url=allowed(tenant,data.get('url'));title=text(data.get('title'),'Source title',120)
            documents=store._list(db,tenant,'knowledgedocument')
            if any(d.get('url')==url for d in documents):raise KnowledgeError('This page is already indexed. Use Refresh.',409)
            if len(documents)>=20:raise KnowledgeError('Use up to 20 indexed documents and pages per workspace.')
        else:raise KnowledgeError('Unknown website knowledge action.',404)
    try:
        mime,raw=fetch_page(url);content=extract_page(mime,raw)
    except Exception:
        if old:
            with store.db() as db:
                db.execute('BEGIN IMMEDIATE');current=next((d for d in store._list(db,tenant,'knowledgedocument') if d['id']==old['id']),None)
                if current and current.get('revision')==old.get('revision'):store._put(db,tenant,'knowledgedocument',dict(current,refresh_error='Refresh failed. Last successful snapshot retained.',last_attempt=int(time.time())),old['id'])
        raise KnowledgeError('Website fetch or text extraction failed. No new snapshot was indexed.',502) from None
    stamp=int(time.time());chunks=[content[start:start+1200] for start in range(0,len(content),1000)]
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');allowed(tenant,url)
        if not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(tenant,ctx['user']['id'])).fetchone():raise KnowledgeError('Administrator access changed during fetch.',403)
        documents=store._list(db,tenant,'knowledgedocument')
        if old:
            current=store._get(db,tenant,'knowledgedocument',old['id'])
            if current.get('revision')!=old.get('revision') or current['enabled']!=old['enabled']:raise KnowledgeError('Source changed during fetch. Review it before refreshing again.',409)
        else:
            if len(documents)>=20 or any(d.get('url')==url for d in documents):raise KnowledgeError('Source capacity or URL changed during fetch. Refresh the list.',409)
        values=dict(title=title,filename=title,format='website',url=url,size=len(raw),characters=len(content),chunks=len(chunks),enabled=old['enabled'] if old else False,digest=hashlib.sha256(raw).hexdigest(),updated=stamp,last_attempt=stamp,last_success=stamp,refresh_error='',revision=secrets.token_hex(16))
        document=store._put(db,tenant,'knowledgedocument',values,old['id'] if old else None)
        db.execute('DELETE FROM knowledge_chunks WHERE tenant=? AND document=?',(tenant,document['id']))
        for ordinal,chunk in enumerate(chunks):db.execute('INSERT INTO knowledge_chunks VALUES(?,?,?,?,?)',(tenant,document['id'],secrets.token_hex(8),ordinal,chunk))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,stamp))
    return document
