"""Authenticated workspace feedback, separate from external customer messaging."""
import json
import re
import time


def state(db,ctx):
    sql="SELECT id,data FROM entities WHERE tenant=? AND kind='productfeedback'";args=[ctx['tenant_id']]
    if ctx['role']!='admin':sql+=" AND json_extract(data,'$.owner')=?";args.append(ctx['user']['id'])
    return [dict(json.loads(row['data']),id=row['id']) for row in db.execute(sql+' ORDER BY rowid DESC LIMIT 100',args)]


def action(store,ctx,operation,data):
    from store import Problem
    tenant=ctx['tenant_id'];user=ctx['user']['id'];stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');member=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(tenant,user)).fetchone()
        if not member:raise Problem('Workspace access changed.',403)
        if operation=='feedback.save':
            rating=data.get('rating',0);body=data.get('body','');category=data.get('category','feedback');page=data.get('page','')
            if type(rating) is not int or not 0<=rating<=5 or not isinstance(body,str) or len(body)>4000 or not rating and not body.strip():raise Problem('Choose a 1-5 rating or write feedback of up to 4,000 characters.')
            if category not in ['feedback','bug','idea'] or not isinstance(page,str) or not re.fullmatch(r'[a-z-]{0,60}',page):raise Problem('Choose a supported feedback category and page.')
            count=db.execute("SELECT COUNT(*) FROM entities WHERE tenant=? AND kind='productfeedback' AND json_extract(data,'$.owner')=? AND json_extract(data,'$.created')>?",(tenant,user,stamp-86400)).fetchone()[0]
            if count>=20:raise Problem('Use up to 20 feedback reports per account and workspace per day.',429)
            result=store._put(db,tenant,'productfeedback',{'owner':user,'rating':rating,'body':body.strip(),'category':category,'page':page,'status':'open','version':1,'created':stamp,'updated':stamp})
        elif operation=='feedback.status':
            if ctx['role']!='admin' or member['role']!='admin':raise Problem('Administrator access required.',403)
            old=store._get(db,tenant,'productfeedback',data.get('id'))
            if type(data.get('version')) is not int or data['version']!=old['version']:raise Problem('Feedback changed. Refresh before updating.',409)
            if data.get('status') not in ['open','reviewing','resolved']:raise Problem('Choose open, reviewing or resolved.')
            result=store._put(db,tenant,'productfeedback',dict(old,status=data['status'],version=old['version']+1,updated=stamp),old['id'])
        else:raise Problem('Unknown feedback action.',404)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,stamp))
        return result
