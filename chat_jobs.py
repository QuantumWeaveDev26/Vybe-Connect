"""Private durable AI chat jobs and verified response citations."""
import hashlib
import json
import secrets
import time
from ai import ai_status, openai_key, ask_local, build_system, clean_history
from openai_background import openai_create, openai_create_agent, openai_retrieve, openai_cancel, response_path
from agent_builder import builder_system,builder_history,agent_schema,parse_proposal,install_proposal
from crm import text

ACTIVE={'queued','running','waiting','cancelling'}
TERMINAL={'completed','cancelled','failed','unknown','cancel_unconfirmed'}


def now():return int(time.time())
def uid():return secrets.token_hex(8)


class ChatError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def public_job(job):
    result={k:job[k] for k in ['id','chat_id','question','status','phase','created','updated','events','error','cancel_outcome'] if k in job}
    result['can_cancel']=bool(job.get('provider_id') and job['status'] not in ['completed','cancelled'])
    return result


def owned_chat(store,db,ctx,id):
    chat=store._get(db,ctx['tenant_id'],'aichat',id)
    if chat['owner']!=ctx['user']['id']:raise ChatError('AI conversation access denied.',403)
    return chat


def history_hash(messages):
    return hashlib.sha256(json.dumps([{k:m.get(k) for k in ['id','role','content']} for m in messages],sort_keys=True).encode()).hexdigest()


def chat_action(store,ctx,action,data):
    tenant=ctx['tenant_id'];stamp=now()
    if action=='ai.chat.start':
        question=text(data.get('question'),'Question',8000)
        purpose=data.get('purpose','chat')
        if purpose not in ['chat','agent_builder']:raise ChatError('Choose a supported AI conversation purpose.')
        if purpose=='agent_builder' and ctx['role']!='admin':raise ChatError('Administrator access required to create agents.',403)
        if purpose=='agent_builder' and data.get('agent_id'):raise ChatError('An agent builder cannot impersonate an existing agent.')
        status=ai_status(tenant)
        if not status['enabled'] or not status['configured']:raise ChatError('Configure and enable the AI provider. OpenAI also requires this workspace’s paid-call approval.',503)
        _,validated=store._ai_context(ctx,data)  # Validate agent, mode and selected contact before queueing.
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if data.get('chat_id'):
                chat=owned_chat(store,db,ctx,data['chat_id'])
                if (chat.get('agent_id') or '')!=(data.get('agent_id') or ''):raise ChatError('Start a new chat to change agents.')
                if chat.get('purpose','chat')!=purpose:raise ChatError('Start a new chat to change its purpose.')
            else:chat=store._put(db,tenant,'aichat',{'name':question[:60],'owner':ctx['user']['id'],'agent_id':data.get('agent_id') or '','purpose':purpose,'messages':[]})
            active=[j for j in store._list(db,tenant,'aijob') if j['owner']==ctx['user']['id'] and j['chat_id']==chat['id'] and j['status'] in ACTIVE]
            if len(active)>=5:raise ChatError('This conversation already has five pending requests. Wait or stop them first.',409)
            params={k:data.get(k) for k in ['agent_id','mode','page','contact_id','model'] if data.get(k) is not None}
            job=store._put(db,tenant,'aijob',{'owner':ctx['user']['id'],'chat_id':chat['id'],'question':question,'params':params,'provider':status['provider_id'],'model':validated.get('_model') or status['model'],'status':'queued','phase':'Queued','created':stamp,'updated':stamp,'next_poll':0,'lease':'','lease_until':0,'submitted':False,'provider_id':'','cancel_requested':False,'events':[{'name':'Queued','at':stamp}]})
            if purpose=='agent_builder':job=store._put(db,tenant,'aijob',dict(job,purpose=purpose),job['id'])
            return public_job(job)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');chat=owned_chat(store,db,ctx,data.get('chat_id'))
        if action=='ai.chat.install-agent':
            if ctx['role']!='admin':raise ChatError('Administrator access required to install agents.',403)
            return install_proposal(store,db,ctx,chat,data,stamp)
        if action=='ai.chat.cancel':
            count=0
            for job in store._list(db,tenant,'aijob'):
                stoppable=job['status'] in ACTIVE or job.get('provider_id') and job['status'] in ['unknown','failed','cancel_unconfirmed']
                if job['owner']!=ctx['user']['id'] or job['chat_id']!=chat['id'] or not stoppable:continue
                status='cancelled' if job['status']=='queued' else 'cancelling';count+=1
                store._put(db,tenant,'aijob',dict(job,status=status,cancel_requested=True,phase='Cancelled before submission' if status=='cancelled' else 'Cancellation requested',next_poll=0,updated=stamp,cancel_outcome='not_submitted' if status=='cancelled' else ''),job['id'])
            return {'requested':count}
        if action=='ai.chat.feedback':
            rating=data.get('rating')
            if rating not in ['helpful','not_helpful','']:raise ChatError('Choose a valid feedback rating.')
            message=next((m for m in chat['messages'] if m.get('id')==data.get('message_id') and m['role']=='assistant'),None)
            if not message:raise ChatError('Assistant message not found.',404)
            message['rating']=rating;store._put(db,tenant,'aichat',chat,chat['id']);return {'saved':True}
        raise ChatError('Unknown AI chat action.',404)


