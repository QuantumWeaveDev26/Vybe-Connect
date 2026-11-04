'use strict';
let accountEntryGeneration=0;
function accountEntryMarkup(setup){
 const passwordLabel=setup?'Create password':'Password';
 return `<div class="authscreen"><section class="authstory"><div class="brand"><span class="brandmark" aria-hidden="true"><svg viewBox="0 0 140 140"><path d="M18 24h29l23 66 23-66h29L83 118H57Z" fill="currentColor"/></svg></span>VYBE Connect</div><h1>Every conversation.<br>One connected team.</h1><p>Bring your customer conversations, team and business knowledge together.</p><div class="authfeatures"><span>✓ Shared inbox</span><span>✓ Your AI agents</span><span>✓ Your workspace</span></div></section><section class="authform"><form id="authform"><div class="badge">YOUR BUSINESS MESSAGING PLATFORM</div><h2>${setup?'Create your workspace':'Welcome back'}</h2><p class="muted">${setup?'Set up the owner account for your business.':'Sign in with your workspace email and password.'}</p>${setup?'<div class="field"><label for="business">Business name</label><input id="business" name="business" required maxlength="100" autocomplete="organization" placeholder="Your business"></div><div class="field"><label for="name">Your name</label><input id="name" name="name" required maxlength="100" autocomplete="name" placeholder="Full name"></div>':''}<div class="field"><label for="email">Email address</label><input id="email" name="email" type="email" autocomplete="username" autocapitalize="none" spellcheck="false" maxlength="200" required placeholder="you@company.com"></div><div class="field"><label for="password">${passwordLabel}</label><div class="auth-password-control"><input id="password" name="password" type="password" autocomplete="${setup?'new-password':'current-password'}" ${setup?'minlength="12" ':''}maxlength="256" required placeholder="${setup?'At least 12 characters':'Enter your password'}"><button id="auth-password-toggle" type="button" aria-controls="password" aria-pressed="false" aria-label="Show password">Show</button></div><p id="auth-caps" class="hint auth-caps" role="status" hidden>Caps Lock is on.</p></div>${!setup?`<details id="auth-mfa"><summary>Use an authenticator or recovery code</summary>${mfaCodeField()}</details>`:''}${setup&&S.setupTokenRequired?'<div class="field"><label for="setup_token">Deployment setup token</label><input id="setup_token" name="setup_token" type="password" autocomplete="off" required maxlength="256"><p class="hint">Use the private token supplied by your server operator.</p></div>':''}<p id="autherror" class="error" role="alert" aria-live="polite"></p><button class="primary auth-submit" type="submit">${setup?'Create workspace':'Sign in'} →</button>${!setup?btn('Forgot password?','password-forgot','','ghost auth-forgot'):''}<p class="authfoot">Secure sign-in · ${S.deployment==='hosted'?'Hosted workspace':'Local workspace'}</p></form></section></div>`;
}
function renderAccountEntry(setup){
 const generation=++accountEntryGeneration;$('#app').innerHTML=accountEntryMarkup(setup);
 const form=$('#authform'),password=$('#password'),toggle=$('#auth-password-toggle'),caps=$('#auth-caps'),error=$('#autherror');
 const same=()=>generation===accountEntryGeneration&&form.isConnected;
 toggle.onclick=()=>{const visible=password.type==='password';password.type=visible?'text':'password';toggle.textContent=visible?'Hide':'Show';toggle.setAttribute('aria-pressed',String(visible));toggle.setAttribute('aria-label',visible?'Hide password':'Show password')};
 password.onkeyup=event=>{caps.hidden=!event.getModifierState?.('CapsLock')};password.onblur=()=>{caps.hidden=true};
 form.onsubmit=async event=>{
  event.preventDefault();const submit=form.querySelector('button[type=submit]');if(submit.disabled)return;
  submit.disabled=true;submit.textContent=setup?'Creating workspace…':'Signing in…';error.textContent='';
  try{
   const values=Object.fromEntries(new FormData(form));values.email=String(values.email||'').trim();
   await api(setup?'/api/setup':'/api/login',{method:'POST',body:JSON.stringify(values)});
   if(!same())return;S.workspace='';S.initialized=true;await refresh();
  }catch(err){
   if(!same())return;
   const mfa=!setup&&err.status===401&&/authenticator|recovery code/i.test(err.message);
   error.textContent=err.message==='Invalid email or password.'?'Check your email and password, then try again. If you forgot your password, use the link below.':err.message;
   if(mfa){$('#auth-mfa').open=true;$('#f-code').focus();submit.textContent='Verify and sign in →'}
   else submit.textContent=setup?'Create workspace →':'Sign in →';
   submit.disabled=false;
  }
 };
}
