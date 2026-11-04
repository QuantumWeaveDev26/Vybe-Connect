"""Loopback-only pilot server. Run with Python 3.13: python server.py."""
from recovery_mail import configuration as recovery_configuration
import argparse
import json
import os
import time
import threading
import secrets
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from store import Store, Problem
from meta import settings, signature_ok
from deployment import configuration
from auth_limits import consume as auth_attempt

ROOT=Path(__file__).resolve().parent


def load_env():
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key,value=line.split('=',1)
                if key.strip().startswith('TW_'): os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))


class Handler(BaseHTTPRequestHandler):
    server_version='TeamWave/0.1'

    def setup(self):
        super().setup();self.connection.settimeout(30)

    def log_message(self,*args): pass  # Request URLs may contain webhook tokens.

    def respond(self,code,data,content_type='application/json; charset=utf-8',cookie=None,disposition=None):
        if isinstance(data,(dict,list)): data=json.dumps(data,ensure_ascii=False).encode()
        elif isinstance(data,str): data=data.encode()
        self.send_response(code)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        if self.server.deployment.production:self.send_header('Strict-Transport-Security','max-age=31536000')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie: self.send_header('Set-Cookie',cookie)
        if disposition:self.send_header('Content-Disposition',disposition)
        self.end_headers();self.wfile.write(data)

    def host_ok(self):
        port=self.server.server_address[1]
        if self.server.deployment.production:return self.headers.get('Host','').lower() in {self.server.deployment.authority,self.server.deployment.authority+':443' if ':' not in self.server.deployment.authority else self.server.deployment.authority}
        return self.headers.get('Host') in ['127.0.0.1:'+str(port),'localhost:'+str(port)]

    def token(self):
        c=SimpleCookie()
        try: c.load(self.headers.get('Cookie',''))
        except Exception: return ''
        return c['tw_session'].value if 'tw_session' in c else ''

    def context(self):
        query=parse_qs(urlsplit(self.path).query)
        tenant=self.headers.get('X-Workspace') or query.get('workspace',[None])[0]
        return self.server.store.auth(self.token(),tenant)

    def do_GET(self):
        try:
            if not self.host_ok(): raise Problem('Invalid host.',403)
            path=urlsplit(self.path).path
            if path=='/healthz':self.respond(200,{'status':'ok'});return
            if path=='/readyz':
                try:
                    with self.server.store.db() as db:db.execute('SELECT 1 FROM tenants LIMIT 1').fetchone()
                except Exception:self.respond(503,{'status':'not_ready'});return
                self.respond(200,{'status':'ready'});return
            if path.startswith('/api/review/'):
                if self.server.review is None:raise Problem('Review mode is unavailable.',404)
                review=self.server.review;ctx=review.context
                if path=='/api/review/state':self.respond(200,review.state());return
                query=parse_qs(urlsplit(self.path).query)
                if path=='/api/review/analytics':self.respond(200,review.store.message_analytics(ctx,query.get('from',[''])[0],query.get('to',[''])[0]));return
                if path=='/api/review/chat-source':self.respond(200,review.store.source_messages(ctx,query.get('contact_id',[''])[0],query.get('ids',[''])[0].split(',')));return
                if path=='/api/review/knowledge-source':self.respond(200,review.store.knowledge_passage(ctx,query.get('document_id',[''])[0],query.get('chunk_id',[''])[0]));return
                if path=='/api/review/export':self.respond(200,review.store.export_contacts(ctx),'text/csv; charset=utf-8');return
                raise Problem('Unknown review resource.',404)
            if path=='/api/bootstrap': self.respond(200,{'review_available':self.server.review is not None,'password_recovery_available':recovery_configuration()['ready'],'initialized':self.server.store.initialized(),'setup_token_required':self.server.deployment.production and not self.server.store.initialized(),'deployment': 'hosted' if self.server.deployment.production else 'local'});return
            if path=='/api/account/mfa':self.respond(200,self.server.store.mfa_status(self.context()));return
            if path=='/api/state': self.respond(200,self.server.store.state(self.context()));return
            if path=='/api/analytics':
                query=parse_qs(urlsplit(self.path).query)
                self.respond(200,self.server.store.message_analytics(self.context(),query.get('from',[''])[0],query.get('to',[''])[0]));return
            if path=='/api/knowledge-source':
                query=parse_qs(urlsplit(self.path).query)
                self.respond(200,self.server.store.knowledge_passage(self.context(),query.get('document_id',[''])[0],query.get('chunk_id',[''])[0]));return
            if path=='/api/chat-source':
                query=parse_qs(urlsplit(self.path).query)
                self.respond(200,self.server.store.source_messages(self.context(),query.get('contact_id',[''])[0],query.get('ids',[''])[0].split(',')));return
            if path=='/api/media':
                query=parse_qs(urlsplit(self.path).query)
                data,mime,name=self.server.store.read_media_asset(self.context(),query.get('id',[''])[0])
                self.respond(200,data,mime,disposition='inline' if mime in ['image/jpeg','image/png'] else 'attachment; filename="'+name+'"');return
            if path=='/api/export': self.respond(200,self.server.store.export_contacts(self.context()),'text/csv; charset=utf-8');return
            if path.startswith('/webhook/'):
                t=path.rsplit('/',1)[-1]; q=parse_qs(urlsplit(self.path).query); s=settings(t)
                if s['VERIFY_TOKEN'] and q.get('hub.mode')==['subscribe'] and q.get('hub.verify_token')==[s['VERIFY_TOKEN']]: self.respond(200,q.get('hub.challenge',[''])[0],'text/plain');return
                raise Problem('Verification failed.',403)
            files={'/auth-entry.js':'auth-entry.js','/connectors.js':'connectors.js','/launch-layout.js':'launch-layout.js','/visuals.js':'visuals.js','/world-dots.json':'world-dots.json','/launch.js':'launch.js','/services.js':'services.js','/owned-commerce.js':'owned-commerce.js','/agent-directory.js':'agent-directory.js','/vybe-theme.css':'vybe-theme.css','/help-widget.css':'help-widget.css','/help-widget.js':'help-widget.js','/account-recovery.js':'account-recovery.js','/team-operations.js':'team-operations.js','/account.js':'account.js','/received-media.js':'received-media.js','/analytics-report.js':'analytics-report.js','/team-invitations.js':'team-invitations.js','/rule-actions.js':'rule-actions.js','/customer-assistant.js':'customer-assistant.js','/contact-segments.js':'contact-segments.js','/external-agents.js':'external-agents.js','/drip-sequences.js':'drip-sequences.js','/knowledge-documents.js':'knowledge-documents.js','/integrations.js':'integrations.js','/business.js':'business.js','/business.css':'business.css','/owner':'index.html','/':'index.html','/index.html':'index.html','/app.js':'app.js','/graph.js':'graph.js','/graph.css':'graph.css','/assistant.js':'assistant.js','/assistant.css':'assistant.css','/shell.js':'shell.js','/shell.css':'shell.css','/template-editor.js':'template-editor.js','/template-editor.css':'template-editor.css','/style.css':'style.css'}
            if path not in files: raise Problem('Not found.',404)
            p=ROOT/'static'/files[path]
            if not p.exists(): raise Problem('UI is not installed.',404)
            mime={'html':'text/html','js':'text/javascript','css':'text/css','json':'application/json'}[p.suffix[1:]]
            self.respond(200,p.read_bytes(),mime+'; charset=utf-8')
        except Problem as e: self.respond(e.code,{'error':str(e)})
        except Exception: self.respond(500,{'error':'An internal error occurred.'})

    def do_POST(self):
        try:
            if not self.host_ok(): raise Problem('Invalid host.',403)
            path=urlsplit(self.path).path
            if path.startswith('/api/review/'):raise Problem('Public review is read-only. Owner setup is required to make changes.',403)
            expected_origin=self.server.deployment.public_origin if self.server.deployment.production else 'http://'+self.headers.get('Host','')
            if not path.startswith(('/webhook/','/shopify-webhook/','/agent-callback/','/razorpay-webhook/')) and self.headers.get('Origin')!=expected_origin: raise Problem('Cross-origin writes are not allowed.',403)
            try: length=int(self.headers.get('Content-Length','0'))
            except ValueError: raise Problem('Invalid body length.')
            limit=5*1024*1024 if path=='/api/media-upload' else 2*1024*1024 if path.startswith('/shopify-webhook/') else 1500000
            if not 0<length<=limit: raise Problem('Request body exceeds this endpoint’s size limit.',413)
            raw=self.rfile.read(length)
            if path.startswith('/razorpay-webhook/'):
                from payment_services import webhook
                from service_jobs import ServiceError
                parts=path.strip('/').split('/')
                if len(parts)!=3 or parts[1] not in ('payments','billing'):raise Problem('Invalid payment webhook route.',404)
                try:result=webhook(self.server.store,parts[2],parts[1],raw,dict(self.headers))
                except ServiceError as e:raise Problem(str(e),e.code) from None
                self.respond(200,result);return
            if path.startswith('/agent-callback/'):
                parts=path.strip('/').split('/')
                if len(parts)!=3:raise Problem('Invalid agent callback path.',404)
                self.respond(200,self.server.store.external_agent_callback(parts[1],parts[2],raw,dict(self.headers)));return
            if path=='/api/knowledge-upload':
                query=parse_qs(urlsplit(self.path).query)
                self.respond(200,self.server.store.upload_knowledge_document(self.context(),query.get('name',[''])[0],raw));return
            if path=='/api/media-upload':
                query=parse_qs(urlsplit(self.path).query)
                self.respond(200,self.server.store.upload_media_asset(self.context(),query.get('name',[''])[0],self.headers.get('Content-Type','').split(';')[0],raw));return
            if path.startswith('/shopify-webhook/'):
                self.respond(200,self.server.store.shopify_webhook(path.rsplit('/',1)[-1],raw,dict(self.headers)));return
            if path.startswith('/webhook/'):
                tenant=path.rsplit('/',1)[-1]
                if not signature_ok(raw,self.headers.get('X-Hub-Signature-256',''),settings(tenant)['APP_SECRET']): raise Problem('Invalid webhook signature.',403)
                data=json.loads(raw)
                for entry in data.get('entry',[]):
                    for change in entry.get('changes',[]):
                        value=change.get('value',{})
                        expected=settings(tenant)['PHONE_ID']
                        if not expected or value.get('metadata',{}).get('phone_number_id')!=expected: raise Problem('Webhook phone number does not match workspace.',403)
                        if value.get('calls'):
                            from whatsapp_calls import ingest
                            from service_jobs import ServiceError
                            try:ingest(self.server.store,tenant,value['calls'])
                            except ServiceError as e:raise Problem(str(e),e.code) from None
                        for message in value.get('messages',[]): self.server.store.inbound(tenant,message)
                        for event in value.get('statuses',[]): self.server.store.delivery(tenant,event.get('id'),event.get('status'))
                self.respond(200,{'received':True});return
            data=json.loads(raw)
            if not isinstance(data,dict): raise Problem('JSON object required.')
            if path in ['/api/password/request','/api/password/reset']:
                identity=data.get('email') if path.endswith('/request') else data.get('token')
                if not auth_attempt(self.server.attempts,self.server.attempts_lock,self.client_address[0],path+':'+(identity if isinstance(identity,str) else ''),time.time()):raise Problem('Too many recovery attempts. Wait a minute.',429)
                if path.endswith('/request'):
                    started=time.monotonic();result=self.server.store.request_password_reset(data.get('email'))
                    time.sleep(max(0,0.15-(time.monotonic()-started)))
                    self.respond(200,result);return
                result=self.server.store.complete_password_reset(data.get('token'),data.get('new_password'))
                self.respond(200,result,cookie=self.server.deployment.cookie(logout=True));return
            if path.startswith('/api/account/mfa/'):
                ctx=self.context()
                if not auth_attempt(self.server.attempts,self.server.attempts_lock,self.client_address[0],'mfa:'+ctx['user']['id'],time.time()):raise Problem('Too many security attempts. Wait a minute.',429)
                result=self.server.store.account_mfa(ctx,path.rsplit('/',1)[-1],data)
                self.respond(200,result,cookie=self.server.deployment.cookie(logout=True) if result.get('sessions_revoked') else None);return
            if path=='/api/account/profile':
                ctx=self.context()
                if not auth_attempt(self.server.attempts,self.server.attempts_lock,self.client_address[0],'profile:'+ctx['user']['id'],time.time()):raise Problem('Too many profile updates. Wait a minute.',429)
                self.respond(200,self.server.store.update_profile(ctx,data));return
            if path=='/api/account/password':
                ctx=self.context()
                if not auth_attempt(self.server.attempts,self.server.attempts_lock,self.client_address[0],'password:'+ctx['user']['id'],time.time()):raise Problem('Too many password attempts. Wait a minute.',429)
                result=self.server.store.change_password(ctx,data.get('current_password'),data.get('new_password'))
                self.respond(200,result,cookie=self.server.deployment.cookie(logout=True));return
            if path in ['/api/login','/api/setup','/api/invitations/inspect','/api/invitations/accept']:
                identity=data.get('email') if path=='/api/login' else data.get('token') if path.startswith('/api/invitations/') else 'owner-setup'
                if not auth_attempt(self.server.attempts,self.server.attempts_lock,self.client_address[0],path+':'+(identity if isinstance(identity,str) else ''),time.time()):raise Problem('Too many login attempts. Wait a minute.',429)
                if path=='/api/invitations/inspect':
                    self.respond(200,self.server.store.inspect_invitation(data.get('token')));return
                if path=='/api/invitations/accept':result=self.server.store.accept_invitation(data)
                elif path=='/api/setup':
                    candidate=data.get('setup_token','')
                    if self.server.deployment.production and (not isinstance(candidate,str) or len(candidate)>256 or not secrets.compare_digest(candidate.encode('utf-8'),self.server.deployment.setup_token.encode('utf-8'))):raise Problem('A valid deployment setup token is required.',403)
                    owner=self.server.deployment.owner_email
                    if owner and (not isinstance(data.get('email'),str) or data['email'].strip().casefold()!=owner):raise Problem('Use the configured platform owner email for initial setup.',403)
                    result=self.server.store.setup(data.get('name'),data.get('email'),data.get('password'),data.get('business'))
                else: result=self.server.store.login(data.get('email'),data.get('password'),data.get('code'))
                self.respond(200,dict(ok=True,**({'tenant_id':result['tenant_id']} if 'tenant_id' in result else {})),cookie=self.server.deployment.cookie(result['token']));return
            if path=='/api/logout':
                self.server.store.logout(self.token());self.respond(200,{'ok':True},cookie=self.server.deployment.cookie(logout=True));return
            if path=='/api/action':
                payload=data.get('data',{})
                if not isinstance(payload,dict): raise Problem('Action data must be an object.')
                ctx=self.context();operation=data.get('action')
                if isinstance(operation,str) and operation.startswith(('payments.','billing.','shipping.','clients.','providers.','services.','calls.')) and operation not in ('calls.end','calls.reject','calls.release'):
                    if not auth_attempt(self.server.service_attempts,self.server.service_attempts_lock,self.client_address[0],ctx['user']['id']+':'+operation,time.time()):raise Problem('Too many service requests. Wait a minute.',429)
                self.respond(200,self.server.store.action(ctx,operation,payload));return
            raise Problem('Not found.',404)
        except Problem as e: self.respond(e.code,{'error':str(e)})
        except (ValueError,TypeError,KeyError): self.respond(400,{'error':'Invalid request data.'})
        except Exception: self.respond(500,{'error':'An internal error occurred.'})


