"""Scoped teams, explicit availability and transactional human routing."""
import json
import time


def availability_rows(store,db,tenant):
    return store._list(db,tenant,'memberavailability')


def team_record(store,db,tenant,identifier):
    row=db.execute("SELECT data FROM entities WHERE tenant=? AND kind='routingteam' AND id=?",(tenant,identifier)).fetchone()
    return dict(json.loads(row['data']),id=identifier) if row else None


def policy_pool(store,db,tenant,assistant,contact):
    team_id=assistant.get('handoff_team_id','');team=team_record(store,db,tenant,team_id) if team_id else None
    configured=(team['members'] if team and team['enabled'] else []) if team_id else assistant.get('handoff_pool',[])
    members={r['user'] for r in db.execute('SELECT user FROM members WHERE tenant=?',(tenant,))}
    pool=[u for u in dict.fromkeys(configured) if u in members]
    rows=db.execute("""SELECT json_extract(data,'$.assignee') AS owner,COUNT(*) AS load FROM entities
        WHERE tenant=? AND kind='contact' AND id<>? AND json_extract(data,'$.status') IN ('open','pending')
        GROUP BY json_extract(data,'$.assignee')""",(tenant,contact['id'])).fetchall()
    loads={r['owner']:r['load'] for r in rows}
    if assistant.get('respect_availability'):
        stamp=int(time.time());available={r['user'] for r in availability_rows(store,db,tenant) if r['status']=='available' and r['until']>stamp}
        pool=[u for u in pool if u in available]
    limit=assistant.get('handoff_max_open',0)
    if limit:pool=[u for u in pool if loads.get(u,0)<limit]
    return pool,loads,{'team_id':team_id,'eligible_members':len(pool),'availability_required':bool(assistant.get('respect_availability')),'max_open':limit}


def assignment(store,db,tenant,contact,before,after,actor,source,team_id='',routing=None):
    if before==after:return
    store._put(db,tenant,'assignmentevent',{'contact_id':contact,'from':before or '', 'to':after or '', 'actor':actor,'source':source,'team_id':team_id,'routing':routing or {},'created':int(time.time())})


def state(store,db,tenant):
    stamp=int(time.time());members={r['user'] for r in db.execute('SELECT user FROM members WHERE tenant=?',(tenant,))}
    availability=[]
    for record in availability_rows(store,db,tenant):
        if record['user'] not in members:continue
        record=dict(record)
        if record['status']=='available' and record['until']<=stamp:record.update(status='away',expired=True)
        availability.append(record)
    rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='assignmentevent' ORDER BY rowid DESC LIMIT 100",(tenant,)).fetchall()
    workload=db.execute("""SELECT json_extract(data,'$.assignee') AS user,COUNT(*) AS assigned FROM entities WHERE tenant=?
        AND kind='contact' AND json_extract(data,'$.status') IN ('open','pending') GROUP BY json_extract(data,'$.assignee')""",(tenant,)).fetchall()
    return {'teams':store._list(db,tenant,'routingteam'),'availability':availability,'workload':[dict(r) for r in workload],'assignments':[dict(json.loads(r['data']),id=r['id']) for r in rows]}


def removed_member(store,db,tenant,user):
    for team in store._list(db,tenant,'routingteam'):
        if user in team['members']:store._put(db,tenant,'routingteam',dict(team,members=[u for u in team['members'] if u!=user],version=team['version']+1,updated=int(time.time())),team['id'])
    db.execute("DELETE FROM entities WHERE tenant=? AND kind='memberavailability' AND json_extract(data,'$.user')=?",(tenant,user))


def action(store,ctx,operation,data):
    from store import Problem,required
    from ai_handoff import select_owner
    tenant=ctx['tenant_id'];user=ctx['user']['id'];stamp=int(time.time())
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        member=db.execute('SELECT role FROM members WHERE tenant=? AND user=?',(tenant,user)).fetchone()
        if not member:raise Problem('Workspace access changed.',403)
        if operation=='team.save':
            if ctx['role']!='admin' or member['role']!='admin':raise Problem('Administrator access required.',403)
            old=store._get(db,tenant,'routingteam',data['id']) if data.get('id') else {}
            if old and (type(data.get('version')) is not int or data['version']!=old['version']):raise Problem('Team changed. Refresh before editing.',409)
            name=required(data.get('name'),'Team name',100);members=data.get('members');enabled=data.get('enabled',True)
            if not isinstance(members,list) or len(members)>100 or any(not isinstance(u,str) or not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,u)).fetchone() for u in members):raise Problem('Select up to 100 current workspace members.')
            if type(enabled) is not bool:raise Problem('Team activation must be true or false.')
            teams=store._list(db,tenant,'routingteam')
            if not old and len(teams)>=50:raise Problem('Use up to 50 teams per workspace.')
            if any(t['id']!=old.get('id') and t['name'].casefold()==name.casefold() for t in teams):raise Problem('A team already uses this name.',409)
            result=store._put(db,tenant,'routingteam',{'name':name,'members':list(dict.fromkeys(members)),'enabled':enabled,'version':old.get('version',0)+1,'updated':stamp},old.get('id'))
        elif operation=='availability.set':
            status=data.get('status');minutes=data.get('minutes',240)
            if status not in ['available','away','offline']:raise Problem('Choose available, away or offline.')
            if type(minutes) is not int or not 15<=minutes<=480:raise Problem('Availability lasts 15–480 whole minutes.')
            old=next((r for r in availability_rows(store,db,tenant) if r['user']==user),{})
            result=store._put(db,tenant,'memberavailability',{'user':user,'status':status,'until':stamp+minutes*60 if status=='available' else 0,'updated':stamp},old.get('id'))
        elif operation=='chat.route':
            contact=store._get(db,tenant,'contact',data.get('id'));team=team_record(store,db,tenant,data.get('team_id'))
            if not team or not team['enabled']:raise Problem('Choose an enabled team in this workspace.')
            if contact.get('assignee'):raise Problem('Clear the current assignment before team routing.',409)
            strategy=data.get('strategy','least_busy');respect=data.get('respect_availability',True);limit=data.get('max_open',0)
            if strategy not in ['least_busy','round_robin'] or type(respect) is not bool or type(limit) is not int or not 0<=limit<=1000:raise Problem('Use least-busy/round-robin routing and a workload limit of 0–1,000.')
            policy={'id':'team:'+team['id'],'version':team['version'],'handoff_strategy':strategy,'handoff_team_id':team['id'],'respect_availability':respect,'handoff_max_open':limit}
            owner,routing=select_owner(store,db,tenant,policy,contact)
            updated=dict(contact,assignee=owner,status='pending',automation_hold=True,last_team_routing=dict(routing,created=stamp))
            updated.pop('flow_session',None);updated.pop('outgoing_watch',None)
            result=store._put(db,tenant,'contact',updated,contact['id'])
            assignment(store,db,tenant,contact['id'],'',owner,user,'team_route',team['id'],routing)
        else:raise Problem('Unknown team operation.',404)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,stamp))
        return result
