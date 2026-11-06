"""Workspace-scoped growth/support workflows. No implicit provider execution."""
import hashlib
import hmac
import html
import json
import re
import secrets
import time


KINDS=('recipe','branch','macro','article','csatsurvey','whatsappform')


def text(value,label,limit=200,optional=False):
    from store import Problem
    if not isinstance(value,str) or len(value)>limit or (not optional and not value.strip()):raise Problem('Enter '+label+' (up to '+str(limit)+' characters).')
    return value.strip()


def admin(store,db,ctx):
    from store import Problem
    if not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(ctx['tenant_id'],ctx['user']['id'])).fetchone():raise Problem('Current administrator access required.',403)


def member(store,db,ctx):
    from store import Problem
    if not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(ctx['tenant_id'],ctx['user']['id'])).fetchone():raise Problem('Workspace access changed.',403)


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


def public_record(record):return {k:v for k,v in record.items() if k not in ('secret_hash','token_hash')}


def state(store,db,ctx):
    t=ctx['tenant_id'];now=int(time.time())
    result={k+'s':[public_record(r) for r in store._list(db,t,k)] for k in KINDS}
    result['form_responses']=[public_record(r) for r in store._list(db,t,'formresponse')[-100:]] if ctx['role']=='admin' else []
    contacts=store._list(db,t,'contact');deals=store._list(db,t,'deal')
    result['branch_report']=[];result['attribution_report']=[]
    for b in result['branchs']:
        ids={c['id'] for c in contacts if c.get('branch_id')==b['id']}
        result['branch_report'].append({'id':b['id'],'name':b['name'],'contacts':len(ids),'open':sum(c['id'] in ids and c.get('status')!='solved' for c in contacts),'deals':sum(d.get('contact_id') in ids for d in deals),'won':sum(d.get('contact_id') in ids and d.get('stage')=='won' for d in deals)})
    sources={(c['attribution'].get('kind','unknown'),c['attribution']['source_id']) for c in contacts if c.get('attribution',{}).get('source_id')}
    for source_kind,source in sorted(sources):
        ids={c['id'] for c in contacts if c.get('attribution',{}).get('source_id')==source and c['attribution'].get('kind','unknown')==source_kind}
        result['attribution_report'].append({'source_id':source,'kind':source_kind,'leads':len(ids),'deals':sum(d.get('contact_id') in ids for d in deals),'won':sum(d.get('contact_id') in ids and d.get('stage')=='won' for d in deals)})
    surveys=result['csatsurveys'];ratings=[s['rating'] for s in surveys if s.get('rating')]
    result['support_report']={'snoozed':sum(c.get('snoozed_until',0)>now for c in contacts),'resolved':sum(c.get('status')=='solved' for c in contacts),'responses':len(ratings),'csat_percent':round(100*sum(r>=4 for r in ratings)/len(ratings),1) if ratings else None}
    resolutions=store._list(db,t,'supportresolution')
    result['operator_report']=[]
    for u in db.execute('SELECT u.id,u.name FROM users u JOIN members m ON m.user=u.id WHERE m.tenant=?',(t,)):
        closed=[r for r in resolutions if r['actor']==u['id']];samples=[r['seconds_since_last_inbound'] for r in closed if r.get('seconds_since_last_inbound') is not None]
        feedback=[s['rating'] for s in surveys if s.get('agent')==u['id'] and s.get('rating')]
        result['operator_report'].append({'name':u['name'],'resolutions':len(closed),'mean_seconds_since_last_inbound':round(sum(samples)/len(samples)) if samples else None,'csat_responses':len(feedback),'csat_percent':round(100*sum(r>=4 for r in feedback)/len(feedback),1) if feedback else None})
    return result


