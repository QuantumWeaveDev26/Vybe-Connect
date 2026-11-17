"""Workspace aggregate reports over recorded real messages, using inclusive UTC dates."""
import re
import time
from datetime import date,datetime,timedelta,timezone

STATES=('accepted','sent','delivered','read','failed','unknown','sending')


class ReportError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def dates(start,end):
    try:
        if any(not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v) for v in [start,end]):raise ValueError()
        first=date.fromisoformat(start);last=date.fromisoformat(end)
        if not 2000<=first.year<=last.year<=2100 or not 0<=(last-first).days<366:raise ValueError()
    except (TypeError,ValueError):raise ReportError('Choose inclusive UTC dates from 2000–2100 spanning at most 366 days.') from None
    return first,last


def report(store,ctx,start,end,export=False):
    first,last=dates(start,end);tenant=ctx['tenant_id'];lower=int(datetime.combine(first,datetime.min.time(),timezone.utc).timestamp());upper=int(datetime.combine(last+timedelta(days=1),datetime.min.time(),timezone.utc).timestamp())
    buckets={str(first+timedelta(days=n)):dict(day=str(first+timedelta(days=n)),inbound=0,**{s:0 for s in STATES}) for n in range((last-first).days+1)}
    scope="tenant=? AND ts>=? AND ts<? AND ((direction='in' AND status='received') OR (direction='out' AND status IN ('accepted','sent','delivered','read','failed','unknown','sending')))"
    with store.db() as db:
        db.execute('BEGIN')
        from member_permissions import require
        require(store,ctx,'reports',db)
        if export:require(store,ctx,'exports',db)
        if not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,ctx['user']['id'])).fetchone():raise ReportError('Workspace access denied.',403)
        rows=db.execute("SELECT strftime('%Y-%m-%d',ts,'unixepoch') AS day,direction,status,COUNT(*) AS amount FROM messages WHERE "+scope+' GROUP BY day,direction,status',(tenant,lower,upper)).fetchall()
        contacts=db.execute('SELECT COUNT(DISTINCT contact) FROM messages WHERE '+scope,(tenant,lower,upper)).fetchone()[0]
        operations=operation_report(store,db,tenant,lower,upper)
    for row in rows:buckets[row['day']]['inbound' if row['direction']=='in' else row['status']]+=row['amount']
    totals={key:sum(day[key] for day in buckets.values()) for key in ['inbound',*STATES]};totals['outbound']=sum(totals[s] for s in STATES)
    result=dict(start=start,end=end,timezone='UTC',generated=int(time.time()),days=list(buckets.values()),totals=totals,contacts=contacts,operations=operations)
    if export:return {'csv':export_csv(result)}
    return result


def export_csv(result):
    import csv,io
    output=io.StringIO();writer=csv.writer(output);writer.writerow(['section','date_or_operator','metric','value'])
    def cell(value):
        text=str(value)
        return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
    for day in result['days']:
        for key in ('inbound',*STATES):writer.writerow(['traffic',day['day'],key,day[key]])
    operations=result['operations']
    for key in ('responses','awaiting_response','average_response_seconds','resolved','resolution_samples','average_resolution_seconds'):
        writer.writerow(['timing','',key,operations[key] if operations[key] is not None else ''])
    for key,value in operations['calls'].items():writer.writerow(['calls','',key,value])
    for operator in operations['operators']:
        for key in ('resolved','assignments','calls'):writer.writerow(['operator',cell(operator['name']),key,operator[key]])
    return output.getvalue()


def operation_report(store,db,tenant,lower,upper):
    """Recorded timings only. Never attribute old messages to today's assignee."""
    import json
    pending={};response_total=0;responses=0
    rows=db.execute("SELECT contact,direction,ts FROM messages WHERE tenant=? AND ts>=? AND ts<? AND ((direction='in' AND status='received') OR (direction='out' AND status IN ('accepted','sent','delivered','read'))) ORDER BY ts,rowid",(tenant,lower,upper))
    for row in rows:
        if row['direction']=='in':pending.setdefault(row['contact'],row['ts'])
        elif row['contact'] in pending:
            response_total+=max(0,row['ts']-pending.pop(row['contact']));responses+=1
    members={r['id']:{'id':r['id'],'name':r['name'],'resolved':0,'assignments':0,'calls':0} for r in db.execute('SELECT u.id,u.name FROM users u JOIN members m ON m.user=u.id WHERE m.tenant=?',(tenant,))}
    def operator(user):
        if not user:return None
        if user not in members:
            row=db.execute('SELECT name FROM users WHERE id=?',(user,)).fetchone()
            members[user]={'id':user,'name':(row['name'] if row else 'Former teammate')+' (former member)','resolved':0,'assignments':0,'calls':0}
        return members[user]
    durations=[];resolutions=0
    events=db.execute("SELECT kind,data FROM entities WHERE tenant=? AND kind IN ('conversationevent','assignmentevent','voicecall') AND json_extract(data,'$.created')>=? AND json_extract(data,'$.created')<?",(tenant,lower,upper))
    calls={'total':0,'inbound':0,'outbound':0,'connected':0,'ended':0,'rejected':0,'failed':0,'unknown':0,'duration_samples':0,'connected_seconds':0}
    for event in events:
        value=json.loads(event['data']);kind=event['kind']
        if kind=='conversationevent' and value.get('after')=='solved':
            resolutions+=1;actor=value.get('actor')
            entry=operator(actor)
            if entry:entry['resolved']+=1
            opened=value.get('opened')
            if type(opened) is int and 0<=opened<=value['created']:durations.append(value['created']-opened)
        elif kind=='assignmentevent':
            entry=operator(value.get('to'))
            if entry:entry['assignments']+=1
        elif kind=='voicecall':
            calls['total']+=1;calls['outbound' if value.get('direction')=='outbound' else 'inbound']+=1
            if value.get('status') in ('ended','rejected','failed','unknown'):calls[value['status']]+=1
            connected=value.get('connected_at');ended=value.get('ended')
            if type(connected) is int:
                calls['connected']+=1
                if type(ended) is int and ended>=connected:calls['duration_samples']+=1;calls['connected_seconds']+=ended-connected
            entry=operator(value.get('owner'))
            if entry:entry['calls']+=1
    return {'responses':responses,'awaiting_response':len(pending),'average_response_seconds':round(response_total/responses,1) if responses else None,
            'resolved':resolutions,'resolution_samples':len(durations),'average_resolution_seconds':round(sum(durations)/len(durations),1) if durations else None,
            'calls':calls,'operators':list(members.values()),'timing_basis':'Recorded events within selected UTC dates; automated replies included. Resolution durations require a recorded reopen; call durations use server-observed connection and end.'}
