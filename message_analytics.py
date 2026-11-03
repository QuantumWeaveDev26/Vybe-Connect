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


def report(store,ctx,start,end):
    first,last=dates(start,end);tenant=ctx['tenant_id'];lower=int(datetime.combine(first,datetime.min.time(),timezone.utc).timestamp());upper=int(datetime.combine(last+timedelta(days=1),datetime.min.time(),timezone.utc).timestamp())
    buckets={str(first+timedelta(days=n)):dict(day=str(first+timedelta(days=n)),inbound=0,**{s:0 for s in STATES}) for n in range((last-first).days+1)}
    scope="tenant=? AND ts>=? AND ts<? AND ((direction='in' AND status='received') OR (direction='out' AND status IN ('accepted','sent','delivered','read','failed','unknown','sending')))"
    with store.db() as db:
        db.execute('BEGIN')
        if not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,ctx['user']['id'])).fetchone():raise ReportError('Workspace access denied.',403)
        rows=db.execute("SELECT strftime('%Y-%m-%d',ts,'unixepoch') AS day,direction,status,COUNT(*) AS amount FROM messages WHERE "+scope+' GROUP BY day,direction,status',(tenant,lower,upper)).fetchall()
        contacts=db.execute('SELECT COUNT(DISTINCT contact) FROM messages WHERE '+scope,(tenant,lower,upper)).fetchone()[0]
    for row in rows:buckets[row['day']]['inbound' if row['direction']=='in' else row['status']]+=row['amount']
    totals={key:sum(day[key] for day in buckets.values()) for key in ['inbound',*STATES]};totals['outbound']=sum(totals[s] for s in STATES)
    return dict(start=start,end=end,timezone='UTC',generated=int(time.time()),days=list(buckets.values()),totals=totals,contacts=contacts)
