import os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem
from provider_transport import RemoteError
import whatsapp_calls

class OutboundCallingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'c.db');self.ctx=self.s.auth(self.s.setup('Owner','calls@example.test','long-calling-password','Calls')['token']);self.t=self.ctx['tenant_id'];self.c=self.s.action(self.ctx,'contact.save',{'name':'Customer','phone':'12025550146'})
  p='TW_META_'+self.t.upper()+'_';q='TW_CALLING_'+self.t.upper()+'_';self.env=patch.dict(os.environ,{p+'TOKEN':'private',p+'PHONE_ID':'123',p+'APP_SECRET':'secret',p+'VERSION':'v25.0',q+'ENABLED':'true',q+'OUTBOUND_ENABLED':'true'});self.env.start()
  self.permission={'permission':{'status':'temporary','expiration_time':int(time.time())+3600},'actions':[{'action_name':'start_call','can_perform_action':True}]}
  self.data={'contact_id':self.c['id'],'request_id':'request-0123456789abcdef','sdp':'v=0\r\no=outbound'}
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def act(self,op,data=None):return self.s.action(self.ctx,op,data or self.data)
 def test_disabled_gate_makes_no_request(self):
  with patch.dict(os.environ,{'TW_CALLING_'+self.t.upper()+'_OUTBOUND_ENABLED':'false'}),patch('outbound_calls.remote') as r:
   with self.assertRaises(Problem):self.act('calls.start')
   r.assert_not_called()
 def test_permission_denial_never_dials(self):
  with patch('outbound_calls.remote',return_value={'permission':{},'actions':[]}) as r:
   result=self.act('calls.start');self.assertEqual(result['status'],'failed');self.assertEqual(r.call_count,1)
 def test_one_attempt_no_duplicate_dial_and_private_answer(self):
  with patch('outbound_calls.remote',side_effect=[self.permission,{'calls':[{'id':'wacid.test'}]}]) as r:
   call=self.act('calls.start');self.assertEqual(call['status'],'dialing');self.act('calls.start');self.assertEqual(r.call_count,2)
  whatsapp_calls.ingest(self.s,self.t,[{'id':'wacid.test','event':'connect','to':self.c['phone'],'session':{'sdp_type':'answer','sdp':'v=0\r\no=answer'}}])
  state=self.s.state(self.ctx)['calling']['calls'][0];self.assertEqual(state['status'],'connected');self.assertNotIn('answer',state)
  self.assertEqual(self.act('calls.session',{'id':call['id']})['answer'],'v=0\r\no=answer')
  with self.assertRaises(Problem):self.s.action(dict(self.ctx,user=dict(self.ctx['user'],id='other')),'calls.session',{'id':call['id']})
 def test_unknown_response_is_not_retried(self):
  with patch('outbound_calls.remote',side_effect=[self.permission,RemoteError('timeout')]) as r:
   self.assertEqual(self.act('calls.start')['status'],'unknown');self.act('calls.start');self.assertEqual(r.call_count,2)
 def test_terminal_webhook_wins_before_http_response(self):
  def remote(t,edge,method='GET',payload=None,query=None):
   if edge=='call_permissions':return self.permission
   whatsapp_calls.ingest(self.s,self.t,[{'id':'wacid.early','event':'terminate','to':self.c['phone'],'biz_opaque_callback_data':payload['biz_opaque_callback_data']}]);return {'calls':[{'id':'wacid.early'}]}
  with patch('outbound_calls.remote',side_effect=remote):self.assertEqual(self.act('calls.start')['status'],'ended')
 def test_permission_request_requires_live_window_and_sender_gate(self):
  with patch('outbound_calls.remote') as r:
   with self.assertRaises(Problem):self.act('calls.request-permission')
   r.assert_not_called()
 def test_other_workspace_cannot_dial_contact(self):
  other=dict(self.ctx,tenant_id='foreign')
  with patch('outbound_calls.remote') as r:
   with self.assertRaises(Problem):self.s.action(other,'calls.start',self.data)
   r.assert_not_called()

 def test_expired_permission_never_dials(self):
  self.permission['permission']['expiration_time']=int(time.time())-1
  with patch('outbound_calls.remote',return_value=self.permission) as r:
   self.assertEqual(self.act('calls.start')['status'],'failed');self.assertEqual(r.call_count,1)
 def test_changed_replay_payload_rejected(self):
  with patch('outbound_calls.remote',side_effect=[self.permission,{'calls':[{'id':'wacid.test'}]}]):self.act('calls.start')
  with patch('outbound_calls.remote') as r:
   with self.assertRaises(Problem):self.act('calls.start',dict(self.data,sdp='v=0 changed'))
   r.assert_not_called()

 def test_permission_request_sent_once_and_visible_in_history(self):
  self.s.inbound(self.t,{'id':'inbound1','from':self.c['phone'],'type':'text','text':{'body':'Please help'},'timestamp':str(int(time.time()))})
  permission={'permission':{},'actions':[{'action_name':'send_call_permission_request','can_perform_action':True}]}
  with patch.dict(os.environ,{'TW_META_'+self.t.upper()+'_LIVE':'true'}),patch('outbound_calls.remote',side_effect=[permission,{'messages':[{'id':'wamid.permission'}]}]) as r:
   result=self.act('calls.request-permission');self.assertEqual(result['status'],'sent');self.act('calls.request-permission');self.assertEqual(r.call_count,2)
   self.assertEqual(r.call_args.args[1],'messages');self.assertEqual(r.call_args.args[3]['interactive']['action']['name'],'call_permission_request')
  history=self.s.state(self.ctx)['calling']['requests'];self.assertEqual(len(history),1);self.assertNotIn('request_digest',history[0])
 def test_foreign_owner_cannot_replay_request_id(self):
  with patch('outbound_calls.remote',side_effect=[self.permission,{'calls':[{'id':'wacid.test'}]}]):self.act('calls.start')
  with patch('outbound_calls.remote') as r:
   with self.assertRaises(Problem):self.s.action(dict(self.ctx,user=dict(self.ctx['user'],id='other')),'calls.start',self.data)
   r.assert_not_called()

 def test_late_signed_answer_reconciles_uncertain_http_outcome(self):
  with patch('outbound_calls.remote',side_effect=[self.permission,RemoteError('timeout')]):call=self.act('calls.start')
  self.assertEqual(call['status'],'unknown')
  whatsapp_calls.ingest(self.s,self.t,[{'id':'wacid.late','event':'connect','to':self.c['phone'],'biz_opaque_callback_data':call['id'],'session':{'sdp_type':'answer','sdp':'v=0 answer'}}])
  state=self.s.state(self.ctx)['calling']['calls'][0];self.assertEqual(state['status'],'connected');self.assertEqual(state['provider_id'],'wacid.late')
