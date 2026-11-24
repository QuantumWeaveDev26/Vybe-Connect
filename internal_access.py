"""Private exact-workspace team access; never inferred from public account data."""
import os,re
from datetime import datetime,timezone


def is_internal(tenant):
    raw=os.environ.get('TW_INTERNAL_WORKSPACES','').strip()
    if not raw:return False
    values=[value.strip() for value in raw.split(',')]
    if len(values)>20 or not all(re.fullmatch(r'[a-f0-9]{16}',value) for value in values):return False
    return isinstance(tenant,str) and tenant in values


def ai_grant(db,tenant):
    # Free software access is not authorization to incur model-provider charges.
    limit=os.environ.get('TW_INTERNAL_AI_REQUESTS_PER_MONTH','50')
    allowed=is_internal(tenant) and os.environ.get('TW_INTERNAL_AI_ENABLED','false').lower()=='true'
    if not re.fullmatch(r'[0-9]{1,4}',limit) or not 1<=int(limit)<=1000:allowed=False
    if not allowed:return {'active':False,'internal_use':True,'remaining':0,'limit':0}
    now=datetime.now(timezone.utc);month=now.month%12+1;year=now.year+(now.month==12)
    end=int(datetime(year,month,1,tzinfo=timezone.utc).timestamp())
    cycle='internal:'+now.strftime('%Y-%m')
    row=db.execute('SELECT requests FROM platform_ai_usage WHERE tenant=? AND cycle=?',(tenant,cycle)).fetchone();used=row[0] if row else 0
    return {'active':True,'internal_use':True,'cycle':cycle,'limit':int(limit),'used':used,'remaining':max(0,int(limit)-used),'expires':end}
