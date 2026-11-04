import hashlib
import hmac
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from provider_transport import RemoteError
import payment_services
import whatsapp_calls


class BusinessServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'test.db')
        self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-test-password','Business')['token']);self.t=self.ctx['tenant_id']
        self.c=self.act('contact.save',name='Customer',phone='+919000000001')
        product=self.act('commerce.product.save',name='Product',sku='SKU',price='10.00',currency='INR',stock=5,enabled=True)
        self.o=self.act('commerce.order.save',contact_id=self.c['id'],items=[{'product_id':product['id'],'quantity':1}])
        self.o=self.act('commerce.order.transition',id=self.o['id'],version=self.o['version'],status='confirmed')
        env={}
        for scope,prefix in [('payments','TW_PAYMENTS_'+self.t.upper()+'_'),('billing','TW_BILLING_')]:
            env.update({prefix+'KEY_ID':'rzp_test_fixture',prefix+'KEY_SECRET':'private-test-secret',prefix+'WEBHOOK_SECRET':'webhook-test-secret',prefix+'ACCOUNT_ID':'acc_fixture',prefix+'ENABLED':'true'})
        prefix='TW_SHIPPING_'+self.t.upper()+'_';env.update({prefix+'TOKEN':'private-shipping-token',prefix+'ENABLED':'true',prefix+'PICKUP_LOCATION':'Office',prefix+'PICKUP_POSTCODE':'560001'})
        prefix='TW_META_'+self.t.upper()+'_';env.update({prefix+'TOKEN':'meta-fixture',prefix+'PHONE_ID':'123',prefix+'VERSION':'v23.0','TW_CALLING_'+self.t.upper()+'_ENABLED':'true'})
        self.env=patch.dict(os.environ,env);self.env.start()

    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def act(self,operation,**data):return self.s.action(self.ctx,operation,data)
    def link(self):
        def create(t,scope,method,edge,payload):
            return dict(id='plink_fixture',short_url='https://rzp.io/fixture',status='created',**payload)
        with patch('payment_services.razorpay',side_effect=create) as remote:
            job=self.act('payments.create-link',order_id=self.o['id'])
        return job
    def event(self,job,event_id='evt1',amount=1000,account='acc_fixture',stamp=None):
        raw=json.dumps({'account_id':account,'created_at':stamp or int(time.time()),'event':'payment_link.paid','payload':{'payment_link':{'entity':{'id':'plink_fixture','reference_id':job['id'],'amount':amount,'currency':'INR','amount_paid':amount,'status':'paid'}}}}).encode()
        headers={'X-Razorpay-Signature':hmac.new(b'webhook-test-secret',raw,hashlib.sha256).hexdigest(),'X-Razorpay-Event-Id':event_id}
        return raw,headers

    def test_link_is_one_shot_and_does_not_notify_customer(self):
        calls=[]
        def create(t,scope,method,edge,payload):
            calls.append(payload);return dict(id='plink_fixture',short_url='https://rzp.io/fixture',status='created',**payload)
        with patch('payment_services.razorpay',side_effect=create):
            first=self.act('payments.create-link',order_id=self.o['id']);second=self.act('payments.create-link',order_id=self.o['id'])
        self.assertEqual(first['id'],second['id']);self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['amount'],1000);self.assertEqual(calls[0]['notify'],{'sms':False,'email':False})
        self.assertNotIn('payload',first)

    def test_uncertain_write_cannot_be_retried(self):
        with patch('payment_services.razorpay',side_effect=RemoteError('uncertain')) as remote:
            first=self.act('payments.create-link',order_id=self.o['id']);self.act('payments.create-link',order_id=self.o['id'])
        self.assertEqual(first['status'],'unknown');self.assertEqual(remote.call_count,1)

    def test_signed_paid_event_is_scoped_idempotent_and_does_not_regress(self):
        job=self.link();raw,headers=self.event(job)
        payment_services.webhook(self.s,self.t,'payments',raw,headers)
        self.assertTrue(payment_services.webhook(self.s,self.t,'payments',raw,headers)['duplicate'])
        state=self.s.state(self.ctx)['services'];self.assertEqual(state['jobs'][0]['status'],'paid')
        raw,headers=self.event(job,'evt2',account='acc_other')
        with self.assertRaises(Exception):payment_services.webhook(self.s,self.t,'payments',raw,headers)
        raw,headers=self.event(job,'evt3',amount=999)
        with self.assertRaises(Exception):payment_services.webhook(self.s,self.t,'payments',raw,headers)
        raw,headers=self.event(job,'evt4');headers['X-Razorpay-Signature']='bad'
        with self.assertRaises(Exception):payment_services.webhook(self.s,self.t,'payments',raw,headers)

    def test_checkout_redirect_cannot_mark_paid(self):
        job=self.link()
        self.assertNotEqual(job['status'],'paid')
        with self.assertRaises(Problem):self.act('payments.paid',id=job['id'],status='paid')

    def test_disable_and_role_gates_prevent_network(self):
        with patch.dict(os.environ,{'TW_PAYMENTS_'+self.t.upper()+'_ENABLED':'false'}),patch('payment_services.razorpay') as remote:
            with self.assertRaises(Problem):self.act('payments.create-link',order_id=self.o['id'])
            remote.assert_not_called()
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,role='agent'),'payments.create-link',{'order_id':self.o['id']})

    def test_subscription_price_and_access_follow_provider_evidence(self):
        plan={'starter':{'plan_id':'plan_fixture','name':'Starter','amount_minor':50000,'currency':'INR','interval':'monthly','cycles':12}}
        def remote(t,scope,method,edge,payload=None):
            if edge.startswith('plans/'):return {'item':{'amount':50000,'currency':'INR'},'period':'monthly','interval':1}
            return dict(payload,id='sub_fixture',short_url='https://rzp.io/subscription',status='created')
        with patch.dict(os.environ,{'TW_BILLING_PLANS':json.dumps(plan)}),patch('payment_services.razorpay',side_effect=remote):
            job=self.act('billing.subscribe',plan='starter');self.assertFalse(self.s.state(self.ctx)['services']['subscription_active'])
            resource={'id':'sub_fixture','plan_id':'plan_fixture','status':'active','current_end':int(time.time())+3600,'notes':{'workspace_id':self.t,'operation_id':job['id']}}
            raw=json.dumps({'account_id':'acc_fixture','created_at':int(time.time()),'payload':{'subscription':{'entity':resource}}}).encode()
            headers={'X-Razorpay-Event-Id':'evt_sub','X-Razorpay-Signature':hmac.new(b'webhook-test-secret',raw,hashlib.sha256).hexdigest()}
            payment_services.webhook(self.s,self.t,'billing',raw,headers)
            self.assertTrue(self.s.state(self.ctx)['services']['subscription_active'])
        plan['starter']['amount_minor']=123
        with patch.dict(os.environ,{'TW_BILLING_PLANS':json.dumps(plan)}),patch('payment_services.razorpay',side_effect=remote):
            with self.assertRaises(Problem):self.act('billing.subscribe',plan='starter')

    def test_shipping_payload_snapshot_and_scoped_quote(self):
        details={'order_id':self.o['id'],'billing_customer_name':'Customer','billing_address':'Example street','billing_city':'Bengaluru','billing_pincode':'560002','billing_state':'Karnataka','billing_email':'customer@example.test','length':'10','breadth':'10','height':'10','weight':'0.5','payment_method':'COD'}
        captured=[]
        def remote(t,method,edge,payload=None,query=None):
            captured.append((edge,payload,query))
            if edge=='orders/create/adhoc':return {'order_id':1,'shipment_id':2,'status':'NEW'}
            if edge=='courier/serviceability':return {'data':{'available_courier_companies':[{'courier_company_id':3,'courier_name':'Courier','rate':50}]}}
            if edge=='courier/assign/awb':return {'awb_assign_status':1,'response':{'data':{'awb_code':'AWB123'}}}
        with patch('shipping_services.shiprocket',side_effect=remote):
            job=self.act('shipping.create',**details);self.assertEqual(job['status'],'created')
            self.assertNotIn('payload',job);self.assertEqual(captured[0][1]['sub_total'],10)
            with self.assertRaises(Problem):self.act('shipping.assign-awb',order_id=self.o['id'],courier_id=99)
            self.act('shipping.rates',order_id=self.o['id'])
            result=self.act('shipping.assign-awb',order_id=self.o['id'],courier_id=3);self.assertEqual(result['result']['awb_code'],'AWB123')

    def test_prepaid_shipping_requires_verified_payment(self):
        with patch('shipping_services.shiprocket') as remote:
            with self.assertRaises(Problem):self.act('shipping.create',order_id=self.o['id'],payment_method='Prepaid')
            remote.assert_not_called()

    def test_call_claim_single_operator_and_no_sdp_in_state(self):
        whatsapp_calls.ingest(self.s,self.t,[{'id':'call_1','event':'connect','from':'12025550146','session':{'sdp_type':'offer','sdp':'v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111'}}])
        call=self.s.state(self.ctx)['calling']['calls'][0];self.assertNotIn('offer',call)
        claimed=self.act('calls.claim',id=call['id']);self.assertIn('offer',claimed)
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,user=dict(self.ctx['user'],id='other')),'calls.claim',{'id':call['id']})
        with patch('whatsapp_calls.request',return_value={'success':True}) as remote:
            self.act('calls.accept',id=call['id'],sdp='v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111')
            with self.assertRaises(Problem):self.act('calls.accept',id=call['id'],sdp='v=0')
            self.assertEqual(remote.call_count,1)
        whatsapp_calls.ingest(self.s,self.t,[{'id':'call_1','event':'terminate'}]);self.assertEqual(self.s.state(self.ctx)['calling']['calls'][0]['status'],'ended')

    def test_provider_checks_default_off_and_secret_free(self):
        with patch.dict(os.environ,{'TW_PROVIDER_READS':'false'}),patch('provider_checks.request') as remote:
            with self.assertRaises(Problem):self.act('providers.check',provider='payments')
            remote.assert_not_called()
        with patch.dict(os.environ,{'TW_PROVIDER_READS':'true'}),patch('provider_checks.request',return_value={'entity':'collection'}):
            self.act('providers.check',provider='payments')
        raw=json.dumps(self.s.state(self.ctx));self.assertNotIn('private-test-secret',raw);self.assertNotIn('private-shipping-token',raw)

    def test_client_provision_requires_platform_operator(self):
        with self.assertRaises(Problem):self.act('clients.create',name='Client',email='client@example.test')
        with patch.dict(os.environ,{'TW_PLATFORM_OWNER_EMAIL':'owner@example.test'}):
            result=self.act('clients.create',name='Client',email='client@example.test')
        self.assertNotEqual(result['client']['tenant_id'],self.t)
        self.assertIn('token',result['invitation'])

    def test_full_refund_and_local_cancellation_need_provider_evidence(self):
        job=self.link();raw,headers=self.event(job);body=json.loads(raw)
        body['payload']['payment']={'entity':{'id':'pay_fixture','status':'captured','amount':1000,'currency':'INR'}}
        raw=json.dumps(body).encode();headers['X-Razorpay-Signature']=hmac.new(b'webhook-test-secret',raw,hashlib.sha256).hexdigest()
        payment_services.webhook(self.s,self.t,'payments',raw,headers)
        with self.assertRaises(Problem):self.act('commerce.order.transition',id=self.o['id'],version=self.o['version'],status='cancelled')
        def remote(t,scope,method,edge,payload):
            return {'id':'rfnd_fixture','payment_id':'pay_fixture','amount':1000,'currency':'INR','status':'processed','notes':payload['notes']}
        with patch('payment_services.razorpay',side_effect=remote) as provider:
            result=self.act('payments.refund',id=job['id']);self.act('payments.refund',id=job['id'])
            self.assertEqual(provider.call_count,1)
        self.assertEqual(result['result']['provider_status'],'processed')
        cancelled=self.act('commerce.order.transition',id=self.o['id'],version=self.o['version'],status='cancelled')
        self.assertEqual(cancelled['status'],'cancelled')

    def test_metadata_check_is_invalid_after_credential_change(self):
        with patch.dict(os.environ,{'TW_PROVIDER_READS':'true'}),patch('provider_checks.request',return_value={'entity':'collection'}):
            self.act('providers.check',provider='payments')
        self.assertTrue(self.s.state(self.ctx)['provider_checks'][0]['current'])
        with patch.dict(os.environ,{'TW_PAYMENTS_'+self.t.upper()+'_KEY_SECRET':'changed'}):
            self.assertFalse(self.s.state(self.ctx)['provider_checks'][0]['current'])

    def test_unknown_webhook_ids_and_changed_duplicates_are_rejected(self):
        job=self.link();raw,headers=self.event(job);payment_services.webhook(self.s,self.t,'payments',raw,headers)
        raw2,headers2=self.event(job,amount=999)
        with self.assertRaises(Exception):payment_services.webhook(self.s,self.t,'payments',raw2,headers2)

    def test_billing_guard_never_blocks_hangup_or_account_read(self):
        with patch.dict(os.environ,{'TW_BILLING_ENFORCE':'true','TW_PLATFORM_OWNER_EMAIL':''}):
            with self.assertRaises(Problem) as failed:self.act('contact.save',name='Blocked',phone='+12025550149')
            self.assertEqual(failed.exception.code,402)
            self.assertIn('services',self.s.state(self.ctx))
            # A missing call is 404, not the subscription 402 gate.
            with self.assertRaises(Problem) as missing:self.act('calls.end',id='missing')
            self.assertEqual(missing.exception.code,404)

    def test_provisioned_client_accepts_once_and_cannot_access_operator_data(self):
        with patch.dict(os.environ,{'TW_PLATFORM_OWNER_EMAIL':'owner@example.test'}):
            result=self.act('clients.create',name='Client',email='new-client@example.test')
        token=result['invitation']['token']
        accepted=self.s.accept_invitation({'token':token,'name':'Client owner','password':'client-owned-password'})
        ctx=self.s.auth(accepted['token'])
        self.assertEqual(ctx['tenant_id'],result['client']['tenant_id'])
        self.assertEqual(ctx['role'],'admin');self.assertEqual(len(ctx['workspaces']),1)
        self.assertEqual(self.s.state(ctx)['contacts'],[])
        with self.assertRaises(Problem):self.s.auth(accepted['token'],self.t)
        with self.assertRaises(Problem):self.s.accept_invitation({'token':token,'name':'Again','password':'client-owned-password'})

    def test_cancelled_subscription_cannot_be_reactivated_by_delayed_event(self):
        with self.s.db() as db:
            job=self.s._put(db,self.t,'servicejob',{'kind':'billing.subscription','reference':'workspace-0','created':1,'payload':{'plan_id':'plan_fixture','notes':{'plan_key':'starter'}},'result':{'provider_id':'sub_fixture'},'status':'created'})
        def send(status,stamp,event_id):
            entity={'id':'sub_fixture','plan_id':'plan_fixture','status':status,'current_end':int(time.time())+3600,'notes':{'operation_id':job['id'],'workspace_id':self.t}}
            raw=json.dumps({'account_id':'acc_fixture','created_at':stamp,'payload':{'subscription':{'entity':entity}}}).encode()
            headers={'X-Razorpay-Event-Id':event_id,'X-Razorpay-Signature':hmac.new(b'webhook-test-secret',raw,hashlib.sha256).hexdigest()}
            payment_services.webhook(self.s,self.t,'billing',raw,headers)
        send('cancelled',100,'cancelled_event');send('active',101,'late_active_event')
        self.assertFalse(self.s.state(self.ctx)['services']['subscription_active'])
        self.assertEqual(self.s.state(self.ctx)['services']['subscription']['result']['provider_status'],'cancelled')

    def test_only_definitive_failure_can_be_released_for_corrected_request(self):
        with patch('payment_services.razorpay',side_effect=RemoteError('rejected',True)) as remote:
            failed=self.act('payments.create-link',order_id=self.o['id'])
            self.act('services.release-failed',id=failed['id'])
            second=self.act('payments.create-link',order_id=self.o['id'])
            self.assertNotEqual(failed['id'],second['id']);self.assertEqual(remote.call_count,2)
        with self.s.db() as db:
            unknown=self.s._put(db,self.t,'servicejob',{'kind':'shipping.order','reference':'other','status':'unknown','created':1})
        with self.assertRaises(Problem):self.act('services.release-failed',id=unknown['id'])
