"""Transactional internal routing for customer AI handoffs; no external effects."""
import time
from team_operations import policy_pool,assignment


def active_member(db,tenant,user):
    return bool(user and db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,user)).fetchone())


def select_owner(store,db,tenant,assistant,contact):
    if active_member(db,tenant,contact.get('assignee')):return contact['assignee'],{'strategy':'preserved'}
    if assistant.get('handoff_strategy','fixed') in ['least_busy','round_robin']:
        pool,loads,policy=policy_pool(store,db,tenant,assistant,contact)
        if pool:
            if assistant['handoff_strategy']=='round_robin':
                cursor=next((value for value in store._list(db,tenant,'airoutingcursor') if value['assistant_id']==assistant['id']),{})
                previous=cursor.get('last_user') if cursor.get('version')==assistant.get('version',0) else None
                owner=pool[(pool.index(previous)+1)%len(pool)] if previous in pool else pool[0]
                store._put(db,tenant,'airoutingcursor',{'assistant_id':assistant['id'],'last_user':owner,'version':assistant.get('version',0)},cursor.get('id'))
                return owner,dict(policy,strategy='round_robin')
            owner=min(pool,key=lambda user:loads.get(user,0))
            return owner,dict(policy,strategy='least_busy',assigned_load=loads.get(owner,0))
        if assistant.get('handoff_team_id') or assistant.get('respect_availability') or assistant.get('handoff_max_open'):
            return '',dict(policy,strategy='unassigned',reason='No team members satisfy the current routing policy.')
        owner=assistant.get('owner','')
        return (owner if active_member(db,tenant,owner) else ''),{'strategy':'administrator_fallback','reason':'No configured pool members remain in this workspace.'}
    candidates=[user for user in [assistant.get('handoff_assignee'),assistant.get('owner')] if active_member(db,tenant,user)]
    if assistant.get('respect_availability') or assistant.get('handoff_max_open'):
        candidates,loads,policy=policy_pool(store,db,tenant,dict(assistant,handoff_pool=candidates),contact)
        if not candidates:return '',dict(policy,strategy='unassigned',reason='No configured teammate satisfies the current routing policy.')
    owner=next(iter(candidates),'')
    return owner,{'strategy':'fixed' if owner and owner==assistant.get('handoff_assignee') else 'administrator_fallback'}


def handoff(store,db,tenant,assistant,contact,job,reason):
    contact=dict(contact);contact.pop('outgoing_watch',None)
    stamp=int(time.time());reason=reason[:500]
    owner,routing=select_owner(store,db,tenant,assistant,contact)
    task_id=''
    if assistant.get('handoff_task'):
        # The caller holds a write transaction; job identity prevents duplicates.
        old=db.execute("SELECT id FROM entities WHERE tenant=? AND kind='task' AND json_extract(data,'$.source')='customer_ai_handoff' AND json_extract(data,'$.job_id')=?",(tenant,job['id'])).fetchone()
        if old:task_id=old['id']
        else:
            task=store._put(db,tenant,'task',dict(title='Review AI handoff',contact_id=contact['id'],owner=owner,created=stamp,updated=stamp,deal_id='',due=0,status='open',completed_at=0,source='customer_ai_handoff',job_id=job['id']))
            task_id=task['id']
    assignment(store,db,tenant,contact['id'],contact.get('assignee'),owner,'Customer AI','ai_handoff',assistant.get('handoff_team_id',''),routing)
    updated=store._put(db,tenant,'contact',dict(contact,status='pending',automation_hold=True,assignee=owner,handoff=dict(active=True,reason=reason,created=stamp,job_id=job['id'],task_id=task_id,source='customer_ai',routing=routing)),contact['id'])
    store._message(db,tenant,contact['id'],'AI handoff: '+reason,'note','internal')
    return updated
