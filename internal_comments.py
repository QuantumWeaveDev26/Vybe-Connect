"""Private note authorship and tenant/recipient-scoped in-app mentions."""
import json
import time


def create(store,db,ctx,contact,body,mentions):
    from store import Problem
    tenant=ctx['tenant_id'];author=ctx['user']['id'];stamp=int(time.time())
    if not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,author)).fetchone():raise Problem('Workspace access changed.',403)
    if not isinstance(mentions,list) or len(mentions)>20 or any(not isinstance(u,str) or not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,u)).fetchone() for u in mentions):raise Problem('Mention up to 20 current workspace teammates.')
    mentions=list(dict.fromkeys(mentions))
    message=store._message(db,tenant,contact['id'],body,'note','internal')
    store._put(db,tenant,'internalcomment',{'message_id':message['id'],'contact_id':contact['id'],'author':author,'mentions':mentions,'created':stamp})
    for recipient in mentions:
        if recipient!=author:store._put(db,tenant,'mentionnotification',{'message_id':message['id'],'contact_id':contact['id'],'author':author,'owner':recipient,'read':False,'created':stamp})
    return message


def state(store,db,ctx):
    tenant=ctx['tenant_id']
    comments=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='internalcomment' ORDER BY rowid DESC LIMIT 2000",(tenant,)).fetchall()
    notifications=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='mentionnotification' AND json_extract(data,'$.owner')=? ORDER BY rowid DESC LIMIT 50",(tenant,ctx['user']['id'])).fetchall()
    return {'internal_comments':[dict(json.loads(r['data']),id=r['id']) for r in comments],'mention_notifications':[dict(json.loads(r['data']),id=r['id']) for r in notifications]}


def read(store,ctx,data):
    from store import Problem
    tenant=ctx['tenant_id'];user=ctx['user']['id']
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,user)).fetchone():raise Problem('Workspace access changed.',403)
        value=store._get(db,tenant,'mentionnotification',data.get('id'))
        if value['owner']!=user:raise Problem('Notification access denied.',403)
        store._put(db,tenant,'mentionnotification',dict(value,read=True),value['id'])
        return {'read':True,'contact_id':value['contact_id']}
