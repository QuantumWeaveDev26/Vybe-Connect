'use strict';
let WA_SIGNUP=null,WA_SDK=null,WA_NOTICE=null;
const operatorMetaSettingsPage=settingsPage;
function whatsappScope(){return S.data?S.workspace+':'+S.data.context.user.id:''}
function paintWhatsAppSignup(){if(S.data&&S.route==='settings')render()}
function whatsAppSignupError(message,scope){if(scope!==whatsappScope())return;clearWhatsAppSignup();WA_NOTICE={scope,message};paintWhatsAppSignup();toast(message)}
function clearWhatsAppSignup(){if(WA_SIGNUP?.timer)clearTimeout(WA_SIGNUP.timer);WA_SIGNUP=null}
settingsPage=function(){
 const c=S.data.whatsapp_connection||{},managed=['connected','expired','disconnected','connecting','needs_reconnect'].includes(c.status),admin=S.data.context.role==='admin',scope=whatsappScope();
 if(WA_SIGNUP&&WA_SIGNUP.scope!==scope)clearWhatsAppSignup();
 if(WA_NOTICE&&WA_NOTICE.scope!==scope)WA_NOTICE=null;
 const label=WA_SIGNUP?.ready?'Continue with Meta':['expired','needs_reconnect'].includes(c.status)?'Reconnect WhatsApp':c.status==='connected'?'Reconnect':'Connect WhatsApp';
 const status=c.status==='connected'?'Connected':['expired','needs_reconnect'].includes(c.status)?'Reconnect required':'Not connected';
 return pagehead('Workspace connections','Connect WhatsApp. Your subscription includes VYBE AI.')+`<section class="card whatsapp-connection-card"><div class="cardhead"><h2>Your WhatsApp account</h2>${badge(status,c.status==='connected'?'':'gray')}</div><div class="cardbody"><p>${c.display_name?esc(c.display_name)+' · ':''}${esc(c.display_phone||'Connect the WhatsApp number your customers already know.')}</p>${c.expires?`<p class="hint">Authorization expires ${esc(date(c.expires))}. Reconnect before then to keep access.</p>`:''}<div class="buttons"><button class="primary" data-wa-connect ${!admin||!c.signup_available||S.review||WA_SIGNUP?.busy||WA_SIGNUP?.opened?'disabled':''}>${label}</button>${managed&&c.status!=='disconnected'?`<button data-wa-sending ${!admin||c.status!=='connected'||S.review?'disabled':''}>${c.sending_enabled?'Pause sending':'Enable sending'}</button><button data-wa-disconnect ${!admin||S.review?'disabled':''}>Disconnect</button>`:''}</div><p class="hint">${!admin?'A workspace administrator can manage this connection.':!c.signup_available?'WhatsApp onboarding is awaiting Meta approval. Your connection will be available once approved.':'Sign in securely with Meta and select your business and phone number.'}</p>${c.status==='connected'?`<p class="hint">${c.sending_enabled?'Sending is enabled for business use. Meta charges may apply.':'Sending is paused. Enable it when ready for real business use.'}</p>`:''}<p role="status" id="wa-signup-status">${esc(WA_NOTICE?.message||(WA_SIGNUP?.opened?'Complete authorization in the Meta window.':WA_SIGNUP?.ready?'Ready. Click Continue with Meta to open the secure authorization window.':''))}</p></div></section>`+aiConnectionCard()+((Object.values(S.data.meta?.present||{}).some(Boolean)||Object.keys(S.data.meta?.invalid||{}).length)&&!managed?`<details><summary>Advanced operator settings</summary>${operatorMetaSettingsPage().replace(aiConnectionCard(),'')}</details>`:'');
}
function whatsAppSDK(config){
 if(WA_SDK)return WA_SDK;
 WA_SDK=new Promise((resolve,reject)=>{
  const timeout=setTimeout(()=>{WA_SDK=null;reject(new Error('Meta login could not load. Check browser blockers and try again.'))},15000);
  const loaded=()=>{try{FB.init({appId:config.app_id,version:config.version,xfbml:false,cookie:false});clearTimeout(timeout);resolve()}catch{clearTimeout(timeout);WA_SDK=null;reject(new Error('Meta login initialization failed.'))}};
  if(window.FB){loaded();return}
  const script=document.createElement('script');script.src='https://connect.facebook.net/en_US/sdk.js';script.async=true;script.crossOrigin='anonymous';script.onload=loaded;script.onerror=()=>{clearTimeout(timeout);script.remove();WA_SDK=null;reject(new Error('Meta login is blocked or unavailable.'))};document.head.append(script);
 });return WA_SDK;
}
async function finishWhatsAppSignup(){
 const attempt=WA_SIGNUP;if(!attempt||attempt.busy||!attempt.code||!attempt.waba_id||!attempt.phone_number_id||attempt.scope!==whatsappScope())return;
 attempt.busy=true;const status=document.querySelector('#wa-signup-status');if(status)status.textContent='Verifying your account and webhook…';
 try{await act('whatsapp.finish',{state:attempt.config.state,code:attempt.code,waba_id:attempt.waba_id,phone_number_id:attempt.phone_number_id});if(attempt.scope!==whatsappScope())return;clearWhatsAppSignup();WA_NOTICE=null;await refresh();paintWhatsAppSignup();toast('WhatsApp connected. Sending is paused until you enable it.')}catch(error){if(attempt.scope!==whatsappScope())return;whatsAppSignupError(error.message,attempt.scope)}
}
window.addEventListener('message',event=>{
 if(!WA_SIGNUP?.opened||WA_SIGNUP.scope!==whatsappScope()||!['https://www.facebook.com','https://web.facebook.com'].includes(event.origin))return;
 let value;try{if(typeof event.data==='string'&&event.data.length<=12000)value=JSON.parse(event.data);else if(event.data&&typeof event.data==='object')value=event.data;else return}catch{return}
 if(value.type!=='WA_EMBEDDED_SIGNUP')return;
 if(value.event==='FINISH'||value.event==='FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING'){
  const d=value.data||{};if(!/^\d{1,30}$/.test(d.waba_id||'')||!/^\d{1,30}$/.test(d.phone_number_id||''))return;
  WA_SIGNUP.waba_id=String(d.waba_id);WA_SIGNUP.phone_number_id=String(d.phone_number_id);finishWhatsAppSignup();
 }else if(value.event==='CANCEL'||value.event==='ERROR'){whatsAppSignupError('Meta signup was cancelled or rejected. Start a new connection to try again.',WA_SIGNUP.scope)}
});
document.addEventListener('click',async event=>{
 const button=event.target.closest?.('[data-wa-connect],[data-wa-disconnect],[data-wa-sending]');if(!button||button.disabled)return;
 const scope=whatsappScope();
 if(button.hasAttribute('data-wa-connect')){
  if(WA_SIGNUP?.ready&&WA_SIGNUP.scope===scope){
   const attempt=WA_SIGNUP;attempt.ready=false;attempt.opened=true;WA_NOTICE=null;paintWhatsAppSignup();
   attempt.timer=setTimeout(()=>{if(WA_SIGNUP===attempt){whatsAppSignupError('Signup timed out. Start a new connection to try again.',scope)}},300000);
   try{FB.login(response=>{if(WA_SIGNUP!==attempt||scope!==whatsappScope())return;const code=response.authResponse?.code;if(!code){whatsAppSignupError('Meta returned no authorization code. Allow browser popups and check the app’s Facebook Login for Business domain settings. Then start a new connection.',scope);return}attempt.code=code;finishWhatsAppSignup()},{config_id:attempt.config.config_id,response_type:'code',override_default_response_type:true,auth_type:'rerequest',extras:{setup:{}}})}catch{whatsAppSignupError('Meta login could not open. Allow the popup and try again.',scope)}return;
  }
  button.disabled=true;WA_NOTICE=null;const loading=document.querySelector('#wa-signup-status');if(loading)loading.textContent='Preparing secure Meta login…';
  try{clearWhatsAppSignup();const config=await act('whatsapp.begin',{});if(scope!==whatsappScope())return;await whatsAppSDK(config);if(scope!==whatsappScope())return;WA_SIGNUP={scope,config,ready:true};paintWhatsAppSignup()}catch(error){if(scope===whatsappScope()){whatsAppSignupError(error.message,scope)}}return;
 }
 const c=S.data.whatsapp_connection||{};
 if(button.hasAttribute('data-wa-disconnect')){
  if(!confirm('Disconnect this workspace? Messaging and incoming webhook processing will stop here. To revoke Meta permissions as well, remove VYBE Connect in Meta Business Integrations.'))return;
  try{await act('whatsapp.disconnect',{});if(scope!==whatsappScope())return;clearWhatsAppSignup();await refresh();toast('Workspace disconnected.')}catch(error){toast(error.message)}return;
 }
 const enabled=!c.sending_enabled;
 if(enabled&&!confirm('Enable real WhatsApp sending for this workspace? Business messages may incur Meta charges. No test message will be sent.'))return;
 try{await act('whatsapp.sending',{enabled});if(scope===whatsappScope())await refresh()}catch(error){toast(error.message)}
});
window.addEventListener('hashchange',()=>{if(WA_SIGNUP&&WA_SIGNUP.scope!==whatsappScope())clearWhatsAppSignup()});
