"""Saved drafts, optimistic editor conflicts and immutable chatbot configurations."""
import json
from flows import validate_graph,default_graph,validate_members
from flow_resources import resolve
from flow_waits import cancel_sessions

FIELDS=('name','keyword','reply','enabled','delivery_mode','graph')


def configuration(flow):return {key:flow[key] for key in FIELDS}


def validate(store,db,tenant,data,old):
    from store import required,Problem
    mode=data.get('delivery_mode',old.get('delivery_mode','draft'))
    if mode not in ['draft','live']:raise Problem('Choose draft or live chatbot delivery.')
    values={'name':required(data.get('name'),'Name',150),'keyword':required(data.get('keyword'),'Keyword',100).lower(),'reply':required(data.get('reply'),'Reply'),'enabled':data.get('enabled') is True,'delivery_mode':mode}
    values['graph']=validate_graph(data.get('graph') or old.get('graph') or default_graph(values['reply']))
    validate_members(values['graph'],{r['user'] for r in db.execute('SELECT user FROM members WHERE tenant=?',(tenant,))})
    resolve(store,db,tenant,values['graph'],mode=='live')
    return values


def record(db,tenant,flow,actor,stamp):
    """Write once. Runtime counters and drafts are not part of a published config."""
    if not flow.get('version'):return
    value=json.dumps(configuration(flow),sort_keys=True,separators=(',',':'))
    old=db.execute('SELECT data FROM flow_versions WHERE tenant=? AND flow=? AND version=?',(tenant,flow['id'],flow['version'])).fetchone()
    if old:
        if old['data']!=value:raise ValueError('Published version cannot be overwritten.')
        return
    db.execute('INSERT INTO flow_versions VALUES(?,?,?,?,?,?)',(tenant,flow['id'],flow['version'],value,actor,stamp))


def history(db,tenant,flow):
    return [dict(row) for row in db.execute('SELECT version,actor,published_at FROM flow_versions WHERE tenant=? AND flow=? ORDER BY version DESC LIMIT 20',(tenant,flow))]


def action(store,db,ctx,operation,data,stamp):
    from store import Problem
    tenant=ctx['tenant_id'];user=ctx['user']['id']
    if not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(tenant,user)).fetchone():raise Problem('Administrator access required.',403)
    old=store._get(db,tenant,'flow',data['id']) if data.get('id') else None
    if not old and operation!='flow.draft.save':raise Problem('Choose an existing chatbot.')
    draft=(old or {}).get('draft') or {}
    if old:
        if type(data.get('base_version')) is not int or data['base_version']!=old.get('version',0):raise Problem('Published chatbot changed. Refresh before editing.',409)
        if type(data.get('draft_revision')) is not int or data['draft_revision']!=draft.get('revision',0):raise Problem('Another editor changed this draft. Refresh before editing.',409)
    if operation=='flow.publish':
        if not draft or draft['base_version']!=old.get('version',0):raise Problem('Save a fresh draft before publishing.',409)
        values=validate(store,db,tenant,draft,old)
        record(db,tenant,old,user,stamp)
        values.update(version=old.get('version',0)+1,executions=old.get('executions',0),owner=user)
        cancel_sessions(store,db,tenant,old['id'],stamp)
        result=store._put(db,tenant,'flow',values,old['id'])
        record(db,tenant,result,user,stamp)
        return result
    if operation=='flow.draft.restore':
        if type(data.get('version')) is not int:raise Problem('Choose a saved version.')
        row=db.execute('SELECT data FROM flow_versions WHERE tenant=? AND flow=? AND version=?',(tenant,old['id'],data['version'])).fetchone()
        if not row:raise Problem('Published version is unavailable.',404)
        source=json.loads(row['data'])
    else:source=data
    values=validate(store,db,tenant,source,old or {})
    values.update(revision=draft.get('revision',0)+1,base_version=(old or {}).get('version',0),updated=stamp,updated_by=user)
    if not old:
        old=store._put(db,tenant,'flow',dict(configuration(values),enabled=False,version=0,executions=0,owner=user))
    return store._put(db,tenant,'flow',dict(old,draft=values),old['id'])
