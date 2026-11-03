"""Bounded local document extraction and lexical passage retrieval. No network calls."""
import hashlib
import io
import math
import re
import secrets
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import PurePath


class KnowledgeError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def extract(filename,raw):
    if not isinstance(filename,str) or not re.fullmatch(r'[^\x00-\x1f/\\]{1,120}',filename) or '..' in filename:raise KnowledgeError('Use a plain document filename without paths.')
    if not isinstance(raw,bytes) or not 0<len(raw)<=1048576:raise KnowledgeError('Upload a document up to 1 MiB.')
    format=PurePath(filename).suffix.lower().lstrip('.')
    try:
        if format in ['txt','md','csv']:text=raw.decode('utf-8-sig')
        elif format=='docx':
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                files=archive.infolist()
                if len(files)>200 or sum(f.file_size for f in files)>2097152 or any(f.flag_bits&1 for f in files):raise KnowledgeError('The DOCX archive exceeds extraction limits or is encrypted.')
                content=archive.read('word/document.xml')
                if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():raise KnowledgeError('Document XML declarations are unsupported.')
                root=ET.fromstring(content);namespace='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                text='\n'.join(''.join(p.itertext()) for p in root.iter(namespace+'p'))
        else:raise KnowledgeError('Supported documents: UTF-8 TXT, Markdown, CSV and DOCX. PDF extraction is not enabled.')
    except (UnicodeError,zipfile.BadZipFile,KeyError,ET.ParseError,RuntimeError,NotImplementedError):raise KnowledgeError('The document could not be read. Use valid UTF-8 text or an unencrypted DOCX file.') from None
    text=text.strip()
    if not text or len(text)>120000 or any(ord(c)<32 and c not in '\r\n\t' for c in text):raise KnowledgeError('Use a text document with 1–120,000 readable characters.')
    return format,text


def upload(store,ctx,filename,raw):
    if ctx['role']!='admin':raise KnowledgeError('Administrator access required.',403)
    format,text=extract(filename,raw);digest=hashlib.sha256(raw).hexdigest();tenant=ctx['tenant_id'];stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');documents=store._list(db,tenant,'knowledgedocument')
        duplicate=next((d for d in documents if d['digest']==digest),None)
        if duplicate:return duplicate
        if len(documents)>=20:raise KnowledgeError('Use up to 20 uploaded documents per workspace.')
        chunks=[text[start:start+1200] for start in range(0,len(text),1000)]
        document=store._put(db,tenant,'knowledgedocument',{'title':filename,'filename':filename,'format':format,'size':len(raw),'characters':len(text),'chunks':len(chunks),'enabled':True,'digest':digest,'updated':stamp})
        for ordinal,chunk in enumerate(chunks):db.execute('INSERT INTO knowledge_chunks VALUES(?,?,?,?,?)',(tenant,document['id'],secrets.token_hex(8),ordinal,chunk))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],'knowledge.document.upload',stamp))
    return document


def document_action(store,ctx,action,data):
    if ctx['role']!='admin':raise KnowledgeError('Administrator access required.',403)
    tenant=ctx['tenant_id']
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');document=store._get(db,tenant,'knowledgedocument',data.get('id'))
        if action=='knowledge.document.delete':
            db.execute("DELETE FROM entities WHERE tenant=? AND id=? AND kind='knowledgedocument'",(tenant,document['id']));db.execute('DELETE FROM knowledge_chunks WHERE tenant=? AND document=?',(tenant,document['id']));result={'deleted':True}
        elif action=='knowledge.document.update':
            if not isinstance(data.get('enabled'),bool):raise KnowledgeError('Enabled must be true or false.')
            result=store._put(db,tenant,'knowledgedocument',dict(document,enabled=data['enabled'],updated=int(time.time())),document['id'])
        else:raise KnowledgeError('Unknown document action.',404)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],action,int(time.time())))
    return result


def tokens(text):return set(re.findall(r'[^\W_]{2,}',str(text).lower(),re.UNICODE))-{'the','and','for','are','what','how','does','with','from','this','that','can','you','your','our'}


def retrieve(store,db,tenant,query,document_ids=None):
    documents={d['id']:d for d in store._list(db,tenant,'knowledgedocument') if d['enabled'] and (document_ids is None or d['id'] in document_ids)}
    if not documents:return []
    rows=[dict(r) for r in db.execute('SELECT * FROM knowledge_chunks WHERE tenant=? ORDER BY document,ordinal',(tenant,)) if r['document'] in documents]
    terms=set(sorted(tokens(query))[:64]);wordsets=[tokens(row['text']) for row in rows];frequency={term:sum(term in words for words in wordsets) for term in terms};ranked=[]
    for row,words in zip(rows,wordsets):
        score=sum(1+math.log((len(rows)+1)/(frequency[term]+1)) for term in terms&words)
        if terms and not score:continue
        ranked.append((score,row))
    ranked.sort(key=lambda pair:(-pair[0],pair[1]['document'],pair[1]['ordinal']))
    return [{'document_id':row['document'],'chunk_id':row['id'],'title':documents[row['document']]['title'],'passage':row['ordinal']+1,'text':row['text']} for _,row in ranked[:6]]


def passage(store,ctx,document_id,chunk_id):
    with store.db() as db:
        document=store._get(db,ctx['tenant_id'],'knowledgedocument',document_id)
        row=db.execute('SELECT ordinal,text FROM knowledge_chunks WHERE tenant=? AND document=? AND id=?',(ctx['tenant_id'],document_id,chunk_id)).fetchone()
    if not document['enabled'] or not row:raise KnowledgeError('This source passage is unavailable or disabled.',404)
    return {'document_id':document_id,'chunk_id':chunk_id,'title':document['title'],'passage':row['ordinal']+1,'text':row['text']}
