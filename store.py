"""Persistent, workspace-scoped application service. No third-party dependencies."""
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from meta import send_text, status as meta_status, list_templates, submit_template, send_template, ProviderError, rich_text_fields
from flows import default_graph, validate_graph, run_graph,validate_members,FlowExecutionError
from flow_waits import cancel_sessions,process_once as flow_wait_worker
from rule_actions import RuleError,validate as validate_rule_actions,execute as execute_rule
from rule_events import validate_trigger,contact_change as contact_rule_change,status_change as status_rule_change,dispatch as dispatch_rule_event,history as rule_history
from reply_tracking import accepted as track_accepted_reply
from no_response_rules import process_once as no_response_worker,history as no_response_history
from team_invitations import InviteError,action as invitation_action,list_invites,inspect as inspect_invite,accept as accept_invite
from member_access import MemberError,action as member_action
from message_analytics import ReportError,report as traffic_report
from ai import ai_status, ask_local
from crm import crm_action
from customer_assistant import CustomerError,action as customer_action,state as customer_state,enqueue as enqueue_customer_reply,process_once as customer_reply_worker
from contact_segments import SegmentError,action as segment_action,audience as segment_audience
from external_agents import ExternalError,action as external_action,enqueue as enqueue_event,public_agent,public_event,recent_events,process_once as dispatch_webhook,callback as external_callback
from drip_sequences import DripError,action as sequence_action,eligible as sequence_eligible,after_submit as sequence_after_submit,run_state as sequence_run_state
from knowledge_documents import KnowledgeError,upload as upload_document,document_action,retrieve as retrieve_documents,passage as document_passage
from media_service import MediaError,upload_for_workspace,read_asset,send_stored_media
from received_media import record as record_received_media,state as received_media_state,download as download_received_media
from whatsapp_media import media_status
from commerce_service import CommerceError,sync_shopify,commerce_state,ingest_shopify_webhook
import owned_commerce
import client_services
import whatsapp_calls
import provider_checks
import payment_services
import shipping_services
from service_jobs import ServiceError
from customer_orders import order_action
from website_knowledge import website_action
import growth_services
import whatsapp_forms
from chat_jobs import ChatError, chat_action, public_job, process_chat_job_once as run_chat_job
from agents import configure_agent, claim_lease, lease_valid, scheduled_context
from reviews import CONTRACT, captured_fingerprint, parse_findings, review_finding
from agent_permissions import allowed_actions
import product_feedback
import password_recovery
import internal_comments
import team_operations
import flow_publishing
import account_mfa
import embedded_signup
import ai_connection
import api_tokens
import flow_delivery
from flow_resources import resolve as flow_resources
from pipeline import save as pipeline_save,state as pipeline_state
from knowledge_usage import state as knowledge_usage_state


class Problem(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code=code


def uid(): return secrets.token_hex(8)
def now(): return int(time.time())
def required(value, label, limit=4096):
    if not isinstance(value,str) or not value.strip() or len(value)>limit: raise Problem(label+' is required (maximum '+str(limit)+' characters).')
    return value.strip()


def phone_number(value):
    value=str(value or '').strip()
    if re.search(r'[^\d+ ()-]',value): raise Problem('Use an international phone number with country code.')
    value=re.sub(r'\D','',value)
    if not re.fullmatch(r'[1-9]\d{6,14}',value): raise Problem('Use 7–15 digits including country code.')
    return value


def password_hash(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),310000).hex()


