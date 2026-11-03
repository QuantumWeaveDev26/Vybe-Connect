"""Agent configuration and durable execution leases. No provider calls here."""
from crm import text
from ai import ai_status
from agent_permissions import allowed_actions,validate_actions

INTERVALS=(3600,86400,604800)


def configure_agent(store,db,ctx,action,data,stamp):
    tenant=ctx['tenant_id']
    old=store._get(db,tenant,'aiagent',data['id']) if data.get('id') else {}
    if action=='aiagent.save':
        if old.get('archived'):raise ValueError('Restore the agent before editing it.')
        result=dict(old,name=text(data.get('name'),'Agent name',100),instructions=text(data.get('instructions'),'Instructions',6000),mode='review_first',created=old.get('created',stamp),updated=stamp)
        result.update(allowed_actions=validate_actions(data.get('allowed_actions',allowed_actions(old))),version=old.get('version',0)+1)
    elif action=='aiagent.archive':
        archived=data.get('archived',True)
        if not old or not isinstance(archived,bool):raise ValueError('Choose an agent and a valid archive state.')
        result=dict(old,archived=archived,schedule_enabled=False,next_run=0,updated=stamp)
        if archived:
            db.execute('DELETE FROM agent_leases WHERE tenant=? AND agent=?',(tenant,old['id']))
            for run in store._list(db,tenant,'airun'):
                if run['agent_id']==old['id'] and run['status']=='running':
                    store._put(db,tenant,'airun',dict(run,status='interrupted',error='Agent was archived during this run.',finished=stamp),run['id'])
                    result.update(last_run=stamp,last_status='interrupted',last_error='Agent was archived during this run.')
    else:
        if not old or old.get('archived'):raise ValueError('Choose an active agent.')
        enabled=data.get('enabled')
        if not isinstance(enabled,bool):raise ValueError('Schedule enabled must be true or false.')
        interval=data.get('interval',old.get('interval',86400))
        if type(interval) is not int or interval not in INTERVALS:raise ValueError('Choose an hourly, daily or weekly interval.')
        status=ai_status(tenant)
        if enabled and not (status['enabled'] and status['configured']):raise ValueError('An AI model must be configured and enabled before scheduling agents. OpenAI also requires workspace paid-call approval.')
        result=dict(old,schedule_enabled=enabled,interval=interval,next_run=stamp+interval if enabled else 0,schedule_owner=ctx['user']['id'],updated=stamp)
    return store._put(db,tenant,'aiagent',result,data.get('id'))


def claim_lease(store,db,tenant,agent_id,token,stamp):
    agent=store._get(db,tenant,'aiagent',agent_id)
    if agent.get('archived'):raise ValueError('This agent is archived. Restore it before running.')
    current=db.execute('SELECT token,expires FROM agent_leases WHERE tenant=? AND agent=?',(tenant,agent_id)).fetchone()
    if current and current['expires']>stamp:raise ValueError('This agent is already running. Wait for its current run to finish.')
    for run in store._list(db,tenant,'airun'):
        if run['agent_id']==agent_id and run['status']=='running':
            store._put(db,tenant,'airun',dict(run,status='interrupted',error='The previous worker lost its execution lease.',finished=stamp),run['id'])
    db.execute('INSERT INTO agent_leases VALUES(?,?,?,?) ON CONFLICT(tenant,agent) DO UPDATE SET token=excluded.token,expires=excluded.expires',(tenant,agent_id,token,stamp+300))


def lease_valid(db,tenant,agent,token,stamp):
    return bool(db.execute('SELECT 1 FROM agent_leases WHERE tenant=? AND agent=? AND token=? AND expires>?',(tenant,agent,token,stamp)).fetchone())


def scheduled_context(db,tenant,owner):
    user=db.execute('SELECT id,name,email FROM users WHERE id=?',(owner,)).fetchone()
    workspace=db.execute('SELECT t.id,t.name,m.role FROM tenants t JOIN members m ON m.tenant=t.id WHERE t.id=? AND m.user=?',(tenant,owner)).fetchone()
    if not user or not workspace or workspace['role']!='admin':return None
    return {'user':dict(user),'tenant_id':tenant,'workspace':dict(workspace),'workspaces':[dict(workspace)],'role':'admin'}
