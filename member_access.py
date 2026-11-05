"""Transactional workspace role/access changes with final-administrator protection."""
import team_operations
import json
import time


class MemberError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def action(store,ctx,operation,data):
    if ctx['role']!='admin':raise MemberError('Administrator access required.',403)
    tenant=ctx['tenant_id'];target=data.get('id');stamp=int(time.time())
    if not isinstance(target,str):raise MemberError('Choose a workspace member.')
    if operation=='member.role' and data.get('role') not in ['admin','agent']:raise MemberError('Choose admin or agent.')
    if operation not in ['member.role','member.remove']:raise MemberError('Unsupported member action.',404)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(tenant,ctx['user']['id'])).fetchone():raise MemberError('Administrator access changed.',403)
        current=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(tenant,target)).fetchone()
        if not current:raise MemberError('Member not found in this workspace.',404)
        loses_admin=current['role']=='admin' and (operation=='member.remove' or data['role']=='agent')
        if loses_admin and db.execute("SELECT COUNT(*) FROM members WHERE tenant=? AND role='admin'",(tenant,)).fetchone()[0]<=1:raise MemberError('Keep at least one workspace administrator.',409)
        if operation=='member.role':db.execute('UPDATE members SET role=? WHERE tenant=? AND user=?',(data['role'],tenant,target))
        else:
            db.execute('DELETE FROM members WHERE tenant=? AND user=?',(tenant,target))
            team_operations.removed_member(store,db,tenant,target)
            for kind,field in [('contact','assignee'),('task','owner')]:
                rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind=? AND json_extract(data,?)=?",(tenant,kind,'$.'+field,target)).fetchall()
                for row in rows:
                    value=json.loads(row['data'])
                    if kind=='task' and value.get('status')=='done':continue
                    if kind=='contact':team_operations.assignment(store,db,tenant,row['id'],target,'',ctx['user']['id'],'member_removed')
                    value[field]='';store._put(db,tenant,kind,value,row['id'])
        if loses_admin:
            db.execute('UPDATE api_tokens SET revoked=1 WHERE tenant=? AND user=?',(tenant,target))
            rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='workspaceinvite' AND json_extract(data,'$.issued_by')=? AND json_extract(data,'$.status')='pending'",(tenant,target)).fetchall()
            for row in rows:store._put(db,tenant,'workspaceinvite',dict(json.loads(row['data']),status='revoked',revoked_at=stamp),row['id'])
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,stamp))
    return {'id':target,'removed':operation=='member.remove','role':data.get('role') if operation=='member.role' else None}