def owner_context(db,tenant,owner):
    user=db.execute('SELECT id,name,email FROM users WHERE id=?',(owner,)).fetchone()
    workspace=db.execute('SELECT t.id,t.name,m.role FROM tenants t JOIN members m ON m.tenant=t.id WHERE t.id=? AND m.user=?',(tenant,owner)).fetchone()
    if not user or not workspace:return None
    return {'user':dict(user),'workspace':dict(workspace),'workspaces':[dict(workspace)],'tenant_id':tenant,'role':workspace['role']}


def commit_job(store,tenant,id,lease,changes):
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'aijob',id)
        if current['lease']!=lease:raise ChatError('AI job execution lease changed.',409)
        result=dict(current,**changes,updated=now())
        if current.get('cancel_requested') and result['status'] not in TERMINAL:result.update(status='cancelling',phase='Cancellation requested',next_poll=0)
        if result.get('phase')!=current.get('phase'):result['events']=(current['events']+[{'name':result['phase'],'at':now()}])[-20:]
        return store._put(db,tenant,'aijob',result,id)


def parse_answer(result,scope,knowledge_scope=None):
    if result.get('status')!='completed':raise ValueError('The AI response did not complete.')
    parts=[]
    for item in result.get('output',[]):
        if not isinstance(item,dict) or item.get('type')!='message':continue
        values=item.get('content',[])
        if not isinstance(values,list):raise ValueError('Invalid AI message content.')
        for value in values:
            if not isinstance(value,dict):raise ValueError('Invalid AI message part.')
            if value.get('type')=='refusal':raise ValueError('The AI provider declined this request.')
            if value.get('type')=='output_text':parts.append(value.get('text',''))
    try:data=json.loads('\n'.join(parts))
    except (TypeError,ValueError):raise ValueError('The AI provider did not return a structured answer.') from None
    answer=text(data.get('answer'),'AI answer',20000);refs=data.get('references',[])
    if not isinstance(refs,list) or len(refs)>10:raise ValueError('AI references must be a list of up to ten sources.')
    normalized=[]
    for reference in refs:
        if not isinstance(reference,dict):raise ValueError('Invalid AI reference.')
        contact=reference.get('contact_id');ids=reference.get('message_ids',[])
        if not isinstance(contact,str) or contact not in scope or not isinstance(ids,list) or not ids or len(ids)>5 or any(not isinstance(i,str) or i not in scope[contact] for i in ids):raise ValueError('AI references are outside the supplied conversation evidence.')
        normalized.append({'label':text(reference.get('label'),'Source label',150),'contact_id':contact,'message_ids':list(dict.fromkeys(ids))})
    knowledge_scope=knowledge_scope or {};knowledge=[];items=data.get('knowledge_references',[])
    if not isinstance(items,list) or len(items)>6:raise ValueError('Use up to six document references.')
    for item in items:
        if not isinstance(item,dict) or not isinstance(item.get('document_id'),str) or not isinstance(item.get('chunk_id'),str) or item['chunk_id'] not in knowledge_scope.get(item['document_id'],[]):raise ValueError('AI document references are outside the supplied evidence.')
        knowledge.append({'label':text(item.get('label'),'Source label',150),'document_id':item['document_id'],'chunk_id':item['chunk_id']})
    return answer,normalized,knowledge


