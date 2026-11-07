"""One workspace support assistant with durable jobs and separately gated live replies."""
import hashlib
import json
import os
import re
import secrets
import time
from ai import ai_status,ask_local
from crm import text
from meta import status as meta_status,send_text
from knowledge_documents import retrieve
from customer_reply_contract import parse_reply
from customer_orders import customer_orders
from team_operations import team_record
from ai_handoff import handoff,active_member
from reply_tracking import accepted as track_accepted_reply

ACTIVE={'queued','generating','sending'}


class CustomerError(Exception):
    def __init__(self,message,code=400):super().__init__(message);self.code=code


def now():return int(time.time())
def automatic_allowed(tenant):return os.environ.get('TW_AI_'+tenant.upper()+'_AUTO_REPLY','false').lower()=='true'


def runtime(tenant):
    ai=ai_status(tenant);meta=meta_status(tenant)
    return {'ai_ready':ai['enabled'] and ai['configured'],'automatic_allowed':automatic_allowed(tenant),'live_ready':bool(ai['enabled'] and ai['configured'] and automatic_allowed(tenant) and meta['live'] and meta.get('configured'))}


def public_job(job):return {k:job[k] for k in ['id','contact_id','assistant_id','status','phase','created','updated','error','reason','message_id','knowledge_references'] if k in job}


def state(store,db,tenant):
    settings=store._list(db,tenant,'customerassistant');rows=db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='customerreplyjob' ORDER BY rowid DESC LIMIT 50",(tenant,)).fetchall()
    return {'settings':settings[0] if settings else None,'runtime':runtime(tenant),'jobs':[public_job(dict(json.loads(r['data']),id=r['id'])) for r in reversed(rows)]}


def action(store,ctx,operation,data):
    if ctx['role']!='admin':raise CustomerError('Administrator access required.',403)
    tenant=ctx['tenant_id'];stamp=now()
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(tenant,ctx['user']['id'])).fetchone():raise CustomerError('Administrator access changed.',403)
        if operation=='customer-assistant.save':
            settings=store._list(db,tenant,'customerassistant');old=settings[0] if settings else {}
            mode=data.get('mode','draft');enabled=data.get('enabled',False);keywords=data.get('keywords',[])
            if mode not in ['draft','live'] or not isinstance(enabled,bool):raise CustomerError('Choose draft/live mode and a valid activation state.')
            if not isinstance(keywords,list) or len(keywords)>10 or any(not isinstance(k,str) or not 1<=len(k.strip())<=100 for k in keywords):raise CustomerError('Use up to ten trigger keywords, or leave empty for unmatched customer messages.')
            if mode=='live' and enabled and not runtime(tenant)['live_ready']:raise CustomerError('Automatic replies require approved AI usage, complete/live Meta settings and the workspace AUTO_REPLY server flag.')
            source_ids=data.get('source_ids',[]);limit=data.get('daily_limit',100);order_access=data.get('order_access',False)
            route=data.get('handoff_assignee','');task=data.get('handoff_task',False)
            strategy=data.get('handoff_strategy',old.get('handoff_strategy','fixed'));pool=data.get('handoff_pool',old.get('handoff_pool',[]))
            if strategy not in ['fixed','least_busy','round_robin']:raise CustomerError('Choose fixed, least-busy or round-robin handoff routing.')
            if not isinstance(pool,list) or len(pool)>50 or any(not isinstance(user,str) or not active_member(db,tenant,user) for user in pool):raise CustomerError('Select up to 50 handoff members from this workspace.')
            pool=list(dict.fromkeys(pool))
            team_id=data.get('handoff_team_id',old.get('handoff_team_id',''));respect=data.get('respect_availability',old.get('respect_availability',False));maximum=data.get('handoff_max_open',old.get('handoff_max_open',0))
            if not isinstance(team_id,str) or team_id and not team_record(store,db,tenant,team_id):raise CustomerError('Choose a handoff team in this workspace.')
            if team_id and strategy=='fixed':raise CustomerError('Use least-busy or round-robin routing for a team.')
            if type(respect) is not bool or type(maximum) is not int or not 0<=maximum<=1000:raise CustomerError('Choose availability policy and a workload cap of 0-1,000.')
            if strategy in ['least_busy','round_robin'] and not pool and not team_id:raise CustomerError('Select at least one member for pool routing.')
            if not isinstance(route,str) or route and not active_member(db,tenant,route):raise CustomerError('Choose a handoff member of this workspace.')
            if type(task) is not bool:raise CustomerError('Choose whether an internal handoff task is created.')
            if type(order_access) is not bool:raise CustomerError('Choose whether linked order access is enabled.')
            if not isinstance(source_ids,list) or len(source_ids)>28 or any(not isinstance(id,str) for id in source_ids):raise CustomerError('Select approved customer-facing knowledge sources.')
            available={s['id'] for s in store._list(db,tenant,'knowledge')+store._list(db,tenant,'knowledgedocument')}
            if any(id not in available for id in source_ids):raise CustomerError('A knowledge source is not in this workspace.',404)
            if type(limit) is not int or not 1<=limit<=1000:raise CustomerError('Choose a daily generation limit of 1–1,000 requests.')
            values={'name':text(data.get('name'),'Assistant name',100),'instructions':text(data.get('instructions'),'Support instructions',6000),'enabled':enabled,'mode':mode,'keywords':list(dict.fromkeys(k.strip().lower() for k in keywords)),'source_ids':list(dict.fromkeys(source_ids)),'order_access':order_access,'handoff_assignee':route,'handoff_task':task,'daily_limit':limit,'version':old.get('version',0)+1,'owner':ctx['user']['id'],'updated':stamp}
            values.update(handoff_strategy=strategy,handoff_pool=pool,handoff_team_id=team_id,respect_availability=respect,handoff_max_open=maximum)
            result=store._put(db,tenant,'customerassistant',values,old.get('id'))
            # Any settings edit fences pending and generating work. A WhatsApp
            # submission already in flight cannot be recalled.
            for row in db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='customerreplyjob' AND json_extract(data,'$.status') IN ('queued','generating')",(tenant,)).fetchall():
                job=dict(json.loads(row['data']),id=row['id']);store._put(db,tenant,'customerreplyjob',dict(job,status='cancelled',phase='Assistant settings changed',lease='',updated=stamp),job['id'])
        elif operation=='customer-assistant.cancel':
            job=store._get(db,tenant,'customerreplyjob',data.get('id'))
            if job['status']=='sending':raise CustomerError('WhatsApp submission is already in flight. Reconcile the provider outcome.',409)
            if job['status'] not in ['queued','generating']:raise CustomerError('Only queued or generating replies can be stopped. Recorded outcomes remain in history.',409)
            result=store._put(db,tenant,'customerreplyjob',dict(job,status='cancelled',phase='Stopped locally; model generation may have continued',lease='',updated=stamp),job['id']);result=public_job(result)
        else:raise CustomerError('Unknown customer assistant action.',404)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],operation,stamp))
    return result


