"""Working interval adaptation of ChatbotX MIT code; see third_party/chatbotx/NOTICE.md."""
from datetime import datetime,date,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import time


def wall_instant(day,minute,zone):
    # Upstream policy: first occurrence of an ambiguous minute, transition instant for a gap.
    wall=datetime.combine(day,datetime.min.time(),timezone.utc).timestamp()+minute*60
    offset=lambda ts:datetime.fromtimestamp(ts,zone).utcoffset().total_seconds()
    before=offset(wall-86400);after=offset(wall+86400)
    if before==after:return int(wall-before)
    candidates=[wall-o for o in (before,after) if offset(wall-o)==o]
    if candidates:return int(min(candidates))
    low=int((wall-86400)//60);high=int((wall+86400)//60)
    while high-low>1:
        mid=(low+high)//2
        if offset(mid*60)==before:low=mid
        else:high=mid
    return high*60


def ranges(schedule,day):
    override=schedule.get('overrides',{}).get(day.isoformat())
    return override if override is not None else [[r['start'],r['end']] for r in schedule['intervals'] if r['weekday']==(day.weekday()+1)%7]


def spans(schedule,start,end=None):
    zone=ZoneInfo(schedule['timezone']);day=datetime.fromtimestamp(start,zone).date()
    for _ in range(367):
        for first,last in ranges(schedule,day):
            left=wall_instant(day,first,zone);right=wall_instant(day,last,zone)
            if right>start and (end is None or left<end):yield max(start,left),right if end is None else min(end,right)
        day+=timedelta(days=1)
        if end is not None and wall_instant(day,0,zone)>=end:return


def seconds_between(schedule,start,end):
    if end<=start:return 0
    if end-start>366*86400:raise ValueError('Timing span exceeds one year.')
    return sum(max(0,b-a) for a,b in spans(schedule,start,end))


def deadline(schedule,start,seconds):
    for a,b in spans(schedule,start):
        if b-a>=seconds:return a+seconds
        seconds-=max(0,b-a)
    return None


def validate(data):
    from store import Problem
    try:ZoneInfo(data.get('timezone',''))
    except (ZoneInfoNotFoundError,ValueError,TypeError):raise Problem('Choose a valid IANA timezone, such as Asia/Kolkata.') from None
    if type(data.get('enabled')) is not bool:raise Problem('Choose whether SLA tracking is enabled.')
    minutes=data.get('response_minutes',60)
    if type(minutes) is not int or not 1<=minutes<=1440:raise Problem('Response target must be 1–1,440 working minutes.')
    intervals=data.get('intervals');overrides=data.get('overrides',{})
    if not isinstance(intervals,list) or not 1<=len(intervals)<=28 or not isinstance(overrides,dict) or len(overrides)>100:raise Problem('Use up to 28 weekly intervals and 100 date overrides.')
    weekly={i:[] for i in range(7)}
    def pair(a,b):
        if type(a) is not int or type(b) is not int or not 0<=a<b<=1440:raise Problem('Use non-overlapping opening and closing minutes within each day.')
        return [a,b]
    for r in intervals:
        if not isinstance(r,dict) or type(r.get('weekday')) is not int or r['weekday'] not in weekly:raise Problem('Invalid weekday.')
        weekly[r['weekday']].append(pair(r.get('start'),r.get('end')))
    def ordered(values):
        values=sorted(values)
        if len(values)>4 or any(b[0]<a[1] for a,b in zip(values,values[1:])):raise Problem('Use up to four non-overlapping intervals per day.')
        return values
    for values in weekly.values():ordered(values)
    clean={}
    for key,values in overrides.items():
        try:
            if date.fromisoformat(key).isoformat()!=key:raise ValueError()
        except (ValueError,TypeError):raise Problem('Override dates use YYYY-MM-DD.') from None
        if not isinstance(values,list) or any(not isinstance(v,list) or len(v)!=2 for v in values):raise Problem('Use opening/closing minute pairs, or an empty list for a holiday.')
        clean[key]=ordered([pair(*v) for v in values])
    return {'enabled':data['enabled'],'timezone':data['timezone'],'response_minutes':minutes,'intervals':[{'weekday':day,'start':a,'end':b} for day,values in weekly.items() for a,b in ordered(values)],'overrides':clean}


def action(store,ctx,data):
    from embedded_signup import administrator
    administrator(store,ctx);values=validate(data)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');administrator(store,ctx)
        old=store._list(db,ctx['tenant_id'],'businesshours')
        result=store._put(db,ctx['tenant_id'],'businesshours',dict(values,updated=int(time.time())),old[0]['id'] if old else None)
        if not values['enabled']:
            for w in store._list(db,ctx['tenant_id'],'slawindow'):
                if w['status']=='waiting':store._put(db,ctx['tenant_id'],'slawindow',dict(w,status='cancelled'),w['id'])
        return result


def inbound(store,db,tenant,contact,message):
    schedules=store._list(db,tenant,'businesshours')
    if not schedules or not schedules[0]['enabled']:return
    if any(w['contact_id']==contact['id'] and w['status']=='waiting' for w in store._list(db,tenant,'slawindow')):return
    stamp=message['ts']
    if stamp<contact.get('last_real_inbound',0):return
    last=db.execute("SELECT MAX(ts) FROM messages WHERE tenant=? AND contact=? AND direction='out' AND status IN ('accepted','sent','delivered','read')",(tenant,contact['id'])).fetchone()[0]
    if last is not None and last>stamp:return
    snapshot={k:schedules[0][k] for k in ('timezone','intervals','overrides','response_minutes')}
    due=deadline(snapshot,stamp,snapshot['response_minutes']*60)
    store._put(db,tenant,'slawindow',{'contact_id':contact['id'],'inbound_id':message['id'],'started':stamp,'due':due,'status':'waiting','schedule':snapshot})


def accepted(store,db,tenant,contact_id,message_id,stamp):
    for w in store._list(db,tenant,'slawindow'):
        if w['contact_id']==contact_id and w['status']=='waiting' and stamp>=w['started']:
            try:working=seconds_between(w['schedule'],w['started'],stamp)
            except ValueError:working=None
            store._put(db,tenant,'slawindow',dict(w,status='answered',outbound_id=message_id,answered=stamp,working_seconds=working,wall_seconds=stamp-w['started'],met=stamp<=w['due'] if w.get('due') is not None else None),w['id'])


def state(store,db,tenant):
    config=store._list(db,tenant,'businesshours');windows=store._list(db,tenant,'slawindow');now=int(time.time())
    current=config[0] if config else {'enabled':False,'timezone':'Asia/Kolkata','response_minutes':60,'intervals':[{'weekday':d,'start':540,'end':1020} for d in range(1,6)],'overrides':{}}
    completed=[w for w in windows if w['status']=='answered' and w.get('met') is not None]
    return {'configuration':current,'waiting':[dict(w,overdue=w.get('due') is not None and w['due']<now) for w in windows if w['status']=='waiting'],'answered':len(completed),'met':sum(w['met'] for w in completed),'history':windows[-100:]}