def finish_answer(store,tenant,job,lease,result,local_answer=None):
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'aijob',job['id'])
        if current['lease']!=lease:raise ChatError('AI job execution lease changed.',409)
        if current['cancel_requested']:
            changes=dict(status='cancelled',phase='Answer discarded after cancellation',cancel_outcome='local_discarded' if local_answer is not None else 'provider_completed')
        else:
            chat=store._get(db,tenant,'aichat',current['chat_id'])
            if history_hash(chat['messages'])!=current['history_hash']:raise ValueError('This AI conversation changed while the answer was being generated. The late answer was not published.')
            proposal=None;knowledge=[]
            if current.get('purpose')=='agent_builder':
                proposal=parse_proposal(result,local_answer);answer=proposal['summary'];references=[]
            else:answer,references,knowledge=(local_answer,[],[]) if local_answer is not None else parse_answer(result,current['reference_scope'],current.get('knowledge_scope'))
            message={'id':uid(),'role':'assistant','content':answer,'references':references,'job_id':job['id'],'steps':current['events']}
            if proposal:message['agent_draft']=proposal
            if knowledge:message['knowledge_references']=knowledge
            chat['messages']=(chat['messages']+[{'id':uid(),'role':'user','content':current['question']},message])[-24:]
            store._put(db,tenant,'aichat',chat,chat['id']);changes=dict(status='completed',phase='Completed')
        updated=dict(current,**changes,lease='',lease_until=0,updated=now())
        updated['events']=(current['events']+[{'name':updated['phase'],'at':now()}])[-20:]
        store._put(db,tenant,'aijob',updated,job['id'])


