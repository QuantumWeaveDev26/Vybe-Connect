'use strict';
const RECOVERY={token:null,mode:null,generation:0};
function clearPasswordRecovery(){RECOVERY.token=null;RECOVERY.mode=null;RECOVERY.generation++}
function hasPasswordResetHash(){return location.hash.startsWith('#reset=')}
function passwordRecoveryMarkup(mode,available=true){
 let content='';
 if(mode==='reset')content=`<h2>Choose a new password</h2><p class="hint">This link expires after 15 minutes and works once. Resetting signs out all sessions. Authenticator MFA stays enabled if configured.</p>${field('new_password','New password','','password')}${field('confirm_password','Confirm new password','','password')}<button class="primary" type="submit">Reset password and sign out</button>`;
 else if(mode==='sent')content='<h2>Check your mailbox</h2><p>If an eligible account exists, a password reset link will be emailed. Check spam folders too. Recent requests may be limited. This page does not confirm account registration or email delivery.</p>';
 else content='<h2>Forgot your password?</h2>'+(available?'<p class="hint">Enter your account email. If eligible, you will receive a single-use reset link.</p><div class="field"><label for="recovery-email">Account email</label><input id="recovery-email" name="email" type="email" autocomplete="username" maxlength="200" required></div><button class="primary" type="submit">Send reset link</button>':'<p>Email password recovery is not configured. Contact your server operator for account recovery.</p>');
 return `<div class="authscreen"><section class="authstory"><div class="brand">VYBE Connect</div><h1>Account recovery.</h1><p>Restore access while keeping your workspace permissions and MFA intact.</p></section><section class="authform"><form id="recovery-form">${content}<p id="recovery-error" class="error"></p>${btn('Return to sign in','password-back','','ghost')}${mode==='reset'?btn('Request a new reset link','password-forgot','','ghost'):''}</form></section></div>`;
}
function showRecoveryPage(mode){
 RECOVERY.mode=mode;const generation=++RECOVERY.generation;
 $('#app').innerHTML=passwordRecoveryMarkup(mode,S.passwordRecoveryAvailable);
 if(mode==='reset')for(const name of ['new_password','confirm_password']){const input=$('#f-'+name);input.autocomplete='new-password';input.minLength=12;input.maxLength=256}
 $('#recovery-form').onsubmit=async event=>{
  event.preventDefault();if(mode==='sent'||mode==='request'&&!S.passwordRecoveryAvailable)return;
  const same=()=>RECOVERY.generation===generation&&RECOVERY.mode===mode;
  if(!same())return;const submit=event.target.querySelector('button[type=submit]');submit.disabled=true;
  try{
   const values=Object.fromEntries(new FormData(event.target));
   if(mode==='reset'){
    if(values.new_password!==values.confirm_password)throw new Error('New passwords do not match.');
    await api('/api/password/reset',{method:'POST',body:JSON.stringify({token:RECOVERY.token,new_password:values.new_password})});
    if(!same())return;clearPasswordRecovery();clearAccountSession();S.initialized=true;renderAuth();toast('Password reset. Sign in again; MFA remains required if enabled.');
   }else{
    await api('/api/password/request',{method:'POST',body:JSON.stringify({email:values.email})});
    if(same())showRecoveryPage('sent');
   }
  }catch(error){if(same()){$('#recovery-error').textContent=error.message;submit.disabled=false}}
 };
}
async function openPasswordReset(){
 const token=new URLSearchParams(location.hash.slice(1)).get('reset');
 clearAccountSession();INV.token=null;clearPasswordRecovery();RECOVERY.token=token;
 history.replaceState(null,'',location.pathname);$('#modal').close();showRecoveryPage('reset');
 try{const bootstrap=await api('/api/bootstrap');S.passwordRecoveryAvailable=bootstrap.password_recovery_available===true}catch{}
}
function passwordRecoveryAction(action){
 if(action==='password-back'){clearPasswordRecovery();renderAuth();return}
 if(action==='password-forgot'){clearAccountSession();INV.token=null;clearPasswordRecovery();showRecoveryPage('request')}
}