def make_server(port=8787,path=None):
    deployment=configuration();store=Store(path or Path(os.environ.get('TW_DATA_DIR',str(ROOT/'data')))/'teamwave.db')
    if deployment.production and not store.initialized() and (not 32<=len(deployment.setup_token)<=256 or deployment.setup_token.startswith('REPLACE_')):raise ValueError('Fresh production setup requires a replaced TW_SETUP_TOKEN with 32–256 characters.')
    server=ThreadingHTTPServer((deployment.bind,port),Handler);server.daemon_threads=True
    server.deployment=deployment;server.store=store
    server.review=None
    if os.environ.get('TW_PUBLIC_REVIEW','false').lower()=='true':
        from public_review import PublicReview
        server.review=PublicReview()
    server.attempts={};server.attempts_lock=threading.Lock()
    server.service_attempts={};server.service_attempts_lock=threading.Lock()
    return server


if __name__=='__main__':
    load_env()
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8787);parser.add_argument('--db',type=Path)
    args=parser.parse_args();server=make_server(args.port,args.db)
    stop=threading.Event()
    def recovery_worker():
        while not stop.wait(1):
            try:server.store.process_recovery_mail_once()
            except Exception:print('Recovery email worker paused after an error; inspect private delivery state.',flush=True)
    threading.Thread(target=recovery_worker,daemon=True).start()
    def worker():
        while not stop.wait(1):
            try: server.store.process_queue_once()
            except Exception: print('Outbound worker paused after an error; inspect local queue state.',flush=True)
    threading.Thread(target=worker,daemon=True).start()
    def agent_worker():
        while not stop.wait(5):
            try:server.store.process_agent_schedule_once()
            except Exception:print('Agent scheduler encountered an error; inspect agent run history.',flush=True)
    threading.Thread(target=agent_worker,daemon=True).start()
    def chat_worker():
        while not stop.wait(1):
            try:server.store.process_chat_job_once()
            except Exception:print('AI chat worker encountered an error; inspect private job status.',flush=True)
    threading.Thread(target=chat_worker,daemon=True).start()
    def webhook_worker():
        while not stop.wait(1):
            try:server.store.process_webhook_once()
            except Exception:print('Webhook worker paused after an error; inspect delivery history.',flush=True)
    threading.Thread(target=webhook_worker,daemon=True).start()
    def customer_worker():
        while not stop.wait(1):
            try:server.store.process_customer_reply_once()
            except Exception:print('Customer assistant worker paused; inspect its run history.',flush=True)
    threading.Thread(target=customer_worker,daemon=True).start()
    def flow_worker():
        while not stop.wait(1):
            try:server.store.process_flow_wait_once()
            except Exception:print('Chatbot wait worker paused; inspect flow and conversation state.',flush=True)
    threading.Thread(target=flow_worker,daemon=True).start()
    def flow_send_worker():
        while not stop.wait(1):
            try:server.store.process_flow_send_once()
            except Exception:print('Chatbot send worker paused; inspect chatbot delivery history.',flush=True)
    threading.Thread(target=flow_send_worker,daemon=True).start()
    def no_response_worker():
        while not stop.wait(1):
            try:server.store.process_no_response_once()
            except Exception:print('No-response rule worker paused; inspect rule history.',flush=True)
    threading.Thread(target=no_response_worker,daemon=True).start()
    print('VYBE Connect local preview: http://127.0.0.1:'+str(server.server_address[1]),flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: stop.set();server.server_close()