def process_chat_job_once(store):
    stamp=now();chosen=None
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');rows=db.execute("SELECT id,tenant,data FROM entities WHERE kind='aijob' ORDER BY rowid").fetchall()
        jobs=[dict(json.loads(r['data']),id=r['id'],tenant=r['tenant']) for r in rows]
        for job in sorted(jobs,key=lambda j:(j['status']!='cancelling',j.get('next_poll',0),j['created'])):
            if job['status'] not in ACTIVE or job.get('lease_until',0)>stamp or job.get('next_poll',0)>stamp:continue
            tenant=job['tenant'];id=job['id'];values={k:v for k,v in job.items() if k!='tenant'}
            if job.get('submitted') and not job.get('provider_id') and job.get('lease'):
                cancelling=job.get('cancel_requested')
                local=job['provider']=='ollama'
                status='cancelled' if cancelling and local else 'cancel_unconfirmed' if cancelling else 'unknown'
                phase='Local result discarded after worker interruption' if cancelling and local else 'Submission and cancellation outcome unknown' if cancelling else 'Provider submission outcome unknown'
                store._put(db,tenant,'aijob',dict(values,status=status,phase=phase,error='The worker stopped after model submission. No automatic resubmission is performed; provider generation may have continued.',cancel_outcome='local_discarded' if cancelling and local else 'unconfirmed' if cancelling else '',lease='',lease_until=0),id);continue
            if job['status']=='running':
                if job.get('submitted') and not job.get('provider_id'):
                    store._put(db,tenant,'aijob',dict(values,status='unknown',phase='Provider submission outcome unknown',error='The worker stopped before recording a provider response ID. This request will not be resubmitted automatically.',lease='',lease_until=0),id);continue
                values['status']='waiting' if job.get('provider_id') else 'queued'
            if values['status']=='queued' and any(j['id']!=id and j['tenant']==tenant and j['chat_id']==job['chat_id'] and j['status'] in ['running','waiting','cancelling'] for j in jobs):continue
            token=uid();values.update(lease=token,lease_until=stamp+120,updated=stamp)
            if values['status']=='queued':values.update(status='running',phase='Reading workspace')
            store._put(db,tenant,'aijob',values,id);chosen=(tenant,values,token);break
    if not chosen:return False
    tenant,job,lease=chosen
    stage='prepare'
    try:
        with store.db() as db:ctx=owner_context(db,tenant,job['owner'])
        if job.get('purpose')=='agent_builder' and ctx and ctx['role']!='admin' and not job.get('provider_id'):raise ValueError('Administrator access was removed before agent generation.')
        config=ai_status(tenant)
        if not ctx or job.get('purpose')=='agent_builder' and ctx['role']!='admin' or not config['enabled'] or not config['configured'] or job['provider']!=config['provider_id'] or job['model'] not in config['models']:
            if not job.get('provider_id'):raise ValueError('AI access or configuration is no longer enabled.')
            job=commit_job(store,tenant,job['id'],lease,{'cancel_requested':True,'status':'cancelling','phase':'Cancellation requested'})
        if job.get('cancel_requested') and job.get('provider_id'):
            stage='cancel'
            result=openai_cancel(openai_key(tenant),job['provider_id']);status=result.get('status')
            if status=='cancelled':commit_job(store,tenant,job['id'],lease,{'status':'cancelled','phase':'Provider confirmed cancellation','cancel_outcome':'provider_cancelled','lease':'','lease_until':0})
            elif status in ['completed','failed','incomplete']:commit_job(store,tenant,job['id'],lease,{'status':'cancelled','phase':'Stopped locally; provider already finished','cancel_outcome':'provider_completed','lease':'','lease_until':0})
            else:commit_job(store,tenant,job['id'],lease,{'status':'cancel_unconfirmed','phase':'Provider cancellation unconfirmed','cancel_outcome':'unconfirmed','lease':'','lease_until':0})
            return True
        if job.get('cancel_requested'):
            commit_job(store,tenant,job['id'],lease,{'status':'cancelled','phase':'Cancelled before submission','cancel_outcome':'not_submitted','lease':'','lease_until':0});return True
        if not job.get('provider_id'):
            state,context=store._ai_context(ctx,dict(job['params'],question=job['question']))
            with store.db() as db:chat=owned_chat(store,db,ctx,job['chat_id'])
            history=builder_history(chat['messages']) if job.get('purpose')=='agent_builder' else clean_history(chat['messages'])
            scope={c['contact_id']:[m['id'] for m in c['messages']] for c in context['recent_conversations']}
            knowledge_scope={}
            for passage in context['knowledge_passages']:knowledge_scope.setdefault(passage['document_id'],[]).append(passage['chunk_id'])
            job=commit_job(store,tenant,job['id'],lease,{'history_hash':history_hash(chat['messages']),'reference_scope':scope,'knowledge_scope':knowledge_scope,'phase':'Requesting model','submitted':True})
            if job['cancel_requested']:
                commit_job(store,tenant,job['id'],lease,{'status':'cancelled','phase':'Cancelled before submission','cancel_outcome':'not_submitted','lease':'','lease_until':0});return True
            if job['provider']=='ollama':
                if job.get('purpose')=='agent_builder':context={'_workspace_id':tenant,'_model':job['model'],'_agent_builder':True,'business':ctx['workspace']['name'],'analysis_contract':agent_schema()}
                answer=ask_local(job['question'],context,history);finish_answer(store,tenant,job,lease,{},local_answer=answer);return True
            stage='create'
            if job.get('purpose')=='agent_builder':result=openai_create_agent(openai_key(tenant),job['model'],builder_system(ctx['workspace']['name']),job['question'],history)
            else:result=openai_create(openai_key(tenant),job['model'],build_system(context),job['question'],history)
            response_path(result.get('id'));job=commit_job(store,tenant,job['id'],lease,{'provider_id':result['id'],'phase':'Waiting for model'})
        else:
            stage='poll'
            result=openai_retrieve(openai_key(tenant),job['provider_id'])
        stage='validate'
        if result.get('status')=='completed':finish_answer(store,tenant,job,lease,result)
        elif result.get('status') in ['queued','in_progress']:
            commit_job(store,tenant,job['id'],lease,{'status':'waiting','phase':'Provider queued' if result['status']=='queued' else 'Generating answer','next_poll':stamp+2,'lease':'','lease_until':0})
        elif result.get('status')=='cancelled':commit_job(store,tenant,job['id'],lease,{'status':'cancelled','phase':'Provider confirmed cancellation','cancel_outcome':'provider_cancelled','lease':'','lease_until':0})
        else:raise ValueError('The AI provider did not complete this request.')
    except Exception as error:
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'aijob',job['id'])
            if current['lease']==lease:
                unknown=current.get('submitted') and not current.get('provider_id') and current.get('provider')=='openai'
                cancelled=current.get('cancel_requested') and current.get('submitted')
                message=str(error) if isinstance(error,(ValueError,ChatError)) else 'AI job failed. No answer was published.'
                retries=current.get('read_failures',0)+1
                retry_read=bool(stage=='poll' and current.get('provider_id') and not cancelled and retries<=3)
                status='waiting' if retry_read else 'cancel_unconfirmed' if cancelled else 'unknown' if unknown or stage=='poll' and current.get('provider_id') else 'failed'
                phase='Checking provider status after an error' if retry_read else 'Cancellation unconfirmed' if cancelled else 'Provider outcome unknown' if status=='unknown' else 'Failed'
                store._put(db,tenant,'aijob',dict(current,status=status,phase=phase,error=message,read_failures=retries,next_poll=now()+min(2**retries,30) if retry_read else 0,lease='',lease_until=0,updated=now()),job['id'])
    return True
