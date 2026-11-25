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
    budget=os.environ.get('TW_INTERNAL_AI_BUDGET_PAISE','')
    if not re.fullmatch(r'[0-9]{1,8}',budget) or not 1<=int(budget)<=10000000:allowed=False
    if not allowed:return {'active':False,'internal_use':True,'remaining':0,'limit':0}
    now=datetime.now(timezone.utc);month=now.month%12+1;year=now.year+(now.month==12)
    end=int(datetime(year,month,1,tzinfo=timezone.utc).timestamp())
    cycle='internal:'+now.strftime('%Y-%m')
    # All approved internal workspaces share one monthly ceiling. Keep charges
    # from removed workspaces in the pool as well, so allowlist changes cannot
    # reset the spend or request count. Customer cycles never use this prefix.
    used=db.execute('SELECT COALESCE(SUM(requests),0) FROM platform_ai_usage WHERE cycle=?',(cycle,)).fetchone()[0]
    reserved=db.execute('SELECT COALESCE(SUM(reserved_paise),0) FROM internal_ai_budget WHERE cycle=?',(cycle,)).fetchone()[0]
    budget_left=max(0,int(budget)-reserved)
    return {'active':True,'internal_use':True,'cycle':cycle,'limit':int(limit),'used':used,'remaining':max(0,int(limit)-used) if budget_left>=339 else 0,'expires':end,'budget_paise':int(budget),'reserved_paise':reserved,'budget_remaining_paise':budget_left}


def reserve_budget(db,tenant,access,input_bytes):
    # Conservative reservation, not an invoice: $1/M input + $5/M output,
    # one token per UTF-8 byte, 8192 envelope tokens, max 4000 output tokens.
    # INR 120/USD includes a buffer above the verified Nov 24 rate and taxes.
    # Never refund uncertain/failed requests; all callers share this transaction.
    paise=((input_bytes+8192+4000*5)*12000+999999)//1000000
    if access['budget_remaining_paise']<paise:raise ValueError('Your team AI monthly spending limit is reached. Ask the operator before increasing it.')
    db.execute('INSERT INTO internal_ai_budget VALUES(?,?,?) ON CONFLICT(tenant,cycle) DO UPDATE SET reserved_paise=reserved_paise+excluded.reserved_paise',(tenant,access['cycle'],paise))
