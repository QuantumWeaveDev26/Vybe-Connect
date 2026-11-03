"""Strict proposals from a local model; only humans can apply allowed local actions."""
from team_operations import assignment
import hashlib
import json
import time
from crm import text, member, crm_action
from agent_permissions import allowed_actions

CONTRACT={
    'response_format':{'summary':'short factual summary','findings':[{'title':'short title','details':'reason and uncertainty','contact_id':'a supplied contact ID, or empty for an account observation','evidence_ids':['supplied message IDs supporting this contact finding'],'action':None}]},
    'allowed_proposals':{'tag':{'type':'tag','tag':'short tag'},'assign':{'type':'assign','owner':'supplied member ID'},'note':{'type':'note','body':'internal note'},'draft_reply':{'type':'draft_reply','body':'unsent reply draft'},'task':{'type':'task','title':'follow-up task'}},
    'rules':'Return only JSON, at most 12 findings. Use action:null for informational findings. Every proposed mutation requires a sampled contact ID and at least one supplied message ID from that contact. Proposals are not executed by you. Do not propose sending, billing, blocking, deleting, arbitrary code, API requests or unsupported actions. Give an empty findings array when evidence is insufficient. Never invent IDs. Only use observed facts; report sample limitations.'
}


def fingerprint(db,tenant,contact):
    last=db.execute('SELECT id FROM messages WHERE tenant=? AND contact=? ORDER BY rowid DESC LIMIT 1',(tenant,contact['id'])).fetchone()
    return captured_fingerprint(contact,last['id'] if last else None)


def captured_fingerprint(contact,last_message):
    data={'contact':contact,'last_message':last_message}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def parse_findings(answer,context):
    if not isinstance(answer,str) or len(answer)>20000:raise ValueError('Analysis returned an oversized or invalid response.')
    value=answer.strip()
    if value.startswith('```json') and value.endswith('```'):value=value[7:-3].strip()
    try:data=json.loads(value)
    except (ValueError,TypeError):raise ValueError('Analysis must return valid JSON; no findings were applied.') from None
    if not isinstance(data,dict) or not isinstance(data.get('findings'),list) or len(data['findings'])>12:raise ValueError('Analysis must return up to 12 structured findings.')
    summary=text(data.get('summary'),'Analysis summary',2000)
    conversations={c['contact_id']:c for c in context['recent_conversations']}
    members={m['id'] for m in context['team_members']}
    findings=[]
    for f in data['findings']:
        if not isinstance(f,dict):raise ValueError('Each finding must be an object.')
        contact=f.get('contact_id') or '';references=f.get('evidence_ids',[]);proposal=f.get('action')
        if not isinstance(contact,str) or contact and contact not in conversations:raise ValueError('Finding contact is outside the supplied workspace sample.')
        if not isinstance(references,list) or len(references)>5 or any(not isinstance(i,str) for i in references):raise ValueError('Use up to five supplied evidence message IDs.')
        known={m['id'] for m in conversations.get(contact,{}).get('messages',[])}
        if any(i not in known for i in references):raise ValueError('Finding evidence is outside the supplied contact messages.')
        if proposal is not None:
            if not contact or not references:raise ValueError('Proposed actions require a contact and supporting message evidence.')
            if not isinstance(proposal,dict):raise ValueError('Proposed action must be an object or null.')
            kind=proposal.get('type')
            if kind not in allowed_actions(context.get('agent',{})):raise ValueError('Analysis proposed an action disabled for this agent; no findings were applied.')
            if kind=='tag':proposal={'type':kind,'tag':text(proposal.get('tag'),'Tag',60)}
            elif kind=='assign':
                if proposal.get('owner') not in members:raise ValueError('Proposed owner is not a supplied workspace member.')
                proposal={'type':kind,'owner':proposal['owner']}
            elif kind in ['note','draft_reply']:proposal={'type':kind,'body':text(proposal.get('body'),'Content',4000)}
            elif kind=='task':proposal={'type':kind,'title':text(proposal.get('title'),'Task title',150)}
            else:raise ValueError('Analysis proposed an unsupported action; no findings were applied.')
        findings.append({'title':text(f.get('title'),'Finding title',200),'details':text(f.get('details'),'Finding details',4000),'contact_id':contact,'evidence_ids':list(dict.fromkeys(references)),'action':proposal})
    return summary,findings


def review_finding(store,db,ctx,data):
    t=ctx['tenant_id'];f=store._get(db,t,'finding',data.get('id'));stamp=int(time.time())
    if f['status']!='pending':raise ValueError('This finding was already reviewed.')
    decision=data.get('decision')
    if decision not in ['approve','dismiss']:raise ValueError('Choose approve or dismiss.')
    result={};status='dismissed'
    if decision=='approve':
        proposal=f.get('action');status='acknowledged'
        if proposal:
            source_run=store._get(db,t,'airun',f['run_id']);agent=store._get(db,t,'aiagent',source_run['agent_id'])
            if agent.get('archived') or proposal.get('type') not in allowed_actions(agent):raise ValueError('This agent is archived or this proposal action is no longer allowed. Dismiss the finding or update the agent policy.')
            contact=store._get(db,t,'contact',f['contact_id'])
            if stamp-f['created']>86400 or fingerprint(db,t,contact)!=f['target_fingerprint']:raise ValueError('The conversation changed or this finding expired. Run a new analysis before applying it.')
            kind=proposal['type'];status='applied'
            if kind=='tag':
                tags=list(dict.fromkeys(contact['tags']+[proposal['tag']]))
                if len(tags)>25:raise ValueError('This contact already has the maximum number of tags.')
                result=store._put(db,t,'contact',dict(contact,tags=tags),contact['id'])
            elif kind=='assign':
                owner=member(db,t,proposal['owner'])
                contact=dict(contact);contact.pop('flow_session',None);contact.pop('outgoing_watch',None)
                assignment(store,db,t,contact['id'],contact.get('assignee'),owner,ctx['user']['id'],'ai_finding')
                result=store._put(db,t,'contact',dict(contact,assignee=owner,status='pending',automation_hold=True),contact['id'])
            elif kind=='note':result=store._message(db,t,contact['id'],proposal['body'],'note','internal')
            elif kind=='draft_reply':result=store._message(db,t,contact['id'],proposal['body'],'out','draft')
            elif kind=='task':result=crm_action(store,db,ctx,'task.save',{'title':proposal['title'],'contact_id':contact['id'],'owner':ctx['user']['id']})
            else:raise ValueError('Unsupported action.')
    return store._put(db,t,'finding',dict(f,status=status,reviewed_at=stamp,reviewed_by=ctx['user']['id'],result_id=result.get('id','')),f['id'])
