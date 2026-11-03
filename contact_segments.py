"""Bounded typed contact filters and dynamic, consent-aware campaign audiences."""
import math
import re
import time
from datetime import datetime,timezone
from crm import text

FIELDS={'name','phone','tags','optin','status','assignee','source','last_inbound'}
OPS={'eq','ne','contains','not_contains','starts_with','ends_with','in','not_in','gt','gte','lt','lte','exists','not_exists','empty','not_empty','date_before','date_after'}
MISSING=object()


class SegmentError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def timestamp(value):
    if type(value) in [int,float] and math.isfinite(value):return value
    if not isinstance(value,str):raise ValueError('A date is required.')
    date=datetime.fromisoformat(value.replace('Z','+00:00'))
    if date.tzinfo is None:
        if 'T' in value or ' ' in value:raise ValueError('Date-time values require a timezone offset.')
        date=date.replace(tzinfo=timezone.utc)
    return date.timestamp()


def validate(criteria,depth=0,counter=None):
    counter=counter if counter is not None else [0]
    if not isinstance(criteria,dict) or depth>3:raise SegmentError('Use valid criteria with at most three nested groups.')
    if 'rules' in criteria:
        rules=criteria['rules']
        if set(criteria)!={'mode','rules'} or criteria['mode'] not in ['all','any'] or not isinstance(rules,list) or not 1<=len(rules)<=20:raise SegmentError('Each all/any group needs one to twenty conditions.')
        return {'mode':criteria['mode'],'rules':[validate(rule,depth+1,counter) for rule in rules]}
    counter[0]+=1
    if counter[0]>20:raise SegmentError('Use up to twenty conditions.')
    field=criteria.get('field');operator=criteria.get('operator')
    if not isinstance(field,str) or field not in FIELDS and not re.fullmatch(r'attributes\.[A-Za-z0-9_ -]{1,60}',field):raise SegmentError('Choose a contact field or custom attribute.')
    if not isinstance(operator,str) or operator not in OPS or set(criteria)-{'field','operator','value'}:raise SegmentError('Choose a supported filter operator.')
    if field=='tags' and operator not in ['contains','not_contains','in','not_in','exists','not_exists','empty','not_empty']:raise SegmentError('Tag conditions use membership, empty or existence comparisons.')
    result={'field':field,'operator':operator}
    if operator in ['exists','not_exists','empty','not_empty']:return result
    value=criteria.get('value',MISSING)
    if operator in ['in','not_in']:
        if not isinstance(value,list) or not 1<=len(value)<=50 or any(type(v) not in [str,int,float,bool] or isinstance(v,str) and len(v)>500 for v in value):raise SegmentError('Use a list of one to fifty primitive values.')
    elif type(value) not in [str,int,float,bool] or isinstance(value,str) and len(value)>500:raise SegmentError('A bounded text, number or boolean filter value is required.')
    if field=='optin' and (operator not in ['eq','ne'] or type(value) is not bool):raise SegmentError('Consent conditions require a true/false equality comparison.')
    if operator in ['gt','gte','lt','lte'] and (type(value) not in [int,float] or not math.isfinite(value)):raise SegmentError('Numeric conditions require a finite number.')
    if operator in ['date_before','date_after']:
        try:timestamp(value)
        except (ValueError,TypeError,OverflowError):raise SegmentError('Use an ISO date or date-time with an explicit timezone offset.') from None
    return dict(result,value=value)


def equal(a,b):
    if type(a) is bool or type(b) is bool:return type(a) is type(b) and a==b
    if isinstance(a,str) and isinstance(b,str):return a.casefold()==b.casefold()
    if type(a) in [int,float] and type(b) in [int,float]:return a==b
    return False


def matches(contact,criteria):
    if 'rules' in criteria:return (all if criteria['mode']=='all' else any)(matches(contact,r) for r in criteria['rules'])
    field=criteria['field'];operator=criteria['operator'];value=criteria.get('value')
    actual=contact.get('attributes',{}).get(field[11:],MISSING) if field.startswith('attributes.') else contact.get(field,MISSING)
    if operator=='exists':return actual is not MISSING
    if operator=='not_exists':return actual is MISSING
    if operator=='empty':return actual is MISSING or actual is None or actual=='' or actual==[]
    if operator=='not_empty':return actual is not MISSING and actual is not None and actual!='' and actual!=[]
    if actual is MISSING:return False
    if operator in ['eq','ne']:return equal(actual,value) if operator=='eq' else not equal(actual,value)
    if operator in ['in','not_in']:
        found=any(equal(a,v) for a in (actual if isinstance(actual,list) else [actual]) for v in value);return found if operator=='in' else not found
    if operator in ['contains','not_contains','starts_with','ends_with']:
        if isinstance(actual,list):found=any(equal(a,value) for a in actual)
        elif isinstance(actual,str) and isinstance(value,str):
            left=actual.casefold();right=value.casefold();found=left.startswith(right) if operator=='starts_with' else left.endswith(right) if operator=='ends_with' else right in left
        else:return False
        return not found if operator=='not_contains' else found
    try:
        if operator in ['date_before','date_after']:left=timestamp(actual);right=timestamp(value);return left<right if operator=='date_before' else left>right
        if type(actual) is bool:return False
        left=float(actual);right=float(value)
        if not math.isfinite(left) or not math.isfinite(right):return False
        return left>right if operator=='gt' else left>=right if operator=='gte' else left<right if operator=='lt' else left<=right
    except (ValueError,TypeError,OverflowError):return False


def audience(store,db,tenant,campaign):
    criteria=None
    if campaign.get('segment_id'):criteria=store._get(db,tenant,'segment',campaign['segment_id'])['criteria']
    return [c for c in store._list(db,tenant,'contact') if c['optin'] and (not campaign.get('tag') or campaign['tag'] in c['tags']) and (not criteria or matches(c,criteria))]


def action(store,ctx,operation,data):
    tenant=ctx['tenant_id']
    if operation!='segment.preview' and ctx['role']!='admin':raise SegmentError('Administrator access required.',403)
    with store.db() as db:
        if operation=='segment.delete':
            db.execute('BEGIN IMMEDIATE');store._get(db,tenant,'segment',data.get('id'));db.execute("DELETE FROM entities WHERE tenant=? AND kind='segment' AND id=?",(tenant,data['id']));result={'deleted':True}
        else:
            criteria=validate(data.get('criteria'))
            if operation=='segment.preview':
                contacts=[c for c in store._list(db,tenant,'contact') if matches(c,criteria)]
                return {'count':len(contacts),'opted_in':sum(c['optin'] for c in contacts),'contact_ids':[c['id'] for c in contacts[:1000]],'sample':[{k:c[k] for k in ['id','name','phone','optin']} for c in contacts[:20]],'truncated':len(contacts)>1000}
            if operation!='segment.save':raise SegmentError('Unknown segment action.',404)
            db.execute('BEGIN IMMEDIATE')
            if data.get('id'):store._get(db,tenant,'segment',data['id'])
            elif len(store._list(db,tenant,'segment'))>=30:raise SegmentError('Use up to thirty saved segments per workspace.')
            result=store._put(db,tenant,'segment',{'name':text(data.get('name'),'Segment name',100),'criteria':criteria,'updated':int(time.time())},data.get('id'))
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,int(time.time())))
    return result
