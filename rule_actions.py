"""Bounded local rule actions with preflight dependency checks and no providers."""
import copy
from team_operations import assignment
import json
import re
import time
from contact_segments import matches

LIMITS={'draft':4096,'tag':60,'untag':60,'assign':64,'status':20,'attribute':1000,'task':150}


class RuleError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def validate(store,db,tenant,actions,segment_id=''):
    if not isinstance(actions,list) or not 1<=len(actions)<=10:raise RuleError('Use one to ten local rule actions.')
    normalized=[]
    for ordinal,action in enumerate(actions):
        if not isinstance(action,dict):raise RuleError('Choose supported local rule actions.')
        kind=action.get('type')
        if not isinstance(kind,str):raise RuleError('Choose a supported action type.')
        if kind=='handoff':
            if set(action)!={'type'} or ordinal!=len(actions)-1:raise RuleError('Human handoff must be the final action.')
        elif kind in LIMITS:
            keys={'type','value','field'} if kind=='attribute' else {'type','value'}
            value=action.get('value')
            if set(action)!=keys or not isinstance(value,str) or not value.strip() or len(value)>LIMITS[kind]:raise RuleError('Each action needs a bounded value.')
            if kind=='assign' and not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,value)).fetchone():raise RuleError('Choose an assignee in this workspace.')
            if kind=='status' and value not in ['open','pending','solved']:raise RuleError('Choose open, pending or solved status.')
            if kind=='attribute' and (not isinstance(action.get('field'),str) or not re.fullmatch(r'[A-Za-z0-9_ -]{1,60}',action['field'])):raise RuleError('Choose a bounded custom attribute name.')
        else:raise RuleError('Unsupported rule action. Provider sends and consent changes are not allowed.')
        normalized.append(copy.deepcopy(action))
    if not isinstance(segment_id,str):raise RuleError('Choose a saved segment.')
    if segment_id and not any(s['id']==segment_id for s in store._list(db,tenant,'segment')):raise RuleError('Saved segment is not available in this workspace.',404)
    return normalized


def execute(store,db,tenant,rule,contact,message):
    actions=rule.get('actions',[{'type':'draft','value':rule['reply']}]);segment_id=rule.get('segment_id','')
    def record(status,reason=''):
        store._put(db,tenant,'ruleexecution',dict(rule_id=rule['id'],contact_id=contact['id'],event=message.get('event','incoming_message'),source_id=message.get('event_id') or message.get('id',''),status=status,reason=reason,actions=[a.get('type') for a in actions if isinstance(a,dict)],created=int(time.time())))
    try:actions=validate(store,db,tenant,actions,segment_id)
    except RuleError:
        record('blocked','Rule dependency or configuration is unavailable.')
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'Rule engine','rule.blocked.dependency',int(time.time())));return False
    if segment_id:
        segment=next(s for s in store._list(db,tenant,'segment') if s['id']==segment_id)
        if not matches(contact,segment['criteria']):return False
    attributes=copy.deepcopy(contact.get('attributes',{}));tags=list(contact.get('tags',[]))
    for action in actions:
        if action['type']=='attribute':attributes[action['field']]=action['value']
        elif action['type']=='untag':tags=[tag for tag in tags if tag.casefold()!=action['value'].casefold()]
        elif action['type']=='tag' and action['value'].casefold() not in {tag.casefold() for tag in tags}:tags.append(action['value'])
    if len(attributes)>50 or len(json.dumps(attributes))>10000 or len(tags)>25:
        record('blocked','Contact tag or attribute capacity exceeded.')
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'Rule engine','rule.blocked.contact_capacity',int(time.time())));return False
    c=copy.deepcopy(contact);c.setdefault('attributes',{});c.setdefault('tags',[]);stamp=int(time.time())
    for action in actions:
        kind=action['type'];value=action.get('value','')
        if kind=='draft':store._message(db,tenant,c['id'],value.replace('{{name}}',c['name'])[:4096],'out','draft')
        elif kind=='tag':
            if value.casefold() not in {tag.casefold() for tag in c['tags']}:c['tags']=(c['tags']+[value])[:25]
        elif kind=='untag':c['tags']=[tag for tag in c['tags'] if tag.casefold()!=value.casefold()]
        elif kind=='attribute':c['attributes'][action['field']]=value
        elif kind=='assign':c['assignee']=value
        elif kind=='status':c['status']=value
        elif kind=='task':
            owner=c.get('assignee','')
            if owner and not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(tenant,owner)).fetchone():owner=''
            store._put(db,tenant,'task',dict(title=value,contact_id=c['id'],owner=owner,created=stamp,updated=stamp,deal_id='',due=0,status='open',completed_at=0,source='automation_rule',rule_id=rule['id'],message_id=message.get('id',''),event_id=message.get('event_id','')))
        elif kind=='handoff':
            c.update(status='pending',automation_hold=True);c.pop('flow_session',None);c.pop('outgoing_watch',None)
            store._message(db,tenant,c['id'],'Rule handoff: '+rule['name'],'note','internal')
    assignment(store,db,tenant,c['id'],contact.get('assignee'),c.get('assignee'),'Rule engine','rule',routing={'rule_id':rule['id']})
    store._put(db,tenant,'contact',c,c['id'])
    record('applied')
    db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'Rule engine','rule.execute',stamp))
    return True