def owner_context(db,tenant,owner):
    row=db.execute("SELECT u.id,u.name,u.email,t.name AS business FROM users u JOIN members m ON m.user=u.id JOIN tenants t ON t.id=m.tenant WHERE m.tenant=? AND m.user=? AND m.role='admin'",(tenant,owner)).fetchone()
    return dict(row) if row else None


def conversation(db,tenant,contact):
    return [dict(r) for r in db.execute("SELECT * FROM (SELECT rowid AS ordinal,id,direction,body,ts FROM messages WHERE tenant=? AND contact=? AND ((direction='in' AND status='received') OR (direction='out' AND status IN ('accepted','sent','delivered','read'))) ORDER BY rowid DESC LIMIT 20) ORDER BY ordinal",(tenant,contact))]


def fingerprint(store,db,tenant,contact,source_ids,order_access=False):
    messages=conversation(db,tenant,contact);sources=[s for s in store._list(db,tenant,'knowledge') if s['id'] in source_ids];documents=[s for s in store._list(db,tenant,'knowledgedocument') if s['id'] in source_ids]
    value=[messages[-1]['ordinal'] if messages else 0,sources,documents,customer_orders(store,db,tenant,contact) if order_access else []]
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def enqueue(store,db,tenant,contact,message,incoming):
    settings=store._list(db,tenant,'customerassistant');ai=ai_status(tenant)
    if not settings or not settings[0]['enabled'] or not ai['enabled'] or not ai['configured'] or contact.get('automation_hold') or contact.get('flow_session'):return
    assistant=settings[0]
    if assistant['keywords'] and not any(k in incoming.lower() for k in assistant['keywords']):return
    if not 0<=now()-contact.get('last_real_inbound',0)<86400 or not owner_context(db,tenant,assistant['owner']):return
    if assistant['mode']=='live' and not runtime(tenant)['live_ready']:return
    # Supersede unsent fragments; an already generating reply will be discarded
    # by its conversation fingerprint if a newer message arrived.
    for row in db.execute("SELECT id,data FROM entities WHERE tenant=? AND kind='customerreplyjob' AND json_extract(data,'$.status')='queued'",(tenant,)).fetchall():
        job=dict(json.loads(row['data']),id=row['id'])
        if job['contact_id']==contact['id']:store._put(db,tenant,'customerreplyjob',dict(job,status='superseded',phase='A newer customer message arrived',updated=now()),job['id'])
    store._put(db,tenant,'customerreplyjob',{'assistant_id':assistant['id'],'version':assistant['version'],'contact_id':contact['id'],'inbound_id':message['id'],'provider':ai['provider_id'],'model':ai['model'],'status':'queued','phase':'Queued for customer support','created':now(),'updated':now(),'lease':'','lease_until':0})


