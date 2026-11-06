"""Explicitly paid, budgeted acceptance against synthetic temporary workspace data.

Never runs in unittest discovery. No Meta, customer data or production database.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
import urllib.request
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class Budget:
    def __init__(self,report,limit):
        self.path=report;self.limit=limit;self.native=urllib.request.urlopen
        if report.exists():raise ValueError('Use a fresh report path; this prevents accidental paid reruns.')
        self.data={'limit_usd':limit,'spent_upper_usd':0,'reserved_usd':0,'calls':[],'checks':[],'network':'OpenAI Responses only; synthetic temporary Store'}
        self.pending={};self.save()
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(self.data,indent=2),encoding='utf-8')
    def open(self,request,*args,**kwargs):
        u=urlsplit(request.full_url)
        if u.scheme!='https' or u.netloc!='api.openai.com' or not u.path.startswith('/v1/responses'):raise ValueError('Non-OpenAI network request blocked by acceptance harness.')
        record=None
        if request.get_method()=='POST' and u.path=='/v1/responses':
            payload=json.loads(request.data)
            if payload.get('model')!='gpt-6-luna' or payload.get('tools'):raise ValueError('Unapproved model/tools blocked.')
            payload['max_output_tokens']=1024
            raw=json.dumps(payload).encode();bound=(len(raw)+1024)/1e6+1024*5/1e6
            if len(self.data['calls'])>=20 or self.data['spent_upper_usd']+self.data['reserved_usd']+bound>self.limit:raise ValueError('Paid acceptance budget exhausted before network submission.')
            record={'index':len(self.data['calls'])+1,'reserved_upper_usd':bound,'state':'submitted_unknown'}
            self.data['calls'].append(record);self.data['reserved_usd']+=bound;self.save()
            request.data=raw
        with self.native(request,*args,**kwargs) as response:raw=response.read()
        result=json.loads(raw)
        if record:self.pending[result.get('id')]=record
        else:record=self.pending.get(result.get('id'))
        if record:
            record['state']=result.get('status','unknown')
            usage=result.get('usage')
            if isinstance(usage,dict) and not record.get('usage'):
                # $1/M input + $5/M output is deliberately above current Luna
                # standard/fast/cache rates. Unknown submissions keep reservation.
                upper=(usage['input_tokens']+5*usage['output_tokens'])/1e6
                if upper>record['reserved_upper_usd']:raise ValueError('Provider token usage exceeded preflight bound; stop all testing.')
                record['usage']=usage;record['cost_upper_usd']=upper
                self.data['reserved_usd']-=record['reserved_upper_usd'];self.data['spent_upper_usd']+=upper
            self.save()
        return io.BytesIO(raw)
    def check(self,name,run):
        try:
            detail=run();self.data['checks'].append({'name':name,'passed':True,'detail':detail})
            print('PASS '+name,flush=True)
        except Exception as error:
            self.data['checks'].append({'name':name,'passed':False,'error':str(error)[:350]})
            print('FAIL '+name+': '+str(error)[:180],flush=True)
        self.save()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--allow-paid',action='store_true');ap.add_argument('--max-cost-usd',type=float,default=0);ap.add_argument('--key-file',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);args=ap.parse_args()
    if not args.allow_paid or not 0<args.max_cost_usd<=0.4:ap.error('Explicit --allow-paid and a cap of at most US$0.40 are required.')
    match=re.search(r'sk-[A-Za-z0-9_-]{20,}',args.key_file.read_text(encoding='utf-8-sig'))
    if not match:raise ValueError('No key found in the private file.')
    budget=Budget(args.report,args.max_cost_usd)
    from store import Store
    script="const fs=require('fs'),vm=require('vm');const c=vm.createContext({setInterval(){}});vm.runInContext(fs.readFileSync('static/assistant.js','utf8'),c);process.stdout.write(vm.runInContext('JSON.stringify(AGENT_PRESETS)',c));"
    presets=json.loads(subprocess.check_output(['node','-e',script],cwd=ROOT,text=True))
    assert len(presets)==12
    with tempfile.TemporaryDirectory(prefix='vybe-real-ai-acceptance-') as folder,patch.dict(os.environ,{'TW_SANDBOX':'false','TW_PLATFORM_AI_MANAGED':'false','TW_BILLING_ENFORCE':'false','TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':match.group(0),'TW_PLATFORM_OWNER_EMAIL':'qa@example.test','TW_META_ALLOW_LIVE':'false','TW_AUTO_REPLY_ENABLED':'false'}):
        s=Store(Path(folder)/'acceptance.db');ctx=s.auth(s.setup('QA Owner','qa@example.test',secrets.token_urlsafe(24),'Synthetic QA Shop')['token']);tenant=ctx['tenant_id']
        os.environ['TW_AI_'+tenant.upper()+'_ALLOW_PAID']='true'
        contact=s.action(ctx,'contact.save',{'name':'Synthetic buyer','phone':'12025550123','optin':False})
        s.inbound(tenant,{'id':'synthetic-inbound-qa','from':contact['phone'],'text':{'body':'I want to buy the Starter plan. What are your opening hours? Please help before Friday.'},'timestamp':str(int(time.time()))})
        knowledge=s.action(ctx,'knowledge.save',{'title':'Approved QA hours','body':'Synthetic QA Shop opens at 9 AM and closes at 5 PM, Monday to Friday. No refund policy has been approved.','enabled':True})
        with patch('urllib.request.urlopen',side_effect=budget.open):
            for name,instructions in presets:
                def run(name=name,instructions=instructions):
                    agent=s.action(ctx,'aiagent.save',{'name':name,'instructions':instructions})
                    result=s.action(ctx,'ai.run',{'agent_id':agent['id']})
                    assert result['status']=='completed' and result['summary'].strip()
                    assert not s.state(ctx)['queue']
                    return {'status':result['status'],'findings':result['finding_count'],'summary':result['summary'][:240]}
                budget.check('Preset: '+name,run)
            def queued(purpose,question):
                job=s.action(ctx,'ai.chat.start',{'question':question,'purpose':purpose})
                deadline=time.time()+90
                while time.time()<deadline:
                    s.process_chat_job_once()
                    with s.db() as db:current=s._get(db,tenant,'aijob',job['id'])
                    if current['status'] in {'completed','failed','unknown','cancelled','cancel_unconfirmed'}:break
                    time.sleep(1)
                assert current['status']=='completed',current.get('error') or current['status']
                state=s.state(ctx);chat=next(c for c in state['aichats'] if c['id']==job['chat_id']);answer=chat['messages'][-1]
                assert answer['role']=='assistant' and answer['content'].strip()
                return {'status':current['status'],'answer':answer['content'][:240],'proposal':bool(answer.get('agent_draft'))}
            budget.check('Queued AI Ask with grounded citations',lambda:queued('chat','What are our approved opening hours? Answer briefly and cite the supplied knowledge.'))
            budget.check('AI agent builder proposal',lambda:queued('agent_builder','Create a manual agent that reviews unanswered chats. Do not schedule or send anything.'))
            def customer_reply():
                s.action(ctx,'customer-assistant.save',{'name':'QA Support','instructions':'Answer only from approved business knowledge. Hand off unknown policies.','enabled':True,'mode':'draft','keywords':[],'source_ids':[knowledge['id']],'daily_limit':2})
                s.inbound(tenant,{'id':'synthetic-customer-support-qa','from':contact['phone'],'text':{'body':'What time do you open and close?'},'timestamp':str(int(time.time()))})
                s.process_customer_reply_once();state=s.state(ctx);job=state['customer_reply_jobs'][-1]
                assert job['status']=='completed',job
                answer=next(m for m in state['messages'] if m['id']==job['message_id'])
                assert answer['status']=='draft' and '9' in answer['body'] and '5' in answer['body']
                assert not state['queue']
                return {'status':job['status'],'message_status':answer['status'],'reply':answer['body']}
            budget.check('Customer support grounded reply draft',customer_reply)
        state=s.state(ctx);assert not state['queue'];assert all(m['status']=='draft' for m in state['messages'] if m['direction']=='out')
        budget.data['no_meta_requests']=True;budget.data['no_outbound_queue']=True;budget.save()
    failures=sum(not x['passed'] for x in budget.data['checks'])
    print(json.dumps({'checks':len(budget.data['checks']),'failed':failures,'model_submissions':len(budget.data['calls']),'spent_upper_usd':budget.data['spent_upper_usd'],'reserved_unknown_usd':budget.data['reserved_usd']}),flush=True)
    return 1 if failures else 0

if __name__=='__main__':raise SystemExit(main())