def action(store,ctx,operation,data):
    from store import Problem
    t=ctx['tenant_id'];stamp=int(time.time());op=operation.removeprefix('growth.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');member(store,db,ctx)
        if op not in ('snooze','resolve','macro.apply','survey.create','branch.route'):admin(store,db,ctx)
        capacities={'recipe.save':('recipe',50),'branch.save':('branch',50),'macro.save':('macro',100),'article.save':('article',200),'survey.create':('csatsurvey',5000)}
        if op in capacities and not data.get('id'):
            kind,limit=capacities[op]
            if len(store._list(db,t,kind))>=limit:raise Problem('Workspace capacity reached for '+kind+'. Remove an old record first.',409)
        if op=='delete':
            kind=data.get('kind')
            if kind not in KINDS:raise Problem('Unsupported record type.')
            record=store._get(db,t,kind,data.get('id'))
            if kind=='whatsappform' and record.get('meta_id'):raise Problem('Remote forms are retained for submission history. Create a new draft instead.')
            if kind=='branch' and any(c.get('branch_id')==record['id'] for c in store._list(db,t,'contact')):raise Problem('Move contacts before deleting this branch.')
            db.execute('DELETE FROM entities WHERE tenant=? AND id=?',(t,record['id']));result={'deleted':True}
        elif op=='recipe.save':
            old=store._get(db,t,'recipe',data['id']) if data.get('id') else {}
            mapping=data.get('mapping')
            if not isinstance(mapping,dict) or set(mapping)-{'phone','name','source_id'} or 'phone' not in mapping:raise Problem('Map phone, name and optional source_id fields.')
            if any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){0,5}',v) for v in mapping.values()):raise Problem('Use dot-separated field paths without code or array expressions.')
            mode=data.get('mode','contact')
            if mode not in ('contact','draft','lead'):raise Problem('Choose contact, reply draft or sales lead.')
            branch=data.get('branch_id','')
            if branch:store._get(db,t,'branch',branch)
            template=data.get('reply','')
            if mode=='draft':template=text(template,'reply draft',4000)
            values=dict(name=text(data.get('name'),'recipe name',100),mapping=mapping,mode=mode,branch_id=branch,reply=template,enabled=data.get('enabled') is True,owner=ctx['user']['id'],secret_hash=old.get('secret_hash',''),created=old.get('created',stamp),updated=stamp)
            secret=''
            if not old:secret=secrets.token_urlsafe(32);values['secret_hash']=digest(secret)
            result=public_record(store._put(db,t,'recipe',values,old.get('id')))
            if secret:result['secret']=secret
        elif op=='recipe.rotate':
            r=store._get(db,t,'recipe',data.get('id'));secret=secrets.token_urlsafe(32)
            result=public_record(store._put(db,t,'recipe',dict(r,secret_hash=digest(secret)),r['id']));result['secret']=secret
        elif op=='branch.save':
            ids=data.get('members',[])
            if not isinstance(ids,list) or len(ids)>50 or any(not isinstance(u,str) or not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(t,u)).fetchone() for u in ids):raise Problem('Select current workspace teammates.')
            result=store._put(db,t,'branch',dict(name=text(data.get('name'),'branch name',100),members=list(dict.fromkeys(ids)),updated=stamp),data.get('id'))
        elif op=='branch.route':
            c=store._get(db,t,'contact',data.get('contact_id'));b=store._get(db,t,'branch',data.get('branch_id'))
            eligible=[u for u in b['members'] if db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(t,u)).fetchone()]
            if not eligible:raise Problem('This branch has no current teammates.')
            contacts=store._list(db,t,'contact');chosen=min(eligible,key=lambda u:(sum(c.get('assignee')==u and c.get('status')!='solved' for c in contacts),u))
            import team_operations
            team_operations.assignment(store,db,t,c['id'],c.get('assignee',''),chosen,ctx['user']['id'],'branch routing')
            result=store._put(db,t,'contact',dict(c,branch_id=b['id'],assignee=chosen),c['id'])
        elif op in ('snooze','resolve'):
            c=store._get(db,t,'contact',data.get('contact_id'))
            if op=='snooze':
                until=data.get('until',0)
                if type(until) is not int or until and not stamp<until<=stamp+30*86400:raise Problem('Snooze for up to 30 days, or choose zero to wake now.')
                values=dict(c,snoozed_until=until)
            else:
                values=dict(c,status='solved',resolved_at=stamp,snoozed_until=0)
                if c.get('status')!='solved':store._put(db,t,'supportresolution',{'contact_id':c['id'],'actor':ctx['user']['id'],'created':stamp,'seconds_since_last_inbound':stamp-c['last_real_inbound'] if c.get('last_real_inbound') and stamp>=c['last_real_inbound'] else None})
            result=store._put(db,t,'contact',values,c['id'])
        elif op=='macro.save':
            tag=text(data.get('tag',''),'tag',60,True)
            result=store._put(db,t,'macro',dict(name=text(data.get('name'),'macro name',100),reply=text(data.get('reply',''),'reply',4000,True),note=text(data.get('note',''),'private note',2000,True),tag=tag),data.get('id'))
            if not any(result[k] for k in ('reply','note','tag')):raise Problem('Add a reply draft, private note or tag.')
        elif op=='macro.apply':
            c=store._get(db,t,'contact',data.get('contact_id'));m=store._get(db,t,'macro',data.get('id'))
            if m['reply']:store._message(db,t,c['id'],m['reply'].replace('{{name}}',c['name']),'out','draft')
            if m['note']:
                import internal_comments
                internal_comments.create(store,db,ctx,c,m['note'],[])
            tags=list(dict.fromkeys(c.get('tags',[])+([m['tag']] if m['tag'] else [])))
            if len(tags)>25:raise Problem('Contact tag limit reached.')
            result=store._put(db,t,'contact',dict(c,tags=tags),c['id'])
        elif op=='survey.create':
            c=store._get(db,t,'contact',data.get('contact_id'));token=secrets.token_urlsafe(32)
            r=store._put(db,t,'csatsurvey',dict(contact_id=c['id'],agent=c.get('assignee',''),created=stamp,expires=stamp+30*86400,token_hash=digest(token)))
            result=dict(public_record(r),token=token)
        elif op=='article.save':
            published=data.get('published') is True
            if published and data.get('confirm_public') is not True:raise Problem('Confirm that this article can be viewed publicly.')
            slug=text(data.get('slug'),'article URL name',80)
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):raise Problem('Use lowercase words separated by hyphens.')
            if any(a['slug']==slug and a['id']!=data.get('id') for a in store._list(db,t,'article')):raise Problem('That article URL is already used.',409)
            result=store._put(db,t,'article',dict(title=text(data.get('title'),'title',150),slug=slug,body=text(data.get('body'),'article text',20000),published=published,updated=stamp),data.get('id'))
        else:raise Problem('Unknown growth action.',404)
        db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(t,ctx['user']['id'],operation,stamp))
        return result


