import http.client
import json
import hashlib
import hmac
import os
import time
import tempfile
import threading
import unittest
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import make_server


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.server=make_server(0,Path(self.tmp.name)/'http.db')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.port=self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()

    def request(self,method,path,data=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.port)
        h={'Content-Type':'application/json','Origin':'http://127.0.0.1:'+str(self.port)}
        h.update(headers or {})
        c.request(method,path,json.dumps(data).encode() if data is not None else None,h)
        r=c.getresponse(); body=r.read(); result=(r.status,dict(r.getheaders()),body);c.close();return result

    def test_all_index_scripts_and_styles_are_served(self):
        import re
        status, _, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        assets = re.findall(r'(?:src|href)="(/[^" ]+\.(?:js|css)(?:\?v=[a-zA-Z0-9-]+)?)"', body.decode())
        self.assertTrue(any(asset.startswith('/agent-directory.js?v=') for asset in assets))
        for asset in assets:
            with self.subTest(asset=asset):
                code, headers, content = self.request('GET', asset)
                self.assertEqual(code, 200)
                self.assertTrue(content)
                self.assertIn('javascript' if asset.split('?')[0].endswith('.js') else 'text/css', headers['Content-Type'])

    def test_cross_origin_setup_rejected(self):
        status,_,_=self.request('POST','/api/setup',{}, {'Origin':'https://evil.example'})
        self.assertEqual(status,403)

    def test_invalid_host_rejected(self):
        status,_,_=self.request('GET','/api/bootstrap',headers={'Host':'evil.example'})
        self.assertEqual(status,403)

    def test_setup_session_required_and_secret_files_not_served(self):
        status,_,_=self.request('GET','/api/state');self.assertEqual(status,401)
        status,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        self.assertEqual(status,200)
        cookie=headers['Set-Cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
        status,_,body=self.request('GET','/api/state',headers={'Cookie':cookie.split(';')[0]})
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['context']['workspace']['name'],'Acme')
        status,_,_=self.request('GET','/.env');self.assertEqual(status,404)

    def test_unsigned_webhook_rejected(self):
        status,_,_=self.request('POST','/webhook/unknown',{'entry':[]})
        self.assertEqual(status,403)

    def test_media_upload_private_download_and_integration_assets(self):
        status,_,_=self.request('GET','/integrations.js');self.assertEqual(status,200)
        status,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie=headers['Set-Cookie'].split(';')[0]
        def upload(extra):
            c=http.client.HTTPConnection('127.0.0.1',self.port)
            c.request('POST','/api/media-upload?name=photo.png',b'private-media',{'Origin':'http://127.0.0.1:'+str(self.port),'Content-Type':'image/png',**extra})
            r=c.getresponse();result=r.status,r.read();c.close();return result
        with patch('media_service.upload_media',return_value='12345') as provider:
            self.assertEqual(upload({})[0],401);provider.assert_not_called()
            self.assertEqual(upload({'Cookie':cookie,'Origin':'https://evil.example'})[0],403);provider.assert_not_called()
            code,body=upload({'Cookie':cookie});self.assertEqual(code,200,body);asset=json.loads(body)
        url='/api/media?id='+asset['id']
        self.assertEqual(self.request('GET',url)[0],401)
        code,headers,body=self.request('GET',url,headers={'Cookie':cookie})
        self.assertEqual(code,200);self.assertEqual(body,b'private-media');self.assertEqual(headers['Cache-Control'],'no-store')
        code,_,body=self.request('POST','/api/action',{'action':'workspace.create','data':{'name':'Other'}},{'Cookie':cookie})
        other=json.loads(body)['id']
        self.assertEqual(self.request('GET',url+'&workspace='+other,headers={'Cookie':cookie})[0],404)

    def test_shopify_unsigned_external_request_rejected(self):
        status,_,_=self.request('POST','/shopify-webhook/unknown',{'id':123},{'Origin':'https://external.example'})
        self.assertEqual(status,403)

    def test_document_upload_uses_authenticated_raw_endpoint(self):
        status,_,_=self.request('GET','/knowledge-documents.js');self.assertEqual(status,200)
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie=headers['Set-Cookie'].split(';')[0]
        c=http.client.HTTPConnection('127.0.0.1',self.port)
        c.request('POST','/api/knowledge-upload?name=returns.txt',b'Returns accepted for fourteen days.',{'Origin':'http://127.0.0.1:'+str(self.port),'Content-Type':'application/octet-stream','Cookie':cookie})
        r=c.getresponse();body=r.read();self.assertEqual(r.status,200,body);document=json.loads(body);c.close()
        self.assertEqual(document['chunks'],1)
        ctx=self.server.store.auth(cookie.split('=',1)[1]);passage=self.server.store._ai_context(ctx,{'question':'Returns?'})[1]['knowledge_passages'][0]
        url='/api/knowledge-source?document_id='+document['id']+'&chunk_id='+passage['chunk_id']
        self.assertEqual(self.request('GET',url)[0],401)
        status,_,body=self.request('GET',url,headers={'Cookie':cookie});self.assertEqual(status,200);self.assertIn('fourteen days',json.loads(body)['text'])

    def test_external_agent_signed_callback_creates_a_draft_over_http(self):
        self.assertEqual(self.request('GET','/external-agents.js')[0],200)
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        code,_,body=self.request('POST','/api/action',{'action':'external-agent.save','data':{'name':'Agent','url':'https://agents.example.test/inbound','events':['message.received'],'enabled':True}},cookie)
        self.assertEqual(code,200,body);agent=json.loads(body)
        code,_,body=self.request('GET','/api/state',headers=cookie);tenant=json.loads(body)['context']['tenant_id'];prefix='TW_WEBHOOK_'+tenant.upper()+'_'
        env={prefix+'ENABLED':'true',prefix+'ALLOWED_ORIGINS':'https://agents.example.test',prefix+agent['id'].upper()+'_SECRET':'test-only'}
        with patch.dict(os.environ,env):
            self.server.store.inbound(tenant,{'id':'incoming_http','from':'919000000001','text':{'body':'Hours?'}})
            _,_,body=self.request('GET','/api/state',headers=cookie);event=json.loads(body)['webhook_events'][0]
            payload={'event_id':event['id'],'reply_id':'http_reply_1','body':'We open at nine.'};raw=json.dumps(payload).encode();stamp=str(int(time.time()))
            signature='sha256='+hmac.new(b'test-only',stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest();path='/agent-callback/'+tenant+'/'+agent['id']
            self.assertEqual(self.request('POST',path,payload,{'Origin':'https://external.example'})[0],403)
            code,_,body=self.request('POST',path,payload,{'Origin':'https://external.example','X-TeamWave-Timestamp':stamp,'X-TeamWave-Signature':signature})
            self.assertEqual(code,200,body);self.assertEqual(json.loads(body)['status'],'draft')
        _,_,body=self.request('GET','/api/state',headers=cookie);self.assertEqual(json.loads(body)['messages'][-1]['status'],'draft')

    def test_customer_assistant_configuration_and_grounded_draft_over_http(self):
        self.assertEqual(self.request('GET','/customer-assistant.js')[0],200)
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        def action(name,data):
            code,_,body=self.request('POST','/api/action',{'action':name,'data':data},cookie)
            self.assertEqual(code,200,body);return json.loads(body)
        source=action('knowledge.save',{'title':'Hours','body':'We open at nine.','enabled':True})
        action('customer-assistant.save',{'name':'Support','instructions':'Use approved knowledge.','mode':'draft','enabled':True,'source_ids':[source['id']],'keywords':[],'daily_limit':10})
        _,_,body=self.request('GET','/api/state',headers=cookie);tenant=json.loads(body)['context']['tenant_id']
        env={'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'http-test-only','TW_AI_'+tenant.upper()+'_ALLOW_PAID':'true'}
        result=json.dumps({'reply':'We open at nine.','needs_human':False,'reason':'Hours policy.','knowledge_references':[]})
        with patch.dict(os.environ,env),patch('customer_assistant.ask_local',return_value=result) as model,patch('customer_assistant.send_text') as send:
            self.server.store.inbound(tenant,{'id':'http_customer_ai','from':'919000000001','text':{'body':'Hours?'},'timestamp':str(int(time.time()))})
            self.server.store.process_customer_reply_once();model.assert_called_once();send.assert_not_called()
            code,_,body=self.request('GET','/api/state',headers=cookie)
        self.assertEqual(code,200);state=json.loads(body)
        self.assertEqual(state['messages'][-1]['status'],'draft')
        self.assertEqual(state['messages'][-1]['body'],'We open at nine.')
        self.assertNotIn('http-test-only',body.decode())

    def test_contact_event_rule_runs_from_authenticated_contact_creation(self):
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        code,_,body=self.request('POST','/api/action',{'action':'rule.save','data':{'name':'New contact','event':'contact_created','enabled':True,'actions':[{'type':'task','value':'Review new contact'}]}},cookie);self.assertEqual(code,200,body)
        code,_,body=self.request('POST','/api/action',{'action':'contact.save','data':{'name':'Buyer','phone':'919000000001'}},cookie);self.assertEqual(code,200,body)
        _,_,body=self.request('GET','/api/state',headers=cookie);state=json.loads(body)
        self.assertEqual(len(state['tasks']),1);self.assertEqual(state['rule_executions'][0]['event'],'contact_created')

    def test_signed_inbound_media_is_retrieved_and_served_privately(self):
        self.assertEqual(self.request('GET','/received-media.js')[0],200)
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        _,_,body=self.request('GET','/api/state',headers=cookie);tenant=json.loads(body)['context']['tenant_id'];prefix='TW_META_'+tenant.upper()+'_'
        data=b'\x89PNG\r\n\x1a\n'+b'image';event={'id':'http_incoming_media','from':'919000000001','type':'image','image':{'id':'12345','mime_type':'image/png','sha256':hashlib.sha256(data).hexdigest()}}
        payload={'entry':[{'changes':[{'value':{'metadata':{'phone_number_id':'111'},'messages':[event]}}]}]};signature='sha256='+hmac.new(b'test-only',json.dumps(payload).encode(),hashlib.sha256).hexdigest()
        with patch.dict(os.environ,{prefix+'APP_SECRET':'test-only',prefix+'PHONE_ID':'111'}):
            self.assertEqual(self.request('POST','/webhook/'+tenant,payload,{'X-Hub-Signature-256':signature})[0],200)
        _,_,body=self.request('GET','/api/state',headers=cookie);received=json.loads(body)['received_media'][0]
        with patch('received_media.retrieve_media',return_value={'data':data,'mime':'image/png','filename':'received.png'}):
            code,_,body=self.request('POST','/api/action',{'action':'media.receive.download','data':{'id':received['id']}},cookie);self.assertEqual(code,200,body);asset_id=json.loads(body)['asset_id']
        self.assertEqual(self.request('GET','/api/media?id='+asset_id)[0],401)
        code,headers,body=self.request('GET','/api/media?id='+asset_id,headers=cookie);self.assertEqual(code,200);self.assertEqual(body,data);self.assertEqual(headers['Cache-Control'],'no-store')

    def test_message_analytics_uses_authenticated_workspace_and_validated_dates(self):
        self.assertEqual(self.request('GET','/analytics-report.js')[0],200)
        path='/api/analytics?from=2026-10-01&to=2026-10-03'
        self.assertEqual(self.request('GET',path)[0],401)
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        _,_,body=self.request('GET','/api/state',headers=cookie);tenant=json.loads(body)['context']['tenant_id']
        self.server.store.inbound(tenant,{'id':'report_inbound','from':'919000000001','timestamp':'1790812800','text':{'body':'PRIVATE SUPPORT MESSAGE'}})
        code,_,body=self.request('GET',path,headers=cookie);self.assertEqual(code,200);self.assertEqual(json.loads(body)['totals']['inbound'],1);self.assertNotIn('PRIVATE SUPPORT MESSAGE',body.decode())
        self.assertEqual(self.request('GET',path,headers={**cookie,'X-Workspace':'foreign'})[0],403)
        self.assertEqual(self.request('GET','/api/analytics?from=bad&to=2026-10-03',headers=cookie)[0],400)

    def test_workspace_removal_revokes_next_authenticated_state_request(self):
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        owner_cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        code,_,body=self.request('POST','/api/action',{'action':'member.add','data':{'name':'Agent','email':'agent@example.test','password':'agent-long-password','role':'agent'}},owner_cookie);self.assertEqual(code,200,body);member=json.loads(body)
        code,headers,_=self.request('POST','/api/login',{'email':'agent@example.test','password':'agent-long-password'});self.assertEqual(code,200);agent_cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        self.assertEqual(self.request('GET','/api/state',headers=agent_cookie)[0],200)
        code,_,body=self.request('POST','/api/action',{'action':'member.remove','data':{'id':member['id']}},owner_cookie);self.assertEqual(code,200,body)
        self.assertEqual(self.request('GET','/api/state',headers=agent_cookie)[0],403)

    def test_invitation_public_acceptance_requires_token_origin_and_creates_scoped_session(self):
        self.assertEqual(self.request('GET','/team-invitations.js')[0],200)
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        payload={'action':'invite.create','data':{'email':'new@example.test','role':'agent','hours':24}}
        self.assertEqual(self.request('POST','/api/action',payload)[0],401)
        code,_,body=self.request('POST','/api/action',payload,cookie);self.assertEqual(code,200,body);invite=json.loads(body)
        self.assertEqual(self.request('POST','/api/invitations/inspect',{'token':invite['token']},{'Origin':'https://evil.example'})[0],403)
        code,_,body=self.request('POST','/api/invitations/inspect',{'token':invite['token']});self.assertEqual(code,200,body);self.assertNotIn('token_hash',body.decode())
        acceptance={'token':invite['token'],'name':'New agent','password':'new-agent-long-password'}
        code,headers,body=self.request('POST','/api/invitations/accept',acceptance);self.assertEqual(code,200,body);self.assertIn('HttpOnly',headers['Set-Cookie'])
        code,_,body=self.request('GET','/api/state',headers={'Cookie':headers['Set-Cookie'].split(';')[0]});state=json.loads(body)
        self.assertEqual(code,200);self.assertEqual(state['context']['role'],'agent');self.assertEqual(state['invitations'],[]);self.assertNotIn(invite['token'],body.decode())
        self.assertEqual(self.request('POST','/api/invitations/accept',acceptance)[0],400)

    def test_rule_actions_persist_and_execute_over_authenticated_http(self):
        self.assertEqual(self.request('GET','/rule-actions.js')[0],200)
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        code,_,body=self.request('POST','/api/action',{'action':'rule.save','data':{'name':'Support','keyword':'help','enabled':True,'actions':[{'type':'tag','value':'Support'},{'type':'task','value':'Review support'}],'priority':10}},cookie)
        self.assertEqual(code,200,body)
        _,_,body=self.request('GET','/api/state',headers=cookie);tenant=json.loads(body)['context']['tenant_id']
        self.server.store.inbound(tenant,{'id':'http_rule_action','from':'919000000001','text':{'body':'help'}})
        code,_,body=self.request('GET','/api/state',headers=cookie);state=json.loads(body)
        self.assertEqual(code,200);self.assertIn('Support',state['contacts'][0]['tags']);self.assertEqual(state['tasks'][0]['title'],'Review support')

    def test_website_index_and_snapshot_preview_over_authenticated_http(self):
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        _,_,body=self.request('GET','/api/state',headers=cookie);tenant=json.loads(body)['context']['tenant_id']
        payload={'action':'knowledge.website.add','data':{'url':'https://example.test/returns','title':'Returns'}}
        with patch.dict(os.environ,{'TW_KNOWLEDGE_WEB_'+tenant.upper()+'_ALLOWED_ORIGINS':'https://example.test'}),patch('website_knowledge.fetch_page',return_value=('text/plain',b'Returns fourteen days.')) as fetch:
            self.assertEqual(self.request('POST','/api/action',payload)[0],401);fetch.assert_not_called()
            code,_,body=self.request('POST','/api/action',payload,cookie);self.assertEqual(code,200,body);source=json.loads(body)
        code,_,body=self.request('POST','/api/action',{'action':'knowledge.website.preview','data':{'id':source['id']}},cookie)
        self.assertEqual(code,200);self.assertIn('fourteen',json.loads(body)['text']);self.assertFalse(source['enabled'])

    def test_verified_order_links_persist_over_authenticated_http(self):
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        _,_,body=self.request('GET','/api/state',headers=cookie);tenant=json.loads(body)['context']['tenant_id']
        _,_,body=self.request('POST','/api/action',{'action':'contact.save','data':{'name':'Buyer','phone':'919000000001'}},cookie);contact=json.loads(body)
        with self.server.store.db() as db:
            order=self.server.store._put(db,tenant,'shopifyorder',{'provider_id':'gid://shopify/Order/1','name':'#1001','shop':'example.myshopify.com','source':'shopify_api','synced':int(time.time())})
        payload={'action':'shopify.order.link','data':{'order_id':order['id'],'contact_id':contact['id'],'ownership_confirmed':True}}
        self.assertEqual(self.request('POST','/api/action',payload)[0],401)
        with patch.dict(os.environ,{'TW_SHOPIFY_'+tenant.upper()+'_SHOP':'example.myshopify.com'}):
            code,_,body=self.request('POST','/api/action',payload,cookie);self.assertEqual(code,200,body);link=json.loads(body)
            _,_,body=self.request('GET','/api/state',headers=cookie);self.assertEqual(json.loads(body)['commerce']['order_links'][0]['id'],link['id'])
            code,_,body=self.request('POST','/api/action',{'action':'shopify.order.unlink','data':{'id':link['id']}},cookie);self.assertEqual(code,200,body)

    def test_crm_assets_and_authenticated_persistence_over_http(self):
        for asset in ['/business.js','/business.css']:
            status,_,body=self.request('GET',asset);self.assertEqual(status,200);self.assertTrue(body)
        status,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        def action(name,data):
            status,_,body=self.request('POST','/api/action',{'action':name,'data':data},cookie)
            self.assertEqual(status,200,body);return json.loads(body)
        contact=action('contact.save',{'name':'Buyer','phone':'919000000001'})
        deal=action('deal.save',{'title':'Setup','contact_id':contact['id'],'amount_minor':150000,'currency':'INR'})
        task=action('task.save',{'title':'Prepare proposal','deal_id':deal['id']})
        action('chat.takeover',{'id':contact['id']})
        status,_,body=self.request('GET','/api/state',headers=cookie)
        self.assertEqual(status,200);state=json.loads(body)
        self.assertEqual(state['deals'][0]['id'],deal['id']);self.assertEqual(state['tasks'][0]['id'],task['id'])
        self.assertTrue(state['contacts'][0]['automation_hold']);self.assertEqual(state['queue'],[])


    def test_password_change_is_authenticated_same_origin_and_revokes_session(self):
        payload={'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'}
        status,headers,_=self.request('POST','/api/setup',payload);self.assertEqual(status,200);cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        change={'current_password':payload['password'],'new_password':'a-new-long-password'}
        self.assertEqual(self.request('POST','/api/account/password',change)[0],401)
        self.assertEqual(self.request('POST','/api/account/password',change,dict(cookie,Origin='https://evil.example'))[0],403)
        status,headers,_=self.request('POST','/api/account/password',change,cookie);self.assertEqual(status,200);self.assertIn('Max-Age=0',headers['Set-Cookie'])
        self.assertEqual(self.request('GET','/api/state',headers=cookie)[0],401)
        self.assertEqual(self.request('POST','/api/login',{'email':payload['email'],'password':payload['password']})[0],401)
        self.assertEqual(self.request('POST','/api/login',{'email':payload['email'],'password':change['new_password']})[0],200)


    def test_mfa_http_lifecycle_and_invitation_safe_login_boundary(self):
        from account_mfa import totp
        password='long-enough-password'
        status,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':password})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        status,_,_=self.request('GET','/api/account/mfa');self.assertEqual(status,401)
        status,_,_=self.request('POST','/api/account/mfa/begin',{'current_password':password});self.assertEqual(status,401)
        status,_,_=self.request('POST','/api/account/mfa/begin',{'current_password':password},{**cookie,'Origin':'https://other.test'});self.assertEqual(status,403)
        status,_,body=self.request('POST','/api/account/mfa/begin',{'current_password':password},cookie);self.assertEqual(status,200)
        secret=json.loads(body)['secret']
        status,headers,body=self.request('POST','/api/account/mfa/confirm',{'current_password':password,'code':totp(secret,int(time.time()))},cookie)
        self.assertEqual(status,200);self.assertIn('Max-Age=0',headers['Set-Cookie']);codes=json.loads(body)['recovery_codes']
        status,_,_=self.request('GET','/api/state',headers=cookie);self.assertEqual(status,401)
        status,headers,_=self.request('POST','/api/login',{'email':'owner@example.test','password':password});self.assertEqual(status,401);self.assertNotIn('Set-Cookie',headers)
        status,headers,_=self.request('POST','/api/login',{'email':'owner@example.test','password':password,'code':codes[0]});self.assertEqual(status,200)
        fresh={'Cookie':headers['Set-Cookie'].split(';')[0]}
        status,_,body=self.request('GET','/api/account/mfa',headers=fresh);self.assertEqual(json.loads(body),{'enabled':True,'recovery_remaining':9})
        status,_,body=self.request('GET','/api/state',headers=fresh);public=json.loads(body);self.assertNotIn('_session_hash',public['context']);self.assertNotIn(secret,body.decode())
        status,_,_=self.request('POST','/api/account/mfa/disable',{'current_password':password,'code':codes[1]},fresh);self.assertEqual(status,200)
        status,_,_=self.request('GET','/api/state',headers=fresh);self.assertEqual(status,401)
        status,_,_=self.request('POST','/api/login',{'email':'owner@example.test','password':password});self.assertEqual(status,200)


    def test_flow_draft_publish_http_keeps_active_configuration_isolated(self):
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        def action(name,data):return self.request('POST','/api/action',{'action':name,'data':data},cookie)
        status,_,body=action('flow.draft.save',{'name':'Help','keyword':'help','reply':'Hello','enabled':True})
        self.assertEqual(status,200);draft=json.loads(body);self.assertFalse(draft['enabled']);self.assertEqual(draft['draft']['revision'],1)
        status,_,body=action('flow.publish',{'id':draft['id'],'base_version':0,'draft_revision':1});self.assertEqual(status,200);self.assertTrue(json.loads(body)['enabled'])
        status,_,body=action('flow.draft.save',{'id':draft['id'],'base_version':1,'draft_revision':0,'name':'Changed','keyword':'new','reply':'New reply','enabled':False});self.assertEqual(status,200)
        status,_,body=self.request('GET','/api/state',headers=cookie);self.assertEqual(status,200);flow=json.loads(body)['flows'][0]
        self.assertEqual(flow['keyword'],'help');self.assertTrue(flow['enabled']);self.assertEqual(flow['draft']['keyword'],'new');self.assertEqual(flow['published_versions'][0]['version'],1)
        status,_,_=action('flow.publish',{'id':draft['id'],'base_version':0,'draft_revision':1});self.assertEqual(status,409)


    def test_team_routing_and_personal_availability_http(self):
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
        owner={'Cookie':headers['Set-Cookie'].split(';')[0]}
        def action(name,data,who=owner):return self.request('POST','/api/action',{'action':name,'data':data},who)
        _,_,body=action('member.add',{'name':'Agent','email':'agent@example.test','password':'long-enough-password','role':'agent'});agent_id=json.loads(body)['id']
        _,_,body=action('team.save',{'name':'Support','members':[agent_id],'enabled':True});team=json.loads(body)
        _,headers,_=self.request('POST','/api/login',{'email':'agent@example.test','password':'long-enough-password'});agent={'Cookie':headers['Set-Cookie'].split(';')[0]}
        self.assertEqual(action('team.save',{'name':'Forbidden','members':[],'enabled':True},agent)[0],403)
        self.assertEqual(action('availability.set',{'status':'available','minutes':60},agent)[0],200)
        _,_,body=action('contact.save',{'name':'Customer','phone':'919000000001'});contact=json.loads(body)
        status,_,body=action('chat.route',{'id':contact['id'],'team_id':team['id'],'respect_availability':True});self.assertEqual(status,200);self.assertEqual(json.loads(body)['assignee'],agent_id)
        status,_,body=self.request('GET','/api/state',headers=owner);self.assertEqual(status,200);self.assertEqual(len(json.loads(body)['team_operations']['assignments']),1)
        self.assertEqual(self.request('GET','/team-operations.js')[0],200)

    def test_comment_mentions_are_private_and_recipient_scoped_http(self):
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'});owner={'Cookie':headers['Set-Cookie'].split(';')[0]}
        def action(name,data,who=owner):return self.request('POST','/api/action',{'action':name,'data':data},who)
        _,_,body=action('member.add',{'name':'Agent','email':'agent@example.test','password':'long-enough-password','role':'agent'});agent_id=json.loads(body)['id']
        _,_,body=action('contact.save',{'name':'Customer','phone':'919000000001'});contact=json.loads(body)
        status,_,body=action('message.send',{'contact_id':contact['id'],'body':'Private review','note':True,'mentions':[agent_id]});self.assertEqual(status,200);self.assertEqual(json.loads(body)['direction'],'note')
        _,headers,_=self.request('POST','/api/login',{'email':'agent@example.test','password':'long-enough-password'});agent={'Cookie':headers['Set-Cookie'].split(';')[0]}
        _,_,body=self.request('GET','/api/state',headers=agent);notice=json.loads(body)['mention_notifications'][0]
        self.assertEqual(action('notification.read',{'id':notice['id']})[0],403)
        self.assertEqual(action('notification.read',{'id':notice['id']},agent)[0],200)
        with self.server.store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM outbound').fetchone()[0],0)

    def test_malformed_action_names_are_client_errors(self):
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'});cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        for action in [None,False,[],{},42]:self.assertEqual(self.request('POST','/api/action',{'action':action,'data':{}},cookie)[0],400)


    def test_email_recovery_http_generic_response_origin_and_reset_session_revocation(self):
        from password_recovery import token_for
        from test_password_recovery import ENV
        with patch.dict(os.environ,ENV),patch('password_recovery.send_recovery') as transport:
            payload={'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'}
            _,headers,_=self.request('POST','/api/setup',payload);cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
            self.assertEqual(self.request('POST','/api/password/request',{'email':payload['email']},{'Origin':'https://attacker.test'})[0],403)
            status,_,known=self.request('POST','/api/password/request',{'email':payload['email']});self.assertEqual(status,200)
            status,_,unknown=self.request('POST','/api/password/request',{'email':'missing@example.test'});self.assertEqual(status,200);self.assertEqual(known,unknown);transport.assert_not_called()
            with self.server.store.db() as db:
                row=db.execute('SELECT * FROM password_resets').fetchone();user=db.execute('SELECT * FROM users').fetchone();token=token_for(row['id'],user)
            self.assertNotIn(token,known.decode())
            self.assertEqual(self.request('POST','/api/password/reset',{'token':token,'new_password':'new-long-password'},{'Origin':'https://attacker.test'})[0],403)
            status,headers,body=self.request('POST','/api/password/reset',{'token':token,'new_password':'new-long-password'});self.assertEqual(status,200);self.assertIn('Max-Age=0',headers['Set-Cookie']);self.assertNotIn('token',json.loads(body))
            self.assertEqual(self.request('GET','/api/state',headers=cookie)[0],401)
            self.assertEqual(self.request('POST','/api/password/reset',{'token':token,'new_password':'other-long-password'})[0],400)
            self.assertEqual(self.request('POST','/api/login',{'email':payload['email'],'password':'new-long-password'})[0],200)
            self.assertEqual(self.request('GET','/account-recovery.js')[0],200)
            _,_,body=self.request('GET','/api/bootstrap');self.assertTrue(json.loads(body)['password_recovery_available']);self.assertNotIn(ENV['TW_RECOVERY_SECRET'],body.decode())

    def test_password_recovery_requests_are_rate_limited_even_when_mail_disabled(self):
        with patch.dict(os.environ,{'TW_RECOVERY_ENABLED':'false'}):
            for _ in range(12):self.assertEqual(self.request('POST','/api/password/request',{'email':'any@example.test'})[0],200)
            self.assertEqual(self.request('POST','/api/password/request',{'email':'any@example.test'})[0],429)


    def test_feedback_is_authenticated_persistent_and_vybe_assets_are_served(self):
        self.assertEqual(self.request('POST','/api/action',{'action':'feedback.save','data':{'rating':5}})[0],401)
        _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'});cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
        status,_,body=self.request('POST','/api/action',{'action':'feedback.save','data':{'rating':5,'body':'Widget feedback','category':'feedback','page':'external-agents'}},cookie);self.assertEqual(status,200);report=json.loads(body)
        _,_,body=self.request('GET','/api/state',headers=cookie);self.assertEqual(json.loads(body)['product_feedback'][0]['id'],report['id'])
        for path in ['/help-widget.js','/help-widget.css','/vybe-theme.css']:self.assertEqual(self.request('GET',path)[0],200)
        _,_,body=self.request('GET','/');self.assertIn('VYBE Connect',body.decode());self.assertIn('/help-widget.js',body.decode())

    def test_customer_whatsapp_begin_requires_session_and_same_origin(self):
        env={'TW_META_PLATFORM_ENABLED':'true','TW_META_PLATFORM_APP_ID':'123','TW_META_PLATFORM_CONFIG_ID':'456','TW_META_PLATFORM_APP_SECRET':'a'*32,'TW_META_PLATFORM_VERIFY_TOKEN':'v'*40,'TW_META_PLATFORM_VERSION':'v25.0','TW_PUBLIC_ORIGIN':'https://example.test'}
        with patch.dict(os.environ,env):
            payload={'action':'whatsapp.begin','data':{}}
            self.assertEqual(self.request('POST','/api/action',payload)[0],401)
            _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
            cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
            self.assertEqual(self.request('POST','/api/action',payload,dict(cookie,Origin='https://wrong.test'))[0],403)
            status,_,body=self.request('POST','/api/action',payload,cookie)
            self.assertEqual(status,200);self.assertEqual(json.loads(body)['config_id'],'456');self.assertNotIn('APP_SECRET',body.decode())
            self.assertEqual(self.request('GET','/meta-credentials/owner.json')[0],404)

    def test_customer_webhook_verification_can_use_platform_token(self):
        from urllib.parse import urlencode
        env={'TW_META_PLATFORM_ENABLED':'true','TW_META_PLATFORM_APP_ID':'123','TW_META_PLATFORM_CONFIG_ID':'456','TW_META_PLATFORM_APP_SECRET':'a'*32,'TW_META_PLATFORM_VERIFY_TOKEN':'v'*40,'TW_META_PLATFORM_VERSION':'v25.0','TW_PUBLIC_ORIGIN':'https://example.test'}
        with patch.dict(os.environ,env):
            query=urlencode({'hub.mode':'subscribe','hub.verify_token':'v'*40,'hub.challenge':'challenge'})
            code,_,body=self.request('GET','/webhook/0123456789abcdef?'+query)
            self.assertEqual(code,200);self.assertEqual(body,b'challenge')
            self.assertEqual(self.request('GET','/webhook/0123456789abcdef?'+query.replace('v'*40,'wrong'))[0],403)
            _,headers,_=self.request('GET','/')
            self.assertIn('https://connect.facebook.net',headers['Content-Security-Policy'])

    def test_ai_connection_is_authenticated_origin_checked_and_never_echoes_key(self):
        env={'TW_DATA_DIR':self.tmp.name,'TW_AI_ENABLED':'true'}
        data={'action':'ai.connection.save','data':{'key':'sk-'+('x'*40),'model':'test-model','enabled':False}}
        with patch.dict(os.environ,env):
            self.assertEqual(self.request('POST','/api/action',data)[0],401)
            _,headers,_=self.request('POST','/api/setup',{'name':'Owner','business':'Acme','email':'owner@example.test','password':'long-enough-password'})
            cookie={'Cookie':headers['Set-Cookie'].split(';')[0]}
            self.assertEqual(self.request('POST','/api/action',data,dict(cookie,Origin='https://wrong.test'))[0],403)
            status,_,body=self.request('POST','/api/action',data,cookie)
            self.assertEqual(status,200);self.assertFalse(json.loads(body)['enabled']);self.assertNotIn(data['data']['key'],body.decode())
            _,_,body=self.request('GET','/api/state',headers=cookie);self.assertNotIn(data['data']['key'],body.decode())
            self.assertEqual(self.request('GET','/ai-credentials/key.json')[0],404)

if __name__=='__main__': unittest.main()
