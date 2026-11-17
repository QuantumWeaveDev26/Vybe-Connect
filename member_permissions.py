"""Current workspace capability checks; defaults preserve existing agent access."""
import time

CAPABILITIES=('calling','reports','exports')


def policy(store,db,tenant,user):
    row=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(tenant,user)).fetchone()
    old=next((p for p in store._list(db,tenant,'memberpermission') if p['user']==user),{})
    values={key:bool(row and (row['role']=='admin' or old.get(key,True))) for key in CAPABILITIES}
    return dict(values,version=old.get('version',0))


def require(store,ctx,capability,db=None):
    from store import Problem
    if db is None:
        with store.db() as connection:return require(store,ctx,capability,connection)
    if not policy(store,db,ctx['tenant_id'],ctx['user']['id'])[capability]:
        raise Problem('Your workspace permission does not allow '+capability+'.',403)


def save(store,ctx,data):
    from store import Problem
    tenant=ctx['tenant_id'];target=data.get('id');values=data.get('permissions')
    if not isinstance(values,dict) or set(values)!=set(CAPABILITIES) or any(type(v) is not bool for v in values.values()):raise Problem('Choose calling, reports and export permissions.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        actor=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(tenant,ctx['user']['id'])).fetchone()
        member=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(tenant,target)).fetchone()
        if not actor or actor['role']!='admin':raise Problem('Administrator access required.',403)
        if not member:raise Problem('Member not found in this workspace.',404)
        if member['role']=='admin':raise Problem('Administrators retain full workspace access.',409)
        old=next((p for p in store._list(db,tenant,'memberpermission') if p['user']==target),{})
        if type(data.get('version')) is not int or data['version']!=old.get('version',0):raise Problem('Permissions changed. Refresh before editing.',409)
        result=store._put(db,tenant,'memberpermission',dict(values,user=target,version=old.get('version',0)+1,updated=int(time.time())),old.get('id'))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],'member.permissions:'+target,int(time.time())))
        return policy(store,db,tenant,target)