def mapped(payload,path):
    value=payload
    for part in path.split('.'):
        if not isinstance(value,dict):return None
        value=value.get(part)
    return value


def receive(store,recipe_id,authorization,event_id,raw):
    from store import Problem
    if len(raw)>65536:raise Problem('Recipe payload limit is 64 KiB.',413)
    if not isinstance(event_id,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,150}',event_id):raise Problem('Provide a unique X-Event-ID header.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT tenant,data FROM entities WHERE id=? AND kind='recipe'",(recipe_id,)).fetchone()
        r=json.loads(row['data']) if row else {}
        secret=authorization.removeprefix('Bearer ') if authorization.startswith('Bearer ') else ''
        if not row or not r.get('enabled') or not secret or not hmac.compare_digest(digest(secret),r.get('secret_hash','')):raise Problem('Recipe authorization failed.',403)
        t=row['tenant']
        if not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(t,r.get('owner',''))).fetchone():raise Problem('Recipe owner authorization changed. An administrator must save it again.',403)
        import client_services
        from service_jobs import ServiceError
        owner=db.execute('SELECT id,name,email FROM users WHERE id=?',(r['owner'],)).fetchone()
        try:client_services.enforce(store,{'tenant_id':t,'role':'admin','user':dict(owner)},'growth.recipe.receive')
        except ServiceError as e:raise Problem(str(e),e.code) from None
        payload_digest=hashlib.sha256(raw).hexdigest()
        old=db.execute("SELECT digest FROM integration_events WHERE tenant=? AND provider=? AND event_id=?",(t,'recipe:'+recipe_id,event_id)).fetchone()
        if old:
            if old['digest']!=payload_digest:raise Problem('Event ID reused with different content.',409)
            return {'duplicate':True}
        try:payload=json.loads(raw)
        except (ValueError,UnicodeDecodeError):raise Problem('Use a JSON object.') from None
        if not isinstance(payload,dict):raise Problem('Use a JSON object.')
        phone=mapped(payload,r['mapping']['phone']);name=mapped(payload,r['mapping'].get('name','name'))
        from store import phone_number
        phone=phone_number(phone)
        c=next((c for c in store._list(db,t,'contact') if c['phone']==phone),None)
        if not c:c=store._contact(db,t,{'phone':phone,'name':text(name or phone,'contact name',100),'optin':False})
        # A webhook can never create marketing consent or forge a WhatsApp service window.
        values=dict(c,source='integration')
        source=mapped(payload,r['mapping'].get('source_id','source_id'))
        if source and not c.get('attribution'):values['attribution']={'source_id':text(source,'source ID',150),'kind':'integration','received':int(time.time())}
        if r.get('branch_id'):store._get(db,t,'branch',r['branch_id']);values['branch_id']=r['branch_id']
        c=store._put(db,t,'contact',values,c['id'])
        if r['mode']=='draft':store._message(db,t,c['id'],r['reply'].replace('{{name}}',c['name']),'out','draft')
        if r['mode']=='lead':
            from crm import crm_action
            crm_action(store,db,{'tenant_id':t,'user':{'id':r['owner']}},'deal.save',{'title':c['name'],'contact_id':c['id'],'owner':c.get('assignee',''),'stage':'new','amount_minor':0,'currency':'INR'})
        db.execute('INSERT INTO integration_events VALUES(?,?,?,?,?,?)',(t,'recipe:'+recipe_id,event_id,payload_digest,'recipe.received',int(time.time())))
        return {'contact_id':c['id'],'accepted':True,'mode':r['mode']}


