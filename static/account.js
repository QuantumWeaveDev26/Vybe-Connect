'use strict';
let accountSecurityGeneration=0;
function mfaCodeField(required=false){return `<div class="field"><label for="f-code">Authenticator or recovery code</label><input id="f-code" name="code" type="text" autocomplete="one-time-code" maxlength="64" ${required?'required':''}><p class="hint">${required?'Enter a fresh authenticator code or an unused recovery code.':'Leave blank unless MFA is enabled on your account.'}</p></div>`}
function mfaRecoveryMarkup(codes){return '<p>Save these single-use recovery codes in a private password manager. They will not be shown again. Each code can replace an authenticator code once.</p><div class="code">'+codes.map(c=>`<div>${esc(c)}</div>`).join('')+'</div><p class="hint">Enabling or disabling MFA signs out all devices. Wait for a fresh authenticator code before signing in again.</p>'}
function securityModal(title,html,submit,label){showModal(title,html,submit,label);$('#modal').dataset.accountSecurity='true'}
function clearSecurityDialog(){const modal=$('#modal');if(modal?.dataset.accountSecurity==='true'){accountSecurityGeneration++;modal.innerHTML='';delete modal.dataset.accountSecurity;formSubmit=null}}
async function accountSecurityForm(){
  const user=S.data?.context.user.id;if(!user)throw new Error('Sign in to manage account security.');
  const generation=++accountSecurityGeneration,same=()=>S.data?.context.user.id===user&&generation===accountSecurityGeneration;
  const status=await api('/api/account/mfa');if(!same())return;
  const password=()=>field('current_password','Current password','','password');
  const secureInput=()=>{const input=$('#f-current_password');if(input){input.autocomplete='current-password';input.minLength=12;input.maxLength=256}};
  const finish=async(operation,values)=>{
    if(!same())throw new Error('Account or dialog changed. Reopen account security.');
    const result=await api('/api/account/mfa/'+operation,{method:'POST',body:JSON.stringify(values)});
    const show=generation===accountSecurityGeneration&&S.data?.context.user.id===user;
    if(result.sessions_revoked&&S.data?.context.user.id===user){clearAccountSession();renderAuth()}
    if(!show)return;
    if(result.recovery_codes)securityModal('Save your recovery codes',mfaRecoveryMarkup(result.recovery_codes),()=>$('#modal').close(),'I saved these codes');
    else{$('#modal').close();toast('MFA disabled. Sign in again.')}
  };
  if(status.enabled){
    securityModal('Account security',`<p><strong>Authenticator MFA is enabled.</strong> ${Number(status.recovery_remaining)} recovery codes remain. This applies to your account in every workspace.</p>`+password()+mfaCodeField(true)+field('operation','Security action','recovery','select',[['recovery','Replace recovery codes'],['disable','Disable authenticator MFA']])+'<p class="hint">Replacing codes invalidates all previous recovery codes. Disabling MFA signs out every device.</p>',values=>finish(values.operation,{current_password:values.current_password,code:values.code}),'Apply security change');secureInput();return;
  }
  securityModal('Enable authenticator MFA','<p>Add a second factor to your account across all workspaces. You will need an authenticator app and a private place to save recovery codes.</p>'+password(),async values=>{
    if(!same())throw new Error('Account or dialog changed. Reopen account security.');
    const enrollment=await api('/api/account/mfa/begin',{method:'POST',body:JSON.stringify({current_password:values.current_password})});if(!same())return;
    securityModal('Connect your authenticator',`<p>In your authenticator app, add a time-based account named VYBE Connect. Enter this setup key manually. Use six digits, SHA-1 and a 30-second interval.</p><div class="code">${esc(enrollment.secret)}</div><details><summary>Authenticator provisioning URI</summary><div class="code" style="overflow-wrap:anywhere">${esc(enrollment.uri)}</div></details><p class="hint">This setup expires in 10 minutes. MFA is enabled only after you verify a code.</p>`+password()+mfaCodeField(true),values=>finish('confirm',{current_password:values.current_password,code:values.code}),'Verify and enable MFA');secureInput();
  },'Generate setup key');secureInput();
}
function accountPasswordFields(){
  return field('current_password','Current password','','password')+field('new_password','New password','','password')+field('confirm_password','Confirm new password','','password')+'<p class="hint">This changes your account across all workspaces and signs out every session. Roles, memberships and business data stay unchanged.</p>';
}
function clearAccountSession(){
  clearHelpWidget();
  accountSecurityGeneration++;
  G.id=null;G.graph=null;G.dirty=false;G.scope='';
  S.data=null;S.workspace='';S.chat=null;S.draft='';localStorage.removeItem('tw_workspace');clearAnalyticsReport();
  A.scope=null;A.chat=null;A.agent=null;A.draft='';A.busy=false;$('#workspace-ai')?.remove();
}
function accountPasswordForm(){
  const user=S.data?.context.user.id;if(!user)throw new Error('Sign in to change your password.');
  showModal('Change account password',accountPasswordFields(),async values=>{
    if(S.data?.context.user.id!==user)throw new Error('Account changed. Reopen password settings.');
    if(values.new_password!==values.confirm_password)throw new Error('New passwords do not match.');
    await api('/api/account/password',{method:'POST',body:JSON.stringify({current_password:values.current_password,new_password:values.new_password})});
    if(S.data?.context.user.id!==user)return;
    $('#modal').close();$('#modal').innerHTML='';clearAccountSession();renderAuth();toast('Password changed. Sign in again on each device.');
  },'Change password and sign out');
  for(const name of ['current_password','new_password','confirm_password']){$('#f-'+name).minLength=12;$('#f-'+name).maxLength=256;$('#f-'+name).autocomplete=name==='current_password'?'current-password':'new-password'}
}

async function refreshWorkspace(button){
 if(button?.disabled)return;const scope=S.data?.context.user.id;
 if(button){button.disabled=true;button.setAttribute('aria-busy','true')}
 try{const success=await refresh();if(success&&scope===S.data?.context.user.id)toast('Workspace is up to date.')}finally{if(button?.isConnected){button.disabled=false;button.removeAttribute('aria-busy')}}
}
function accountProfileForm(){
 const ctx=S.data?.context;if(!ctx)throw new Error('Sign in to view your profile.');
 const user=ctx.user.id,tenant=ctx.tenant_id,same=()=>S.data?.context.user.id===user&&S.data?.context.tenant_id===tenant;
 const info=`<div class="profile-summary"><span class="avatar">${initials(ctx.user.name)}</span><div><strong>${esc(ctx.user.name)}</strong><p>${esc(ctx.user.email||'Read-only preview visitor')}</p></div></div><div class="profile-meta"><span>Workspace</span><strong>${esc(ctx.workspace.name)}</strong><span>Role</span><strong>${esc(ctx.role)}</strong></div>`;
 showModal('Your profile',info+field('name','Display name',ctx.user.name)+`<p class="hint">${S.review?'This preview is read-only. Sign in to your owner account to manage your profile.':'Your display name applies across all your workspaces. Email and account permissions cannot be changed here.'}</p>`+(!S.review?`<div class="buttons">${btn('Account security','account-security','','small')}${btn('Change password','account-password','','small')}</div>`:''),async values=>{
  if(S.review){$('#modal').close();return}
  if(!same())throw new Error('Account or workspace changed. Reopen your profile.');
  await api('/api/account/profile',{method:'POST',body:JSON.stringify({name:values.name})});
  if(!same())return;$('#modal').close();await refresh();toast('Profile updated.');
 },S.review?'Close':'Save profile');$('#f-name').maxLength=100;$('#f-name').disabled=S.review;
}