class Store:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,salt TEXT,password TEXT);
            CREATE TABLE IF NOT EXISTS tenants(id TEXT PRIMARY KEY,name TEXT);
            CREATE TABLE IF NOT EXISTS members(tenant TEXT,user TEXT,role TEXT,PRIMARY KEY(tenant,user));
            CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user TEXT,expires INTEGER);
            CREATE TABLE IF NOT EXISTS password_resets(id TEXT PRIMARY KEY,user TEXT,token_hash TEXT,fingerprint TEXT,created INTEGER,expires INTEGER,used INTEGER,revoked INTEGER,mail_status TEXT,error TEXT);
            CREATE INDEX IF NOT EXISTS reset_user_time ON password_resets(user,created);
            CREATE INDEX IF NOT EXISTS reset_mail_queue ON password_resets(mail_status,created);
            CREATE TABLE IF NOT EXISTS flow_versions(tenant TEXT,flow TEXT,version INTEGER,data TEXT,actor TEXT,published_at INTEGER,PRIMARY KEY(tenant,flow,version));
            CREATE TABLE IF NOT EXISTS account_mfa(user TEXT PRIMARY KEY,secret TEXT NOT NULL,last_counter INTEGER NOT NULL,recovery TEXT NOT NULL,pending TEXT NOT NULL,pending_until INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY,tenant TEXT,kind TEXT,data TEXT);
            CREATE INDEX IF NOT EXISTS entity_scope ON entities(tenant,kind);
            CREATE INDEX IF NOT EXISTS customer_reply_created ON entities(tenant,json_extract(data,'$.created')) WHERE kind='customerreplyjob';
            CREATE INDEX IF NOT EXISTS rule_event_type ON entities(json_extract(data,'$.event')) WHERE kind='rule';
            CREATE INDEX IF NOT EXISTS reply_watch_due ON entities(tenant,json_extract(data,'$.outgoing_watch.accepted')) WHERE kind='contact';
            CREATE UNIQUE INDEX IF NOT EXISTS no_response_identity ON entities(tenant,json_extract(data,'$.rule_id'),json_extract(data,'$.anchor_id')) WHERE kind='rulenoresponse';
            CREATE UNIQUE INDEX IF NOT EXISTS invitation_token ON entities(json_extract(data,'$.token_hash')) WHERE kind='workspaceinvite';
            CREATE INDEX IF NOT EXISTS flow_wait_due ON entities(json_extract(data,'$.flow_session.due')) WHERE kind='contact' AND json_extract(data,'$.flow_session.mode')='wait';
            CREATE INDEX IF NOT EXISTS flow_send_pending ON entities(json_extract(data,'$.status'),json_extract(data,'$.lease_until')) WHERE kind='flowsend';
            CREATE INDEX IF NOT EXISTS webhook_pending ON entities(json_extract(data,'$.status')) WHERE kind='webhookevent';
            CREATE INDEX IF NOT EXISTS webhook_identity ON entities(tenant,json_extract(data,'$.connector_id'),json_extract(data,'$.resource_id'),json_extract(data,'$.type')) WHERE kind='webhookevent';
            CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,tenant TEXT,contact TEXT,direction TEXT,body TEXT,status TEXT,ts INTEGER,external_id TEXT,UNIQUE(tenant,external_id));
            CREATE INDEX IF NOT EXISTS message_scope ON messages(tenant,contact,ts);
            CREATE INDEX IF NOT EXISTS message_reporting ON messages(tenant,ts);
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,tenant TEXT,actor TEXT,action TEXT,ts INTEGER);
            CREATE TABLE IF NOT EXISTS knowledge_chunks(tenant TEXT,document TEXT,id TEXT,ordinal INTEGER,text TEXT,PRIMARY KEY(tenant,id));
            CREATE TABLE IF NOT EXISTS integration_events(tenant TEXT,provider TEXT,event_id TEXT,digest TEXT,topic TEXT,created INTEGER,PRIMARY KEY(tenant,provider,event_id));
            CREATE TABLE IF NOT EXISTS agent_leases(tenant TEXT,agent TEXT,token TEXT,expires INTEGER,PRIMARY KEY(tenant,agent));
            CREATE TABLE IF NOT EXISTS outbound(id TEXT PRIMARY KEY,tenant TEXT,campaign TEXT,contact TEXT,payload TEXT,status TEXT,due INTEGER,claimed INTEGER,error TEXT,external_id TEXT,UNIQUE(tenant,campaign,contact));
            ''')
            embedded_signup.initialize(db)
            api_tokens.initialize(db)

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=15)
        db.row_factory=sqlite3.Row
        try:
            with db: yield db
        finally: db.close()

    def initialized(self):
        with self.db() as db: return bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone())

    def _new_user(self,db,name,email,password,allow_operator=False):
        name=required(name,'Name',100)
        email=required(email,'Email',200).lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise Problem('Enter a valid email address.')
        owner=os.environ.get('TW_PLATFORM_OWNER_EMAIL','').strip().lower()
        if owner and email==owner and not allow_operator:raise Problem('The platform owner account must be created through initial setup.',403)
        if not isinstance(password,str) or not 12<=len(password)<=256: raise Problem('Use a password of 12–256 characters.')
        user=uid(); salt=secrets.token_hex(16)
        db.execute('INSERT INTO users VALUES(?,?,?,?,?)',(user,name,email,salt,password_hash(password,salt)))
        return user

    def _session(self,db,user,remember=False):
        token=secrets.token_urlsafe(32)
        duration=2592000 if remember is True else 43200
        db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user,now()+duration))
        return {'token':token,'max_age':duration}

    def setup(self,name,email,password,business):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM users LIMIT 1').fetchone(): raise Problem('Setup is already complete.',409)
            user=self._new_user(db,name,email,password,allow_operator=True)
            tenant=uid()
            db.execute('INSERT INTO tenants VALUES(?,?)',(tenant,required(business,'Business name',100)))
            db.execute('INSERT INTO members VALUES(?,?,?)',(tenant,user,'admin'))
            return self._session(db,user)

    def signup(self,name,email,password,business,remember=False):
        if os.environ.get('TW_PUBLIC_SIGNUP','false').lower()!='true':raise Problem('Public account creation is not enabled.',403)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM users LIMIT 1').fetchone():raise Problem('The platform owner must complete initial setup first.',403)
            normalized=email.strip().lower() if isinstance(email,str) else ''
            if db.execute('SELECT 1 FROM users WHERE email=?',(normalized,)).fetchone():raise Problem('This email already has an account. Sign in instead.',409)
            user=self._new_user(db,name,email,password)
            tenant=uid();db.execute('INSERT INTO tenants VALUES(?,?)',(tenant,required(business,'Business name',100)))
            db.execute('INSERT INTO members VALUES(?,?,?)',(tenant,user,'admin'))
            db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,'Account registration','account.signup',now()))
            return dict(self._session(db,user,remember),tenant_id=tenant)

    def login(self,email,password,code=None,remember=False):
        if not isinstance(password,str) or len(password)>256: raise Problem('Invalid email or password.',401)
        with self.db() as db:
            u=db.execute('SELECT * FROM users WHERE email=?',(str(email).lower().strip(),)).fetchone()
            salt=u['salt'] if u else '00'*16
            candidate=password_hash(password,salt)
            if not u or not hmac.compare_digest(candidate,u['password']): raise Problem('Invalid email or password.',401)
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM users WHERE id=? AND salt=? AND password=?',(u['id'],u['salt'],u['password'])).fetchone():raise Problem('Credentials changed. Sign in again.',401)
            try:account_mfa.consume(db,u['id'],code)
            except account_mfa.MFAError as e:raise Problem(str(e),e.code)
            return self._session(db,u['id'],remember)

    def request_password_reset(self,email):return password_recovery.request(self,email)

    def complete_password_reset(self,token,password):return password_recovery.complete(self,token,password)

    def process_recovery_mail_once(self):return password_recovery.process_once(self)

    def mfa_status(self,ctx):
        with self.db() as db:return account_mfa.status(db,ctx['user']['id'])

    def update_profile(self,ctx,data):
        if not isinstance(data,dict) or set(data)!={'name'}:raise Problem('Only the display name can be updated here.')
        name=required(data.get('name'),'Display name',100)
        if any(ord(c)<32 or ord(c)==127 for c in name):raise Problem('Display name cannot contain control characters.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            user=db.execute('SELECT id,name,email FROM users WHERE id=?',(ctx['user']['id'],)).fetchone()
            if not user:raise Problem('Account is no longer available.',401)
            db.execute('UPDATE users SET name=? WHERE id=?',(name,user['id']))
            for row in db.execute('SELECT tenant FROM members WHERE user=?',(user['id'],)):
                db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(row['tenant'],user['name'],'account.profile.updated',now()))
            return {'id':user['id'],'name':name,'email':user['email']}

    def account_mfa(self,ctx,operation,data):
        try:return account_mfa.action(self,ctx,operation,data)
        except account_mfa.MFAError as e:raise Problem(str(e),e.code)

    def logout(self,token):
        with self.db() as db: db.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),))

    def _replace_password(self,db,user,new_password,action):
        if not isinstance(new_password,str) or not 12<=len(new_password)<=256:raise Problem('Use a password of 12–256 characters.')
        salt=secrets.token_hex(16)
        db.execute('UPDATE users SET salt=?,password=? WHERE id=?',(salt,password_hash(new_password,salt),user['id']))
        db.execute('DELETE FROM sessions WHERE user=?',(user['id'],))
        db.execute('UPDATE api_tokens SET revoked=1 WHERE user=?',(user['id'],))
        db.execute('UPDATE password_resets SET revoked=? WHERE user=? AND used=0',(now(),user['id']))
        for row in db.execute('SELECT tenant FROM members WHERE user=?',(user['id'],)):
            db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(row['tenant'],'Account security',action,now()))
        return {'changed':True,'sessions_revoked':True}

    def change_password(self,ctx,current_password,new_password):
        if not isinstance(current_password,str) or not 12<=len(current_password)<=256:raise Problem('Current password is incorrect.',403)
        if current_password==new_password:raise Problem('Choose a different new password.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');user=db.execute('SELECT * FROM users WHERE id=?',(ctx['user']['id'],)).fetchone()
            if not user or not hmac.compare_digest(password_hash(current_password,user['salt']),user['password']):raise Problem('Current password is incorrect.',403)
            return self._replace_password(db,user,new_password,'account.password.changed')

    def operator_reset_password(self,email,new_password):
        if not isinstance(email,str):raise Problem('An existing account email is required.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');user=db.execute('SELECT * FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
            if not user:raise Problem('Account not found; no account was created.',404)
            return self._replace_password(db,user,new_password,'account.password.operator_recovery')

    def inspect_invitation(self,token):
        try:return inspect_invite(self,token)
        except InviteError as e:raise Problem(str(e),e.code)

    def message_analytics(self,ctx,start,end):
        try:return traffic_report(self,ctx,start,end)
        except ReportError as e:raise Problem(str(e),e.code)

    def accept_invitation(self,data):
        try:return accept_invite(self,data)
        except InviteError as e:raise Problem(str(e),e.code)

    def auth(self,token,tenant=None):
        with self.db() as db:
            u=db.execute('SELECT u.id,u.name,u.email FROM users u JOIN sessions s ON s.user=u.id WHERE s.token=? AND s.expires>?',(hashlib.sha256(str(token).encode()).hexdigest(),now())).fetchone()
            if not u: raise Problem('Please sign in.',401)
            memberships=[dict(x) for x in db.execute('SELECT t.id,t.name,m.role FROM tenants t JOIN members m ON m.tenant=t.id WHERE m.user=? ORDER BY t.rowid',(u['id'],))]
            selected=next((x for x in memberships if x['id']==tenant),None) if tenant else (memberships[0] if memberships else None)
            if not selected: raise Problem('Workspace access denied.',403)
            return {'_session_hash':hashlib.sha256(str(token).encode()).hexdigest(),'user':dict(u),'tenant_id':selected['id'],'workspace':selected,'workspaces':memberships,'role':selected['role']}

    def _list(self,db,tenant,kind):
        return [dict(json.loads(x['data']),id=x['id']) for x in db.execute('SELECT id,data FROM entities WHERE tenant=? AND kind=? ORDER BY rowid',(tenant,kind))]

    def _get(self,db,tenant,kind,id):
        row=db.execute('SELECT data FROM entities WHERE tenant=? AND kind=? AND id=?',(tenant,kind,id)).fetchone()
        if not row: raise Problem('Record not found in this workspace.',404)
        return dict(json.loads(row['data']),id=id)

    def _put(self,db,tenant,kind,data,id=None):
        if id: self._get(db,tenant,kind,id)
        else: id=uid()
        data={k:v for k,v in data.items() if k!='id'}
        db.execute('INSERT INTO entities VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(id,tenant,kind,json.dumps(data)))
        return dict(data,id=id)

    def _message(self,db,tenant,contact,body,direction,status='simulated',external_id=None,ts=None):
        id=uid()
        db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)',(id,tenant,contact,direction,body,status,ts if ts is not None else now(),external_id))
        if direction=='out' and status=='accepted':track_accepted_reply(self,db,tenant,id,now())
        return dict(id=id,contact=contact,body=body,direction=direction,status=status,ts=ts or now())

    def state(self,ctx):
        tenant=ctx['tenant_id']
        with self.db() as db:
            db.execute('BEGIN')
            data={('replies' if k=='reply' else k+'s'):self._list(db,tenant,k) for k in ['contact','template','campaign','rule','flow','sequence','reply','aichat','aiagent','knowledge','deal','task','airun','finding','aijob','segment']}
            for flow in data['flows']:
                if ctx['role']=='admin':flow['published_versions']=flow_publishing.history(db,tenant,flow['id'])
                else:flow.pop('draft',None)
            data['aichats']=[c for c in data['aichats'] if c.get('owner')==ctx['user']['id']]
            data['aijobs']=[public_job(j) for j in data['aijobs'] if j.get('owner')==ctx['user']['id']]
            data['messages']=[dict(x) for x in db.execute('SELECT * FROM (SELECT rowid AS ordinal,* FROM messages WHERE tenant=? ORDER BY rowid DESC LIMIT 2000) ORDER BY ts,ordinal',(tenant,))]
            data['growth']=growth_services.state(self,db,ctx)
            data['api_tokens']=api_tokens.listing(self,ctx,strict=False)
            data['members']=[dict(x) for x in db.execute('SELECT u.id,u.name,u.email,m.role FROM users u JOIN members m ON m.user=u.id WHERE m.tenant=?',(tenant,))]
            data['product_feedback']=product_feedback.state(db,ctx)
            data.update(internal_comments.state(self,db,ctx))
            data['team_operations']=team_operations.state(self,db,tenant)
            data['invitations']=list_invites(self,db,ctx)
            data['audit']=[dict(x) for x in db.execute('SELECT actor,action,ts FROM audit WHERE tenant=? ORDER BY id DESC LIMIT 30',(tenant,))]
            customer=customer_state(self,db,tenant);data['customer_assistant']=customer['settings'];data['customer_assistant_runtime']=customer['runtime'];data['customer_reply_jobs']=customer['jobs']
            data['external_agents']=[public_agent(tenant,a) for a in self._list(db,tenant,'externalagent')]
            data['webhook_events']=recent_events(db,tenant)
            data['sequence_runs']=sequence_run_state(self,db,tenant)
            data['knowledge_web_self_service']=os.environ.get('TW_KNOWLEDGE_WEB_SELF_SERVICE','false').lower()=='true'
            data['knowledge_documents']=self._list(db,tenant,'knowledgedocument')
            data['media_assets']=[a for a in self._list(db,tenant,'media') if a.get('source')!='received']
            data['received_media']=received_media_state(db,tenant)
            data['rule_executions']=rule_history(db,tenant)
            data['no_response_evaluations']=no_response_history(self,db,tenant)
            data['flow_sends']=flow_delivery.history(db,tenant)
            data['flow_live_ready']=flow_delivery.ready(tenant)
            data['pipeline']=pipeline_state(self,db,tenant)
            data['knowledge_usage']=knowledge_usage_state(self,db,tenant)
            data['media_sends']=self._list(db,tenant,'mediasend')
            data['media_status']=media_status(tenant)
            data['commerce']=commerce_state(self,db,tenant)
            data['owned_commerce']=owned_commerce.state(self,db,tenant)
            data['services']=client_services.state(self,db,ctx)
            data['provider_checks']=provider_checks.state(self,db,tenant)
            data['calling']=dict(whatsapp_calls.status(tenant),calls=[whatsapp_calls.public(c) for c in self._list(db,tenant,'voicecall')[-100:]],requests=[whatsapp_calls.public(c) for c in self._list(db,tenant,'callpermission')[-50:]])
            data['queue']=[dict(x) for x in db.execute('SELECT id,campaign,contact,status,due,error,external_id FROM outbound WHERE tenant=? ORDER BY rowid DESC LIMIT 500',(tenant,))]
        data['whatsapp_connection']=embedded_signup.state(self,ctx)
        return dict(data,context={k:v for k,v in ctx.items() if not k.startswith('_')},meta=meta_status(tenant),ai=ai_status(tenant),sandbox=os.environ.get('TW_SANDBOX','false').lower()=='true')

    def _contact(self,db,t,d):
        old=self._get(db,t,'contact',d['id']) if d.get('id') else {}
        p=phone_number(d.get('phone',old.get('phone')))
        if any(c['phone']==p and c['id']!=d.get('id') for c in self._list(db,t,'contact')): raise Problem('This phone number already exists.',409)
        tags=d.get('tags',old.get('tags',[]))
        if isinstance(tags,str): tags=[x.strip() for x in tags.split(',') if x.strip()]
        if not isinstance(tags,list) or len(tags)>25 or any(not isinstance(x,str) or len(x)>60 for x in tags): raise Problem('Use up to 25 short text tags.')
        attrs=d.get('attributes',old.get('attributes',{}))
        if not isinstance(attrs,dict) or len(attrs)>50 or len(json.dumps(attrs))>10000: raise Problem('Custom attributes must be an object with up to 50 fields.')
        return self._put(db,t,'contact',dict(old,name=required(d.get('name',old.get('name')),'Contact name',100),phone=p,tags=list(dict.fromkeys(tags)),optin=d.get('optin',old.get('optin',False)) is True,attributes=attrs,status=old.get('status','open'),assignee=old.get('assignee',''),last_inbound=old.get('last_inbound',0),source=old.get('source','manual')),d.get('id'))

    def action(self,ctx,action,d):
        if not isinstance(action,str) or not 1<=len(action)<=100 or not isinstance(d,dict):raise Problem('Use a named action and an object payload.')
        t=ctx['tenant_id']; user=ctx['user']['id']
        try:client_services.enforce(self,ctx,action)
        except ServiceError as e:raise Problem(str(e),e.code)
        if action.startswith('growth.form.'):return whatsapp_forms.action(self,ctx,action,d)
        if action.startswith('growth.'):return growth_services.action(self,ctx,action,d)
        if action.startswith('whatsapp.'):
            try:return embedded_signup.action(self,ctx,action,d)
            except embedded_signup.ConnectionError as e:raise Problem(str(e),e.code) from None
        if action.startswith('ai.connection.'):
            try:return ai_connection.action(self,ctx,action,d)
            except embedded_signup.ConnectionError as e:raise Problem(str(e),e.code) from None
        if action=='services.release-failed':
            from service_jobs import release_failed
            try:return release_failed(self,ctx,d.get('id'))
            except ServiceError as e:raise Problem(str(e),e.code)
        if action=='providers.check':
            try:return provider_checks.check(self,ctx,d.get('provider'))
            except ServiceError as e:raise Problem(str(e),e.code)
        if action.startswith('calls.'):
            try:return whatsapp_calls.action(self,ctx,action,d)
            except ServiceError as e:raise Problem(str(e),e.code)
        if action.startswith(('payments.','billing.','shipping.','clients.')):
            try:
                if action.startswith(('payments.','billing.')):return payment_services.action(self,ctx,action,d)
                if action.startswith('shipping.'):return shipping_services.action(self,ctx,action,d)
                return client_services.action(self,ctx,action,d)
            except ServiceError as e:raise Problem(str(e),e.code)
            except Exception as e:
                from provider_transport import RemoteError
                if isinstance(e,RemoteError):raise Problem(str(e),502) from None
                raise
        if action=='message.send' and any(flag in d and type(d[flag]) is not bool for flag in ['note','live']):raise Problem('Message note/live flags must be true or false.')
        if action in ['demo.seed','message.simulate','campaign.run'] or action=='message.send' and not d.get('live') and not d.get('note'):
            if os.environ.get('TW_SANDBOX','false').lower()!='true':raise Problem('Simulation is disabled. Configure Meta for real messaging, or explicitly enable a separate sandbox.')
        if action in ['feedback.save','feedback.status']:return product_feedback.action(self,ctx,action,d)
        if action=='notification.read':return internal_comments.read(self,ctx,d)
        if action in ['team.save','availability.set','chat.route']:return team_operations.action(self,ctx,action,d)
        if action in ['member.role','member.remove']:
            try:return member_action(self,ctx,action,d)
            except MemberError as e:raise Problem(str(e),e.code)
        if action.startswith('invite.'):
            try:return invitation_action(self,ctx,action,d)
            except InviteError as e:raise Problem(str(e),e.code)
        if action.startswith('customer-assistant.'):
            try:return customer_action(self,ctx,action,d)
            except CustomerError as e:raise Problem(str(e),e.code)
            except ValueError as e:raise Problem(str(e))
        if action.startswith('segment.'):
            try:return segment_action(self,ctx,action,d)
            except SegmentError as e:raise Problem(str(e),e.code)
            except ValueError as e:raise Problem(str(e))
        if action.startswith('external-agent.'):
            try:return external_action(self,ctx,action,d)
            except ExternalError as e:raise Problem(str(e),e.code)
            except ValueError as e:raise Problem(str(e))
        if action.startswith('sequence.'):
            try:return sequence_action(self,ctx,action,d,now())
            except DripError as e:raise Problem(str(e),e.code)
            except ValueError as e:raise Problem(str(e))
        if action.startswith('knowledge.website.'):
            try:return website_action(self,ctx,action,d)
            except KnowledgeError as e:raise Problem(str(e),e.code)
            except ValueError as e:raise Problem(str(e))
        if action.startswith('knowledge.document.'):
            try:return document_action(self,ctx,action,d)
            except KnowledgeError as e:raise Problem(str(e),e.code)
        if action=='media.receive.download':
            try:return download_received_media(self,ctx,d)
            except MediaError as e:raise Problem(str(e),e.code)
        if action=='media.send':
            try:return send_stored_media(self,ctx,d)
            except MediaError as e:raise Problem(str(e),e.code)
        if action.startswith('shopify.order.'):
            try:return order_action(self,ctx,action,d)
            except CommerceError as e:raise Problem(str(e),e.code)
        if action.startswith('commerce.'):
            try:return owned_commerce.action(self,ctx,action,d)
            except CommerceError as e:raise Problem(str(e),e.code)
        if action=='shopify.sync':
            try:return sync_shopify(self,ctx,d.get('kind'),d.get('cursor'))
            except CommerceError as e:raise Problem(str(e),e.code)
        if action.startswith('ai.chat.'):
            try:return chat_action(self,ctx,action,d)
            except ChatError as e:raise Problem(str(e),e.code)
            except ValueError as e:raise Problem(str(e))
        if action=='ai.ask':return self._ai_ask(ctx,d)
        if action=='ai.run':return self._ai_run(ctx,d)
        agent_actions={'contact.save','contacts.import','chat.update','chat.takeover','chat.resume','message.send','message.simulate','deal.save','task.save','task.complete'}
        if ctx['role']!='admin' and action not in agent_actions: raise Problem('Administrator access required.',403)
        if action=='message.send' and d.get('live'):
            return self._live_reply(ctx,d)
        if action in ['templates.sync','template.submit']:
            return self._template_provider_action(ctx,action,d)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if action=='workspace.create':
                id=uid(); name=required(d.get('name'),'Workspace name',100)
                db.execute('INSERT INTO tenants VALUES(?,?)',(id,name)); db.execute('INSERT INTO members VALUES(?,?,?)',(id,user,'admin'))
                result={'id':id,'name':name}
            elif action=='member.add':
                role=d.get('role','agent')
                if role not in ['admin','agent']: raise Problem('Choose admin or agent.')
                email=str(d.get('email','')).strip().lower()
                existing=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
                member=existing['id'] if existing else self._new_user(db,d.get('name'),email,d.get('password'))
                if db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(t,member)).fetchone(): raise Problem('User is already a member.')
                db.execute('INSERT INTO members VALUES(?,?,?)',(t,member,role)); result={'id':member}
            elif action=='pipeline.save':
                try:result=pipeline_save(self,db,ctx,d)
                except ValueError as e:raise Problem(str(e))
            elif action in ['deal.save','task.save','task.complete']:
                try:result=crm_action(self,db,ctx,action,d)
                except ValueError as e:raise Problem(str(e))
            elif action=='finding.review':
                try:result=review_finding(self,db,ctx,d)
                except ValueError as e:raise Problem(str(e),409)
            elif action=='contact.save':
                before=self._get(db,t,'contact',d['id']) if d.get('id') else None
                result=contact_rule_change(self,db,t,before,self._contact(db,t,d))
            elif action=='contacts.import':
                text=required(d.get('csv'),'CSV',1000000)
                reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
                if not reader.fieldnames or not {'name','phone'}.issubset(reader.fieldnames): raise Problem('CSV requires name and phone columns.')
                imported=0; errors=[]
                for i,row in enumerate(reader,2):
                    if i>5001: errors.append('Import limit: 5,000 rows.'); break
                    try:
                        self._contact(db,t,dict(name=row.get('name'),phone=row.get('phone'),tags=row.get('tags',''),optin=str(row.get('optin','')).lower() in ['true','1','yes']))
                        imported+=1
                    except Problem as e: errors.append('Row '+str(i)+': '+str(e))
                result={'imported':imported,'errors':errors}
            elif action=='chat.update':
                c=self._get(db,t,'contact',d.get('id'))
                status=d.get('status',c['status']); assignee=d.get('assignee',c['assignee'])
                if status not in ['open','pending','solved']: raise Problem('Invalid conversation status.')
                if assignee and not db.execute('SELECT 1 FROM members WHERE tenant=? AND user=?',(t,assignee)).fetchone(): raise Problem('Choose a member of this workspace.')
                team_operations.assignment(self,db,t,c['id'],c.get('assignee'),assignee,user,'manual')
                result=status_rule_change(self,db,t,c,self._put(db,t,'contact',dict(c,status=status,assignee=assignee),c['id']))
            elif action in ['chat.takeover','chat.resume']:
                c=self._get(db,t,'contact',d.get('id'))
                c.pop('flow_session',None)
                if action=='chat.takeover':
                    team_operations.assignment(self,db,t,c['id'],c.get('assignee'),user,user,'takeover')
                    c.update(automation_hold=True,assignee=user,status='pending');c.pop('outgoing_watch',None)
                else:
                    c.update(automation_hold=False)
                    if c.get('handoff',{}).get('active'):c['handoff']=dict(c['handoff'],active=False,resolved_at=now(),resolved_by=user)
                result=self._put(db,t,'contact',c,c['id'])
            elif action=='message.send':
                c=self._get(db,t,'contact',d.get('contact_id')); body=required(d.get('body'),'Message')
                note=d.get('note') is True
                result=internal_comments.create(self,db,ctx,c,body,d.get('mentions',[])) if note else self._message(db,t,c['id'],body,'out','simulated')
            elif action=='message.simulate':
                c=self._get(db,t,'contact',d.get('contact_id'))
                result=self._inbound(db,t,{'id':'demo-'+uid(),'from':c['phone'],'text':{'body':required(d.get('body'),'Message')},'timestamp':str(now())},True)
            elif action=='template.save':
                name=required(d.get('name'),'Template name',512)
                if not re.fullmatch(r'[a-z0-9_]+',name): raise Problem('Template names use lowercase letters, numbers and underscores.')
                category=d.get('category','UTILITY')
                if category not in ['MARKETING','UTILITY','AUTHENTICATION']: raise Problem('Invalid template category.')
                if category=='AUTHENTICATION':raise Problem('Authentication templates require the dedicated OTP workflow; this editor supports marketing and utility templates.')
                try:rich=rich_text_fields(d)
                except ValueError as e:raise Problem(str(e))
                result=self._put(db,t,'template',dict(name=name,body=required(d.get('body'),'Template body',1024),language=required(d.get('language','en'),'Language',20),category=category,status='local_draft',updated=now(),**rich),d.get('id'))
            elif action=='campaign.save':
                template=self._get(db,t,'template',d.get('template_id'))
                if template.get('category')=='AUTHENTICATION':raise Problem('Authentication templates cannot be used for broadcast campaigns.')
                schedule=d.get('schedule','')
                if not isinstance(schedule,str) or len(schedule)>40: raise Problem('Invalid schedule.')
                tag=str(d.get('tag',''))[:60]
                audience=segment_audience(self,db,t,{'tag':tag,'segment_id':d.get('segment_id')})
                result=self._put(db,t,'campaign',{'name':required(d.get('name'),'Campaign name',150),'template_id':template['id'],'tag':tag,'segment_id':d.get('segment_id') or '','schedule':schedule,'status':'draft','audience':len(audience),'created':now(),'simulated':0},d.get('id'))
            elif action=='campaign.run':
                c=self._get(db,t,'campaign',d.get('id'))
                if c['status']!='draft': raise Problem('This campaign already ran. Create another draft to run again.',409)
                template=self._get(db,t,'template',c['template_id'])
                audience=segment_audience(self,db,t,c)
                if not audience: raise Problem('No opted-in contacts match this audience.')
                for p in audience:
                    body=template['body'].replace('{{name}}',p['name'])
                    self._message(db,t,p['id'],body,'out','simulated')
                result=self._put(db,t,'campaign',dict(c,status='demo_complete',audience=len(audience),simulated=len(audience)),c['id'])
            elif action=='campaign.launch':
                c=self._get(db,t,'campaign',d.get('id'));template=self._get(db,t,'template',c['template_id'])
                if template.get('status')!='APPROVED' or not template.get('meta_id'):raise Problem('A synced Meta-approved template is required.')
                if not meta_status(t)['live']:raise Problem('Live sending must be enabled on the server before launching a campaign.')
                if c['status']!='draft':raise Problem('This campaign has already been launched.',409)
                audience=segment_audience(self,db,t,c)
                if not audience:raise Problem('No opted-in contacts match this audience.')
                due=now()
                if c.get('schedule'):
                    from datetime import datetime
                    try:
                        scheduled=datetime.fromisoformat(c['schedule'])
                        if scheduled.tzinfo is None:raise ValueError('timezone required')
                        due=max(due,int(scheduled.timestamp()))
                    except ValueError:raise Problem('Schedule must include a timezone offset.')
                for contact in audience:
                    db.execute('INSERT INTO outbound VALUES(?,?,?,?,?,?,?,?,?,?)',(uid(),t,c['id'],contact['id'],json.dumps(template),'queued',due,0,'',None))
                result=self._put(db,t,'campaign',dict(c,status='queued',audience=len(audience),mode='live'),c['id'])
            elif action=='campaign.cancel':
                c=self._get(db,t,'campaign',d.get('id'))
                db.execute("UPDATE outbound SET status='cancelled' WHERE tenant=? AND campaign=? AND status='queued'",(t,c['id']))
                result=self._put(db,t,'campaign',dict(c,status='cancelled'),c['id'])
            elif action in ['flow.draft.save','flow.publish','flow.draft.restore']:
                try:result=flow_publishing.action(self,db,ctx,action,d,now())
                except ValueError as e:raise Problem(str(e))
            elif action in ['rule.save','flow.save']:
                kind=action.split('.')[0]
                old=self._get(db,t,kind,d['id']) if d.get('id') else {}
                reply=d.get('reply','')
                if kind=='rule' and ('actions' in d or old.get('actions')):
                    if not isinstance(reply,str) or len(reply)>4096:raise Problem('Reply metadata must be bounded text.')
                else:reply=required(reply,'Reply')
                event=d.get('event',old.get('event','incoming_message'));trigger_attribute=d.get('trigger_attribute',old.get('trigger_attribute',''))
                keyword=d.get('keyword','')
                if kind=='flow' or event=='incoming_message':keyword=required(keyword,'Keyword',100).lower()
                elif not isinstance(keyword,str) or len(keyword)>100:raise Problem('Keyword metadata must be bounded text.')
                values={'name':required(d.get('name'),'Name',150),'keyword':keyword,'reply':reply,'enabled':d.get('enabled') is True,'executions':old.get('executions',0)}
                if kind=='rule':
                    try:validate_trigger(event,trigger_attribute)
                    except RuleError as e:raise Problem(str(e),e.code)
                    values.update(event=event,trigger_attribute=trigger_attribute)
                    if event=='customer_no_response':
                        delay=d.get('wait_seconds',old.get('wait_seconds',3600))
                        if type(delay) is not int or not 1<=delay<=604800:raise Problem('No-response wait must be 1–604,800 whole seconds.')
                        values.update(wait_seconds=delay,after_message_ordinal=db.execute('SELECT COALESCE(MAX(rowid),0) FROM messages WHERE tenant=?',(t,)).fetchone()[0])
                    priority=d.get('priority',old.get('priority',100))
                    if type(priority) is not int or not 0<=priority<=1000:raise Problem('Rule priority must be a whole number from 0 to 1,000.')
                    implicit=old.get('actions',[{'type':'draft','value':reply}])
                    if 'actions' not in d and 'reply' in d and implicit==[{'type':'draft','value':old.get('reply',reply)}]:implicit=[{'type':'draft','value':reply}]
                    try:values['actions']=validate_rule_actions(self,db,t,d.get('actions',implicit),d.get('segment_id',old.get('segment_id','')))
                    except RuleError as e:raise Problem(str(e),e.code)
                    values['segment_id']=d.get('segment_id',old.get('segment_id',''))
                    values['priority']=priority
                if kind=='flow':
                    if not db.execute("SELECT 1 FROM members WHERE tenant=? AND user=? AND role='admin'",(t,user)).fetchone():raise Problem('Administrator access required.',403)
                    mode=d.get('delivery_mode',old.get('delivery_mode','draft'))
                    if mode not in ['draft','live']:raise Problem('Choose draft or live chatbot delivery.')
                    values.update(delivery_mode=mode,owner=user)
                    try:
                        values['graph']=validate_graph(d.get('graph') or old.get('graph') or default_graph(values['reply']))
                        validate_members(values['graph'],{row['user'] for row in db.execute('SELECT user FROM members WHERE tenant=?',(t,))})
                        flow_resources(self,db,t,values['graph'],mode=='live')
                    except ValueError as e: raise Problem(str(e))
                    values['version']=old.get('version',0)+1
                    if old:
                        flow_publishing.record(db,t,old,user,now());cancel_sessions(self,db,t,old['id'],now())
                        if old.get('draft'):values['draft']=old['draft']
                result=self._put(db,t,kind,values,d.get('id'))
                if kind=='flow':flow_publishing.record(db,t,result,user,now())
            elif action=='reply.save':
                result=self._put(db,t,'reply',{'name':required(d.get('name'),'Name',150),'body':required(d.get('body'),'Reply')},d.get('id'))
            elif action in ['aiagent.save','aiagent.schedule','aiagent.archive']:
                try:result=configure_agent(self,db,ctx,action,d,now())
                except ValueError as e:raise Problem(str(e))
            elif action=='knowledge.save':
                if d.get('id'): self._get(db,t,'knowledge',d['id'])
                elif len(self._list(db,t,'knowledge'))>=8: raise Problem('Use up to 8 sources per workspace. Edit or remove an existing source first.')
                if not isinstance(d.get('enabled',True),bool): raise Problem('Enabled must be true or false.')
                result=self._put(db,t,'knowledge',{'title':required(d.get('title'),'Source title',120),'body':required(d.get('body'),'Source content',4000),'enabled':d.get('enabled',True),'updated':now()},d.get('id'))
            elif action=='entity.delete':
                kind=d.get('kind')
                if kind not in ['rule','flow','sequence','reply','template','campaign','knowledge']: raise Problem('This record type cannot be deleted.')
                self._get(db,t,kind,d.get('id'))
                if kind=='template' and any(c['template_id']==d['id'] for c in self._list(db,t,'campaign')): raise Problem('A campaign uses this template.')
                db.execute('DELETE FROM entities WHERE id=? AND tenant=?',(d['id'],t)); result={'deleted':True}
            elif action=='demo.seed': result=self._seed(db,t,user)
            else: raise Problem('Unknown action.',404)
            db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(t,ctx['user']['name'],action,now()))
            return result

    def _ai_ask(self,ctx,d):
        question=required(d.get('question'),'Question',4000)
        with self.db() as db:
            chat=self._get(db,ctx['tenant_id'],'aichat',d['id']) if d.get('id') else {'name':question[:60],'messages':[],'owner':ctx['user']['id'],'agent_id':d.get('agent_id') or ''}
            if chat['owner']!=ctx['user']['id']:raise Problem('AI conversation access denied.',403)
            if (chat.get('agent_id') or '')!=(d.get('agent_id') or ''):raise Problem('Start a new chat to change the selected agent.')
        state,context=self._ai_context(ctx,d)
        try:answer=ask_local(question,context,chat['messages'])
        except ValueError as e:raise Problem(str(e),503)
        chat['messages']=(chat['messages']+[{'role':'user','content':question},{'role':'assistant','content':answer}])[-24:]
        with self.db() as db:return self._put(db,ctx['tenant_id'],'aichat',chat,chat.get('id'))

    def _ai_context(self,ctx,d):
        state=self.state(ctx)
        if d.get('agent_id'):
            with self.db() as db:agent=self._get(db,ctx['tenant_id'],'aiagent',d['agent_id'])
            if agent.get('archived'):raise Problem('This agent is archived. Restore it before running.')
        else:agent=None
        context={'business':ctx['workspace']['name'],'page':str(d.get('page',''))[:100],'role':ctx['role'],'contacts':len(state['contacts']),'opted_in':sum(c['optin'] for c in state['contacts']),'tickets':{s:sum(c['status']==s for c in state['contacts']) for s in ['open','pending','solved']},'campaigns':[{'name':c['name'],'status':c['status'],'audience':c['audience']} for c in state['campaigns'][:30]],'templates':[{'name':t['name'],'body':t['body'],'status':t['status']} for t in state['templates'][:20]],'messages_by_status':{s:sum(m['status']==s for m in state['messages']) for s in ['accepted','sent','delivered','read','failed','unknown']}}
        with self.db() as db:context['knowledge_passages']=retrieve_documents(self,db,ctx['tenant_id'],d.get('question') or (agent or {}).get('instructions',''))
        context['knowledge_sources']=[{k:source[k] for k in ['id','title','body']} for source in state['knowledges'] if source.get('enabled')]
        context['connection_configuration']={'meta_configured':state['meta']['configured'],'live_gate_enabled':state['meta']['live'],'provider_health':'not verified','wallet_balance':None}
        context['automation_configuration']=[{'name':r['name'],'keyword':r['keyword'],'enabled':r['enabled'],'executions':r.get('executions',0)} for r in (state['rules']+state['flows'])[:30]]
        context['tag_counts']={tag:sum(tag in c['tags'] for c in state['contacts']) for tag in sorted({tag for c in state['contacts'] for tag in c['tags']})[:100]}
        context['queue_counts']={status:sum(q['status']==status for q in state['queue']) for status in ['queued','sending','accepted','sent','delivered','read','failed','unknown','cancelled']}
        context['queue_scope']='Counts cover at most 500 most recently recorded queue rows, not lifetime totals.'
        recent={}
        for message in state['messages']:
            if message['direction'] in ['in','out']:
                recent.setdefault(message['contact'],[]).append(message)
        contacts={c['id']:c for c in state['contacts']}
        context['current_timestamp']=now()
        context['conversation_scope']='At most 20 recently active contacts from the last 2,000 stored messages, with at most 3 messages each and 500 characters per message. This is a partial sample, not a full inbox scan. Scheduled and manual runs analyze only this bounded sample. No customer actions are performed during analysis.'
        context['recent_conversations']=[]
        candidates=sorted(recent.items(),key=lambda entry:max(m['ts'] for m in entry[1]),reverse=True)
        if d.get('contact_id'):candidates=[entry for entry in candidates if entry[0]==d['contact_id']]
        for contact_id,messages in candidates[:20]:
            c=contacts.get(contact_id)
            if not c:continue
            context['recent_conversations'].append({'contact_id':c['id'],'contact_name':c['name'],'status':c['status'],'assignee':c['assignee'],'optin':c['optin'],'last_inbound':c['last_inbound'],'messages':[{'direction':m['direction'],'id':m['id'],'body':m['body'][:500],'truncated':len(m['body'])>500,'status':m['status'],'ts':m['ts']} for m in messages[-3:]]})
        if agent:context['agent']={'name':agent['name'],'instructions':agent['instructions'],'permissions':'read_only','allowed_actions':allowed_actions(agent),'version':agent.get('version',0)}
        context['team_members']=[{'id':m['id'],'name':m['name']} for m in state['members'][:100]]
        context['_workspace_id']=ctx['tenant_id']
        if d.get('model'):
            if d['model'] not in state['ai']['models']:raise Problem('Choose a model allowed by this workspace server configuration.')
            context['_model']=d['model']
        mode=d.get('mode','ask')
        if mode not in ['ask','summary','draft','analysis']:raise Problem('Choose a valid assistant mode.')
        context['answer_mode']=mode
        if d.get('contact_id'):
            selected=next((c for c in state['contacts'] if c['id']==d['contact_id']),None)
            if not selected:raise Problem('Contact not found in this workspace.',404)
            context['recent_conversations']=[c for c in context['recent_conversations'] if c['contact_id']==selected['id']]
            context['selected_contact']={k:selected[k] for k in ['id','name','status','assignee','tags','optin']}
            context['conversation_scope']='Selected contact only, at most three messages of up to 500 characters within the most recent 2,000 recorded workspace messages. This is not the full conversation history.'
        return state,context

    def process_customer_reply_once(self):return customer_reply_worker(self)
    def process_flow_wait_once(self):return flow_wait_worker(self,now())
    def process_no_response_once(self):return no_response_worker(self,now())
    def process_flow_send_once(self):return flow_delivery.process_once(self)

    def process_webhook_once(self):return dispatch_webhook(self)

    def external_agent_callback(self,tenant,agent,raw,headers):
        try:return external_callback(self,tenant,agent,raw,headers)
        except ExternalError as e:raise Problem(str(e),e.code)
        except ValueError as e:raise Problem(str(e))

    def upload_knowledge_document(self,ctx,filename,raw):
        try:return upload_document(self,ctx,filename,raw)
        except KnowledgeError as e:raise Problem(str(e),e.code)

    def knowledge_passage(self,ctx,document_id,chunk_id):
        try:return document_passage(self,ctx,document_id,chunk_id)
        except KnowledgeError as e:raise Problem(str(e),e.code)

    def upload_media_asset(self,ctx,filename,mime,data):
        try:return upload_for_workspace(self,ctx,filename,mime,data)
        except MediaError as e:raise Problem(str(e),e.code)

    def read_media_asset(self,ctx,id):
        try:return read_asset(self,ctx,id)
        except MediaError as e:raise Problem(str(e),e.code)

    def shopify_webhook(self,tenant,raw,headers):
        try:return ingest_shopify_webhook(self,tenant,raw,headers)
        except CommerceError as e:raise Problem(str(e),e.code)

    def process_chat_job_once(self):return run_chat_job(self)

    def source_messages(self,ctx,contact_id,ids):
        if not isinstance(ids,list) or not 1<=len(ids)<=5 or any(not isinstance(id,str) or not id or len(id)>100 for id in ids):raise Problem('Choose one to five source message IDs.')
        ids=list(dict.fromkeys(ids))
        with self.db() as db:
            contact=self._get(db,ctx['tenant_id'],'contact',contact_id)
            rows=[dict(row) for row in db.execute('SELECT id,body,direction,status,ts FROM messages WHERE tenant=? AND contact=? AND id IN ('+','.join('?' for _ in ids)+')',[ctx['tenant_id'],contact_id]+ids)]
            if len(rows)!=len(ids):raise Problem('Source messages not found in this conversation.',404)
            return {'contact':{'id':contact['id'],'name':contact['name']},'messages':rows}

    def _ai_run(self,ctx,d,lease=None,trigger='manual'):
        agent_id=d.get('agent_id')
        if not agent_id:raise Problem('Choose a saved AI agent.')
        token=lease or uid();tenant=ctx['tenant_id'];result=None;error=''
        if not lease:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                try:claim_lease(self,db,tenant,agent_id,token,now())
                except ValueError as e:raise Problem(str(e),409)
        try:
            result=self._perform_ai_run(ctx,d,token,trigger)
            return result
        except Exception as e:
            error=str(e) if isinstance(e,Problem) else 'Agent execution failed. Inspect the run history.'
            raise
        finally:
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                owned=db.execute('SELECT 1 FROM agent_leases WHERE tenant=? AND agent=? AND token=?',(tenant,agent_id,token)).fetchone()
                if owned:
                    agent=self._get(db,tenant,'aiagent',agent_id)
                    self._put(db,tenant,'aiagent',dict(agent,last_run=now(),last_status=result['status'] if result else 'failed',last_error=error),agent_id)
                    db.execute('DELETE FROM agent_leases WHERE tenant=? AND agent=? AND token=?',(tenant,agent_id,token))

    def process_agent_schedule_once(self):
        status=ai_status()
        if not status['requested_enabled']:return False
        chosen=None;stamp=now()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute("SELECT id,tenant,data FROM entities WHERE kind='aiagent'").fetchall()
            due=sorted((dict(json.loads(r['data']),id=r['id'],tenant=r['tenant']) for r in rows),key=lambda a:a.get('next_run',0))
            for agent in due:
                if agent.get('archived') or not agent.get('schedule_enabled') or agent.get('next_run',0)>stamp:continue
                tenant=agent.pop('tenant')
                configured=ai_status(tenant)
                if not configured['enabled'] or not configured['configured']:continue
                ctx=scheduled_context(db,tenant,agent.get('schedule_owner'))
                if not ctx:
                    self._put(db,tenant,'aiagent',dict(agent,schedule_enabled=False,next_run=0,last_error='Schedule paused: its administrator no longer has access.'),agent['id'])
                    continue
                token=uid()
                try:claim_lease(self,db,tenant,agent['id'],token,stamp)
                except ValueError:continue
                self._put(db,tenant,'aiagent',dict(agent,next_run=stamp+agent['interval']),agent['id'])
                chosen=(ctx,agent['id'],token);break
        if not chosen:return False
        ctx,agent_id,token=chosen
        try:self._ai_run(ctx,{'agent_id':agent_id},lease=token,trigger='scheduled')
        except Problem:pass
        return True

    def _perform_ai_run(self,ctx,d,lease,trigger):
        if not d.get('agent_id'):raise Problem('Choose a saved AI agent.')
        state,context=self._ai_context(ctx,d)
        context['analysis_contract']=dict(CONTRACT,allowed_proposals={kind:value for kind,value in CONTRACT['allowed_proposals'].items() if kind in context['agent']['allowed_actions']})
        tenant=ctx['tenant_id'];stamp=now()
        latest={}
        for message in state['messages']:
            if message['ordinal']>latest.get(message['contact'],{}).get('ordinal',-1):latest[message['contact']]=message
        snapshots={c['id']:captured_fingerprint(c,latest.get(c['id'],{}).get('id')) for c in state['contacts']}
        with self.db() as db:
            run=self._put(db,tenant,'airun',{'agent_id':d['agent_id'],'agent_name':context['agent']['name'],'status':'running','created':stamp,'started_by':ctx['user']['id'],'summary':'','scope':context['conversation_scope'],'sample_contacts':len(context['recent_conversations']),'trigger':trigger})
        try:
            answer=ask_local('Analyze the supplied workspace using this agent role. Follow analysis_contract and return JSON only. Propose actions for review; never execute them.',context,[])
            summary,findings=parse_findings(answer,context)
        except (ValueError,TypeError,KeyError) as e:
            message=str(e) if isinstance(e,ValueError) else 'Analysis returned invalid structured findings.'
            with self.db() as db:self._put(db,tenant,'airun',dict(run,status='failed',error=message,finished=now()),run['id'])
            raise Problem(message,503) from None
        lost=False;result=None
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            current=self._get(db,tenant,'aiagent',d['agent_id'])
            if current.get('archived') or current.get('version',0)!=context['agent']['version'] or not lease_valid(db,tenant,d['agent_id'],lease,now()):
                self._put(db,tenant,'airun',dict(run,status='interrupted',error='Agent changed, archived or execution lease lost.',finished=now()),run['id'])
                lost=True
            else:
                for finding in findings:
                    self._put(db,tenant,'finding',dict(finding,run_id=run['id'],agent_name=run['agent_name'],status='pending',created=now(),target_fingerprint=snapshots.get(finding['contact_id'],'')))
                result=self._put(db,tenant,'airun',dict(run,status='completed',summary=summary,finished=now(),finding_count=len(findings)),run['id'])
                db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],'ai.run',now()))
        if lost:raise Problem('Agent changed, archived or execution lease lost; findings were not published.',409)
        return result

    def _template_provider_action(self,ctx,action,d):
        tenant=ctx['tenant_id']
        try:
            if action=='templates.sync':
                provider=list_templates(tenant)
                with self.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    existing=self._list(db,tenant,'template')
                    for t in provider.get('data',[]):
                        components=t.get('components',[]);body=next((x.get('text','') for x in components if x.get('type')=='BODY'),'')
                        old=next((x for x in existing if x.get('meta_id')==t['id']),None)
                        header=next((x.get('text','') for x in components if x.get('type')=='HEADER' and x.get('format')=='TEXT'),'')
                        footer=next((x.get('text','') for x in components if x.get('type')=='FOOTER'),'')
                        buttons=next((x.get('buttons',[]) for x in components if x.get('type')=='BUTTONS'),[])
                        self._put(db,tenant,'template',{'name':t['name'],'language':t['language'],'category':t.get('category','UTILITY'),'status':t['status'],'body':body,'header':header,'footer':footer,'buttons':buttons,'components':components,'meta_id':t['id'],'updated':now()},old['id'] if old else None)
                    db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],action,now()))
                return {'synced':len(provider.get('data',[])),'has_more':bool(provider.get('paging',{}).get('next'))}
            with self.db() as db:template=self._get(db,tenant,'template',d.get('id'))
            if template.get('meta_id'):raise Problem('This template already exists at Meta. Create a new local draft to submit a new template.')
            result=submit_template(tenant,template)
            with self.db() as db:
                saved=self._put(db,tenant,'template',dict(template,meta_id=result['id'],status=result.get('status','PENDING'),updated=now()),template['id'])
                db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(tenant,ctx['user']['name'],action,now()))
            return saved
        except ProviderError as e:raise Problem(str(e),502)

    def process_queue_once(self):
        """Claim once. Never automatically repeat an uncertain provider request."""
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            # A worker that vanished after claiming may have already sent the message.
            interrupted=db.execute("SELECT * FROM outbound WHERE status='sending' AND claimed<?",(now()-300,)).fetchall()
            db.execute("UPDATE outbound SET status='unknown',error='Worker interrupted; reconcile with Meta before retrying.' WHERE status='sending' AND claimed<?",(now()-300,))
            for lost in interrupted:sequence_after_submit(self,db,dict(lost),'unknown',now())
            rows=db.execute("SELECT * FROM outbound WHERE status='queued' AND due<=? ORDER BY rowid LIMIT 100",(now(),)).fetchall()
            job=next((dict(x) for x in rows if meta_status(x['tenant'])['live'] and sequence_eligible(self,db,dict(x),now())),None)
            if not job:return False
            contact=self._get(db,job['tenant'],'contact',job['contact'])
            status='sending' if contact['optin'] else 'skipped'
            db.execute('UPDATE outbound SET status=?,claimed=? WHERE id=?',(status,now(),job['id']))
            if status=='skipped':sequence_after_submit(self,db,job,status,now());self._update_campaign_queue(db,job);return True
        template=json.loads(job['payload'])
        try:
            external=send_template(job['tenant'],contact['phone'],template,contact['name'])
            result='accepted';error=''
        except ProviderError as e:external=None;result='failed' if e.definitive else 'unknown';error=str(e)
        except Exception:external=None;result='unknown';error='Uncertain provider result. Reconcile manually; automatic retry is disabled.'
        with self.db() as db:
            db.execute('UPDATE outbound SET status=?,external_id=?,error=? WHERE id=?',(result,external,error,job['id']))
            body=template.get('body','').replace('{{name}}',contact['name']).replace('{{1}}',contact['name'])
            self._message(db,job['tenant'],contact['id'],body,'out',result,external)
            sequence_after_submit(self,db,job,result,now())
            self._update_campaign_queue(db,job)
        return True

    def _update_campaign_queue(self,db,job):
        statuses=[x[0] for x in db.execute('SELECT status FROM outbound WHERE tenant=? AND campaign=?',(job['tenant'],job['campaign']))]
        campaign=self._get(db,job['tenant'],'campaign',job['campaign'])
        if campaign['status']=='cancelled':return
        status='queued' if any(x in ['queued','sending'] for x in statuses) else 'paused' if 'paused' in statuses else 'cancelled' if statuses and all(x=='cancelled' for x in statuses) else 'needs_attention' if any(x in ['unknown','failed'] for x in statuses) else 'submitted'
        self._put(db,job['tenant'],'campaign',dict(campaign,status=status),campaign['id'])

    def _live_reply(self,ctx,d):
        t=ctx['tenant_id']
        if d.get('note'): raise Problem('Internal notes cannot be sent live.')
        body=required(d.get('body'),'Message')
        with self.db() as db:
            c=self._get(db,t,'contact',d.get('contact_id'))
            last=c.get('last_real_inbound',0)
            if not 0<=now()-last<86400: raise Problem('The 24-hour customer service window is closed. An approved template is required.')
            if not meta_status(t)['live']: raise Problem('Live sending is disabled on the server.')
            record=self._message(db,t,c['id'],body,'out','sending')
        try:
            external=send_text(t,c['phone'],body)
        except Exception:
            with self.db() as db: db.execute('UPDATE messages SET status=? WHERE id=?',('unknown',record['id']))
            raise Problem('Provider result is uncertain. Check Meta before manually retrying; no automatic retry was made.',502)
        with self.db() as db:
            db.execute('UPDATE messages SET status=?,external_id=? WHERE id=?',('accepted',external,record['id']))
            track_accepted_reply(self,db,t,record['id'],now())
            db.execute('INSERT INTO audit(tenant,actor,action,ts) VALUES(?,?,?,?)',(t,ctx['user']['name'],'message.live',now()))
        return dict(record,status='accepted')

    def inbound(self,tenant,event,simulated=False):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM tenants WHERE id=?',(tenant,)).fetchone(): raise Problem('Unknown workspace.',404)
            return self._inbound(db,tenant,event,simulated)

    def _inbound(self,db,t,event,simulated):
        external=required(event.get('id'),'Message id',250)
        if db.execute('SELECT 1 FROM messages WHERE tenant=? AND external_id=?',(t,external)).fetchone(): return {'duplicate':True}
        p=phone_number(event.get('from')); text=event.get('text',{}).get('body') or '['+str(event.get('type','unsupported message'))+']'
        if event.get('type') in ['image','audio','video','document']:
            payload=event.get(event['type'])
            if isinstance(payload,dict) and isinstance(payload.get('caption'),str):text='['+event['type']+'] '+payload['caption'][:4096]
        text=required(text,'Inbound message',10000)
        c=next((c for c in self._list(db,t,'contact') if c['phone']==p),None)
        created=c is None;before=dict(c) if c else None
        if not c: c=self._contact(db,t,{'name':p,'phone':p,'optin':False})
        try: timestamp=min(int(event.get('timestamp',now())),now())
        except (TypeError,ValueError): timestamp=now()
        c=dict(c,last_inbound=max(c.get('last_inbound',0),timestamp),status='open')
        c=growth_services.inbound(self,db,t,c,event,simulated)
        if not simulated:whatsapp_forms.receive(self,db,t,c,event)
        if not simulated: c['last_real_inbound']=max(c.get('last_real_inbound',0),timestamp)
        stop=text.strip().lower() in ['stop','unsubscribe','cancel','stop all']
        if stop: c['optin']=False;c.pop('flow_session',None);c.pop('outgoing_watch',None)
        self._put(db,t,'contact',c,c['id'])
        message=self._message(db,t,c['id'],text,'in','simulated' if simulated else 'received',external,timestamp)
        if not simulated:
            c['last_real_inbound_ordinal']=db.execute('SELECT rowid FROM messages WHERE id=?',(message['id'],)).fetchone()[0];self._put(db,t,'contact',c,c['id'])
        if not simulated and event.get('type','text')!='text':
            record_received_media(self,db,t,message,event)
            c.update(status='pending',automation_hold=True);c.pop('flow_session',None);c.pop('outgoing_watch',None);self._put(db,t,'contact',c,c['id'])
            self._message(db,t,c['id'],'Received non-text message requires human review. This assistant does not inspect attachment content.','note','internal')
        if not simulated and not stop and not c.get('automation_hold'):
            c=dispatch_rule_event(self,db,t,c,'contact_created',message=message) if created else status_rule_change(self,db,t,before,c,message)
        if not simulated and not c.get('automation_hold'):enqueue_event(self,db,t,'message.received',external,{'contact_id':c['id'],'message':{'id':message['id'],'body':text,'direction':'in','ts':timestamp}})
        if not stop and not c.get('automation_hold'):
            if c.get('flow_session'):
                active=next((f for f in self._list(db,t,'flow') if f['id']==c['flow_session']['flow_id'] and f['enabled'] and f.get('graph') and f.get('version',0)==c['flow_session'].get('version',0)),None)
                if active:
                    self._run_flow(db,t,c,active,text,True,simulated=simulated)
                    return message
                c.pop('flow_session',None)
                self._put(db,t,'contact',c,c['id'])
            for kind in ['rule','flow']:
                candidates=self._list(db,t,kind)
                if kind=='rule':candidates.sort(key=lambda rule:rule.get('priority',100))
                for rule in candidates:
                    if kind=='rule' and rule.get('event','incoming_message')!='incoming_message':continue
                    if rule['enabled'] and rule['keyword'] in text.lower():
                        if kind=='rule':
                            if not execute_rule(self,db,t,rule,c,message):continue
                        elif rule.get('graph'): self._run_flow(db,t,c,rule,text,simulated=simulated)
                        else: self._message(db,t,c['id'],rule['reply'],'out','draft')
                        self._put(db,t,kind,dict(rule,executions=rule.get('executions',0)+1),rule['id'])
                        return message
            if not simulated:enqueue_customer_reply(self,db,t,c,message,text)
        return message

    def _run_flow(self,db,t,contact,flow,text,resume=False,timer=False,simulated=False,delivered=False):
        previous_assignee=contact.get('assignee','')
        execution=contact.get('flow_session',{}).get('execution','draft') if resume else 'live' if flow.get('delivery_mode')=='live' and not simulated else 'draft'
        if simulated and execution=='live':return True
        try:
            if execution=='live' and not flow_delivery.ready(t):raise FlowExecutionError('Live chatbot runtime is not configured and approved.')
            resources=flow_resources(self,db,t,flow['graph'],execution=='live')
            contact,drafts=run_graph(flow,contact,text,resume,timer=timer,timestamp=now(),member_ids={row['user'] for row in db.execute('SELECT user FROM members WHERE tenant=?',(t,))},execution=execution,delivered=delivered,resources=resources)
        except FlowExecutionError as error:
            contact=dict(contact,status='pending',automation_hold=True,flow_last_event={'status':'blocked','reason':str(error),'updated':now(),'flow_id':flow['id']});contact.pop('flow_session',None);contact.pop('outgoing_watch',None)
            self._put(db,t,'contact',contact,contact['id']);self._message(db,t,contact['id'],'Chatbot paused for human review: '+str(error),'note','internal');return False
        team_operations.assignment(self,db,t,contact['id'],previous_assignee,contact.get('assignee',''),flow.get('owner','Chatbot'),'chatbot',routing={'flow_id':flow['id']})
        if execution=='live' and drafts:flow_delivery.enqueue(self,db,t,flow,contact,drafts[0],resources)
        else:
            for body in drafts:self._message(db,t,contact['id'],body,'out','draft')
        self._put(db,t,'contact',contact,contact['id'])
        return True

    def delivery(self,tenant,external,status):
        ranks={'accepted':0,'sent':1,'delivered':2,'read':3,'failed':4}
        if status not in ranks: return
        with self.db() as db:
            row=db.execute('SELECT id,status FROM messages WHERE tenant=? AND external_id=?',(tenant,external)).fetchone()
            if row and ranks.get(row['status'],-1)<=ranks[status]: db.execute('UPDATE messages SET status=? WHERE id=?',(status,row['id']))
            job=db.execute('SELECT id,status FROM outbound WHERE tenant=? AND external_id=?',(tenant,external)).fetchone()
            if job and ranks.get(job['status'],-1)<=ranks[status]:db.execute('UPDATE outbound SET status=? WHERE id=?',(status,job['id']))
            changed=(row and row['status']!=status and ranks.get(row['status'],-1)<=ranks[status]) or (job and job['status']!=status and ranks.get(job['status'],-1)<=ranks[status])
            if changed:enqueue_event(self,db,tenant,'message.status',str(external)+':'+status,{'message_id':row['id'] if row else None,'provider_id':external,'status':status})

    def export_contacts(self,ctx):
        def safe(s):
            s=str(s)
            return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r')) else s
        out=io.StringIO(); w=csv.writer(out); w.writerow(['name','phone','tags','optin'])
        for c in self.state(ctx)['contacts']: w.writerow([safe(c['name']),c['phone'],safe(','.join(c['tags'])),'true' if c['optin'] else 'false'])
        return out.getvalue()

    def _seed(self,db,t,user):
        if self._list(db,t,'contact'): raise Problem('Load sample data only into an empty workspace.')
        for i,(name,tags,text) in enumerate([('Asha Rao',['Lead','Priority'],'Hi, can you share your pricing?'),('Rahul Shah',['Customer'],'Thank you! Can we book a demo?'),('Meera Patel',['Lead'],'I would like to know more about your services.'),('Kiran Das',['Customer'],'Please help me with my order.')]):
            c=self._contact(db,t,{'name':name,'phone':'91900000000'+str(i),'tags':tags,'optin':i!=3})
            self._inbound(db,t,{'id':'sample-'+uid(),'from':c['phone'],'text':{'body':text},'timestamp':str(now()-i*900)},True)
        template=self._put(db,t,'template',{'name':'welcome_message','body':'Hi {{name}}, thanks for your interest! How can our team help you today?','language':'en','category':'UTILITY','status':'local_draft','updated':now()})
        self._put(db,t,'rule',{'name':'Welcome and handoff','keyword':'hello','reply':'Hello! Thanks for reaching out. A member of our team will help you shortly.','enabled':True,'executions':0})
        self._put(db,t,'reply',{'name':'Business hours','body':'Our team is available Monday–Friday, 9 AM–6 PM. We will get back to you shortly.'})
        self._put(db,t,'campaign',{'name':'Welcome new leads','template_id':template['id'],'tag':'Lead','schedule':'','status':'draft','audience':2,'created':now(),'simulated':0})
        return {'loaded':True}