def inbound(store,db,t,contact,event,simulated):
    """Only caller-verified Meta webhook messages may supply ad/form provenance."""
    if simulated:return contact
    c=dict(contact,snoozed_until=0)
    referral=event.get('referral')
    if isinstance(referral,dict) and not c.get('attribution'):
        source=referral.get('source_id')
        if isinstance(source,str) and 0<len(source)<=150:c['attribution']={'source_id':source,'kind':'meta_ad' if referral.get('source_type')=='ad' else 'meta_referral','received':int(time.time())}
    return c


def page(title,body):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font:17px/1.65 system-ui;margin:0;background:#f5faf7;color:#173d2b}main{max-width:780px;margin:40px auto;padding:24px}a{color:#008557}article{white-space:pre-wrap;overflow-wrap:anywhere}input,textarea,button{font:inherit;padding:12px;max-width:100%;box-sizing:border-box}button{background:#009c68;color:white;border:0;border-radius:10px}label{display:block;margin:18px 0}textarea{width:100%}</style><main><a href="/">VYBE Connect</a><h1>'+html.escape(title)+'</h1>'+body+'</main></html>'


def help_page(store,tenant,slug=''):
    from store import Problem
    with store.db() as db:
        business=db.execute('SELECT name FROM tenants WHERE id=?',(tenant,)).fetchone()
        if not business:raise Problem('Help centre not found.',404)
        articles=[a for a in store._list(db,tenant,'article') if a.get('published')]
        if slug:
            a=next((a for a in articles if a['slug']==slug),None)
            if not a:raise Problem('Article not found.',404)
            return page(a['title'],'<article>'+html.escape(a['body'])+'</article><p><a href="/help/'+tenant+'">All articles</a></p>')
        return page(business['name']+' · Help centre',''.join('<p><a href="/help/'+tenant+'/'+a['slug']+'">'+html.escape(a['title'])+'</a></p>' for a in articles) or '<p>No published articles yet.</p>')


def survey(store,token,data=None):
    from store import Problem
    if not re.fullmatch(r'[A-Za-z0-9_-]{40,60}',token):raise Problem('Survey not found.',404)
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT id,tenant,data FROM entities WHERE kind='csatsurvey' AND json_extract(data,'$.token_hash')=?",(digest(token),)).fetchone()
        r=json.loads(row['data']) if row else {}
        if not row or r['expires']<int(time.time()):raise Problem('Survey expired or unavailable.',404)
        if data is None:
            if r.get('rating'):return page('Thank you','<p>Your feedback has been recorded.</p>')
            return page('How was your support experience?','<form method="post"><label>Rating <select name="rating" required>'+''.join('<option value="'+str(i)+'">'+str(i)+' / 5</option>' for i in range(5,0,-1))+'</select></label><label>Comment (optional)<textarea name="comment" maxlength="1000"></textarea></label><button>Submit feedback</button></form>')
        if r.get('rating'):raise Problem('Feedback has already been submitted.',409)
        try:rating=int(data.get('rating',''))
        except (ValueError,TypeError):raise Problem('Choose a rating from 1 to 5.') from None
        if not 1<=rating<=5:raise Problem('Choose a rating from 1 to 5.')
        store._put(db,row['tenant'],'csatsurvey',dict(r,rating=rating,comment=text(data.get('comment',''),'comment',1000,True),answered=int(time.time())),row['id'])
        return page('Thank you','<p>Your feedback has been recorded.</p>')