def valid(store,db,tenant,job,assistant,contact):
    ai=ai_status(tenant)
    return (assistant['enabled'] and assistant['version']==job['version'] and not contact.get('automation_hold') and not contact.get('flow_session') and
            owner_context(db,tenant,assistant['owner']) and ai['enabled'] and ai['configured'] and ai['provider_id']==job['provider'] and job['model'] in ai['models'] and
            0<=now()-contact.get('last_real_inbound',0)<86400 and (assistant['mode']=='draft' or runtime(tenant)['live_ready']))


def process_once(store):
    stamp=now();chosen=None
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');rows=db.execute("SELECT id,tenant,data FROM entities WHERE kind='customerreplyjob' AND json_extract(data,'$.status') IN ('queued','generating','sending') ORDER BY rowid").fetchall()
        for row in rows:
            job=dict(json.loads(row['data']),id=row['id']);tenant=row['tenant']
            if job['status'] in ['generating','sending']:
                if job.get('lease_until',0)<stamp:
                    store._put(db,tenant,'customerreplyjob',dict(job,status='unknown',phase='Worker interrupted; no automatic retry',lease='',updated=stamp),job['id'])
                    assistant=store._get(db,tenant,'customerassistant',job['assistant_id']);contact=store._get(db,tenant,'contact',job['contact_id'])
                    messages=conversation(db,tenant,contact['id'])
                    if not contact.get('automation_hold') and (job['status']=='sending' or assistant['version']==job['version'] and messages and messages[-1]['id']==job['inbound_id']):
                        handoff(store,db,tenant,assistant,contact,job,'AI worker was interrupted. Reconcile its unknown outcome before responding again.')
                    if job.get('message_id'):db.execute("UPDATE messages SET status='unknown' WHERE tenant=? AND id=? AND status='sending'",(tenant,job['message_id']))
                continue
            assistant=store._get(db,tenant,'customerassistant',job['assistant_id']);contact=store._get(db,tenant,'contact',job['contact_id'])
            if not valid(store,db,tenant,job,assistant,contact):store._put(db,tenant,'customerreplyjob',dict(job,status='cancelled',phase='Assistant access or conversation eligibility changed',updated=stamp),job['id']);continue
            if any(r['tenant']==tenant and json.loads(r['data']).get('contact_id')==job['contact_id'] and json.loads(r['data'])['status'] in ['generating','sending'] for r in rows):continue
            owner=owner_context(db,tenant,assistant['owner']);messages=conversation(db,tenant,contact['id']);question=next((m['body'] for m in reversed(messages) if m['direction']=='in'),'')
            if not messages or messages[-1]['direction']!='in' or messages[-1]['id']!=job['inbound_id']:
                store._put(db,tenant,'customerreplyjob',dict(job,status='superseded',phase='Conversation was answered or newer input arrived',updated=stamp),job['id']);continue
            context={'_workspace_id':tenant,'_model':job['model'],'_customer_reply':True,'business':owner['business'],'support_instructions':assistant['instructions'],'conversation':[{'direction':m['direction'],'text':m['body'][:2000],'truncated':len(m['body'])>2000} for m in messages],
                     'knowledge_sources':[{k:s[k] for k in ['id','title','body']} for s in store._list(db,tenant,'knowledge') if s['enabled'] and s['id'] in assistant['source_ids']],
                     'knowledge_passages':retrieve(store,db,tenant,question,assistant['source_ids']),'customer_orders':customer_orders(store,db,tenant,contact['id']) if assistant.get('order_access') else []}
            has_knowledge=bool(context['knowledge_sources'] or context['knowledge_passages'] or context['customer_orders'])
            count=db.execute("SELECT COUNT(*) FROM entities WHERE tenant=? AND kind='customerreplyjob' AND json_extract(data,'$.model_submitted')=1 AND json_extract(data,'$.model_started')>=?",(tenant,stamp-stamp%86400)).fetchone()[0]
            if has_knowledge and count>=assistant['daily_limit']:
                context['knowledge_sources']=[];context['knowledge_passages']=[];context['customer_orders']=[];context['_limit_reached']=True;has_knowledge=False
            token=secrets.token_hex(16);job=store._put(db,tenant,'customerreplyjob',dict(job,status='generating',phase='Drafting a grounded reply' if has_knowledge else 'Requesting human review',fingerprint=fingerprint(store,db,tenant,contact['id'],assistant['source_ids'],assistant.get('order_access',False)),model_submitted=has_knowledge,model_started=stamp if has_knowledge else 0,lease=token,lease_until=stamp+120,updated=stamp),job['id'])
            chosen=tenant,job,token,question,context;break
    if not chosen:return False
    tenant,job,token,question,context=chosen;stage='model';context['_gateway_path']=str(store.path)
    try:
        if re.search(r'\b(talk to (?:an? )?(?:human|agent)|speak (?:to|with) (?:an? )?(?:human|agent)|human agent|real person|representative|executive|complaint|cheated|scam|fraud|terrible service|worst service|useless service|escalate to manager)\b',question,re.IGNORECASE):
            raw=json.dumps({'reply':'','needs_human':True,'reason':'Customer requested a human agent or expressed negative sentiment.','knowledge_references':[]})
        elif context['knowledge_sources'] or context['knowledge_passages'] or context['customer_orders']:raw=ask_local(question,context,[])
        else:raw=json.dumps({'reply':'','needs_human':True,'reason':'Daily generation limit reached.' if context.get('_limit_reached') else 'No approved customer knowledge supports this question.','knowledge_references':[]})
        stage='validate';answer=parse_reply(raw,context['knowledge_passages']);send=None
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'customerreplyjob',job['id']);assistant=store._get(db,tenant,'customerassistant',job['assistant_id']);contact=store._get(db,tenant,'contact',job['contact_id'])
            if current.get('lease')!=token or current['status']!='generating':return True
            if not valid(store,db,tenant,current,assistant,contact) or fingerprint(store,db,tenant,contact['id'],assistant['source_ids'],assistant.get('order_access',False))!=current['fingerprint']:
                store._put(db,tenant,'customerreplyjob',dict(current,status='discarded',phase='Context changed; late answer discarded',lease='',updated=now()),job['id']);return True
            if answer['needs_human']:
                contact=handoff(store,db,tenant,assistant,contact,job,answer['reason'])
            message=store._message(db,tenant,contact['id'],answer['reply'],'out','sending' if assistant['mode']=='live' and not answer['needs_human'] else 'draft') if answer['reply'] else None
            status='handoff' if answer['needs_human'] else 'sending' if assistant['mode']=='live' else 'completed'
            phase='Human review requested' if status=='handoff' else 'Submitting one WhatsApp reply' if status=='sending' else 'Reply draft ready'
            current=store._put(db,tenant,'customerreplyjob',dict(current,status=status,phase=phase,message_id=message['id'] if message else None,reason=answer['reason'],knowledge_references=answer['knowledge_references'],updated=now(),lease=token if status=='sending' else ''),job['id'])
            if status=='sending':send=(contact['phone'],answer['reply'],message['id'])
            db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'Customer assistant','customer-assistant.'+status,now()))
        if send:
            stage='send'
            try:external=send_text(tenant,send[0],send[1]);outcome='accepted';error=''
            except Exception:external=None;outcome='unknown';error='WhatsApp submission outcome is uncertain. Reconcile with Meta; no automatic retry.'
            with store.db() as db:
                db.execute('BEGIN IMMEDIATE');db.execute('UPDATE messages SET status=?,external_id=? WHERE tenant=? AND id=?',(outcome,external,tenant,send[2]));current=store._get(db,tenant,'customerreplyjob',job['id'])
                store._put(db,tenant,'customerreplyjob',dict(current,status=outcome,phase='Provider accepted reply' if outcome=='accepted' else 'Provider outcome unknown',error=error,lease='',updated=now()),job['id'])
                if outcome=='accepted':track_accepted_reply(store,db,tenant,send[2],now())
                if outcome=='unknown':
                    contact=store._get(db,tenant,'contact',job['contact_id']);assistant=store._get(db,tenant,'customerassistant',job['assistant_id'])
                    if not contact.get('automation_hold'):handoff(store,db,tenant,assistant,contact,job,'AI reply submission outcome is unknown. Reconcile with Meta before sending again.')
                db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'Customer assistant','customer-assistant.'+outcome,now()))
        return True
    except Exception:
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE');current=store._get(db,tenant,'customerreplyjob',job['id'])
            if current.get('lease')==token and current['status']=='generating':
                store._put(db,tenant,'customerreplyjob',dict(current,status='unknown' if stage=='model' else 'failed',phase='No usable customer reply; review required',error='AI request or output could not be verified. No automatic retry.',lease='',updated=now()),job['id'])
                contact=store._get(db,tenant,'contact',job['contact_id']);assistant=store._get(db,tenant,'customerassistant',job['assistant_id'])
                if not contact.get('automation_hold') and assistant['version']==job['version'] and fingerprint(store,db,tenant,contact['id'],assistant['source_ids'],assistant.get('order_access',False))==current['fingerprint']:
                    handoff(store,db,tenant,assistant,contact,job,'Customer AI could not produce a verified reply. A teammate must review this conversation.')
        return True
