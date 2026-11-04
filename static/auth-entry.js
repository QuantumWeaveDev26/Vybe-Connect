'use strict';
let accountEntryGeneration=0;
function accountEntryMarkup(setup,signup=false){
 const creating=setup||signup;
 const passwordLabel=creating?'Create password':'Password';
 return `<div class="authscreen${signup?' auth-register':''}"><section class="authstory"><div class="brand"><span class="brandmark" aria-hidden="true"><svg viewBox="0 0 140 140"><path d="M18 24h29l23 66 23-66h29L83 118H57Z" fill="currentColor"/></svg></span>VYBE Connect</div><h1>Every conversation.<br>One connected team.</h1><p>Bring your customer conversations, team and business knowledge together.</p><div class="authfeatures"><span>✓ Shared inbox</span><span>✓ Your AI agents</span><span>✓ Your workspace</span></div></section><section class="authform"><form id="authform"><div class="badge">YOUR BUSINESS MESSAGING PLATFORM</div><h2>${setup?'Create your workspace':signup?'Create your account':'Welcome back'}</h2><p class="muted">${setup?'Set up the owner account for your business.':signup?'Your business gets its own private workspace.':'Sign in with your email and password.'}</p>${creating?'<div class="field"><label for="business">Business name</label><input id="business" name="business" required maxlength="100" autocomplete="organization" placeholder="Your business"></div><div class="field"><label for="name">Your name</label><input id="name" name="name" required maxlength="100" autocomplete="name" placeholder="Full name"></div>':''}<div class="field"><label for="email">Email address</label><input id="email" name="email" type="email" autocomplete="username" autocapitalize="none" spellcheck="false" maxlength="200" required placeholder="you@company.com"></div><div class="field"><label for="password">${passwordLabel}</label><div class="auth-password-control"><input id="password" name="password" type="password" autocomplete="${creating?'new-password':'current-password'}" ${creating?'minlength="12" ':''}maxlength="256" required placeholder="${creating?'At least 12 characters':'Enter your password'}"><button id="auth-password-toggle" type="button" aria-controls="password" aria-pressed="false" aria-label="Show password">Show</button></div><p id="auth-caps" class="hint auth-caps" role="status" hidden>Caps Lock is on.</p></div>${!creating?`<details id="auth-mfa"><summary>Use an authenticator or recovery code</summary>${mfaCodeField()}</details>`:''}${setup&&S.setupTokenRequired?'<div class="field"><label for="setup_token">Deployment setup token</label><input id="setup_token" name="setup_token" type="password" autocomplete="off" required maxlength="256"><p class="hint">Use the private token supplied by your server operator.</p></div>':''}${!setup?'<label class="auth-remember"><input type="checkbox" name="remember" checked><span>Keep me signed in for 30 days</span></label>':''}<p id="autherror" class="error" role="alert" aria-live="polite"></p><button class="primary auth-submit" type="submit">${setup?'Create workspace':signup?'Create account':'Sign in'} →</button>${!creating?btn('Forgot password?','password-forgot','','ghost auth-forgot'):''}${!creating&&S.signupAvailable?`<p class="auth-switch">New to VYBE Connect? ${btn('Create account','auth-signup','','ghost')}</p>`:''}${signup?btn('Already have an account? Sign in','auth-login','','ghost auth-forgot'):''}<p class="authfoot">Secure sign-in · ${S.deployment==='hosted'?'Hosted workspace':'Local workspace'}</p></form></section></div>`;
}
function renderAccountEntry(setup,signup=false){
 const generation=++accountEntryGeneration;$('#app').innerHTML=accountEntryMarkup(setup,signup);
 const form=$('#authform'),password=$('#password'),toggle=$('#auth-password-toggle'),caps=$('#auth-caps'),error=$('#autherror');
 const same=()=>generation===accountEntryGeneration&&form.isConnected;
 toggle.onclick=()=>{const visible=password.type==='password';password.type=visible?'text':'password';toggle.textContent=visible?'Hide':'Show';toggle.setAttribute('aria-pressed',String(visible));toggle.setAttribute('aria-label',visible?'Hide password':'Show password')};
 password.onkeyup=event=>{caps.hidden=!event.getModifierState?.('CapsLock')};password.onblur=()=>{caps.hidden=true};
 form.onsubmit=async event=>{
  event.preventDefault();const submit=form.querySelector('button[type=submit]');if(submit.disabled)return;
  submit.disabled=true;submit.textContent=setup?'Creating workspace…':signup?'Creating account…':'Signing in…';error.textContent='';
  try{
   const values=Object.fromEntries(new FormData(form));values.email=String(values.email||'').trim();values.remember=form.querySelector('input[name="remember"]')?.checked===true;
   await api(setup?'/api/setup':signup?'/api/signup':'/api/login',{method:'POST',body:JSON.stringify(values)});
   if(!same())return;S.workspace='';S.initialized=true;if(signup){S.route='inbox';history.replaceState(null,'',location.pathname+'#inbox')}await refresh();
  }catch(err){
   if(!same())return;
   const mfa=!setup&&!signup&&err.status===401&&/authenticator|recovery code/i.test(err.message);
   error.textContent=err.message==='Invalid email or password.'?'Check your email and password, then try again. If you forgot your password, use the link below.':err.message;
   if(mfa){$('#auth-mfa').open=true;$('#f-code').focus();submit.textContent='Verify and sign in →'}
   else submit.textContent=setup?'Create workspace →':signup?'Create account →':'Sign in →';
   submit.disabled=false;
  }
 };
}

function authEntryAction(action){
 if(action==='auth-signup'){
  if(!S.signupAvailable||!S.initialized)throw new Error('Public account creation is not available.');
  S.data=null;S.workspace='';history.replaceState(null,'',location.pathname+'#signup');renderAuth(true);return;
 }
 if(action==='auth-login'){history.replaceState(null,'',location.pathname);renderAuth()}
}
