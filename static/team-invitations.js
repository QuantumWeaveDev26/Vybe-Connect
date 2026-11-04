'use strict';
const INV={token:null};
function invitationPanel(){
  if(S.data.context.role!=='admin')return '';
  return `<section class="card"><div class="cardhead"><h2>Workspace invitations</h2>${btn('Invite teammate','invite-create','','primary small')}</div><div class="cardbody"><p class="hint">One-time links let recipients choose their own passwords. Existing accounts must enter their current password. Share links privately with the intended recipient. Invitation emails are not sent automatically.</p>${(S.data.invitations||[]).map(i=>`<div class="summaryrow"><span><strong>${esc(i.email)}</strong> · ${esc(i.role)} · ${esc(i.status)}<div class="sub">Expires ${esc(new Date(i.expires*1000).toLocaleString())}</div></span>${i.status==='pending'?btn('Revoke','invite-revoke',`data-id="${esc(i.id)}"`,'small'):''}</div>`).join('')||'<p>No invitations issued.</p>'}</div></section>`;
}
async function invitationAction(action,el){
  const tenant=S.data.context.tenant_id,user=S.data.context.user.id,same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user;
  if(action==='invite-create')return showModal('Invite a workspace teammate',field('email','Recipient email','','email')+field('role','Workspace role','agent','select',[['agent','Agent'],['admin','Administrator']])+field('hours','Link expires after hours',24,'number')+'<p class="hint">An administrator can change workspace configuration and team access. Verify the recipient and role before creating a link. The recipient chooses their password.</p>',async data=>{
    if(!same())throw new Error('Workspace changed.');const invitation=await act('invite.create',{email:data.email,role:data.role,hours:Number(data.hours)});if(!same())return;
    await refresh();if(!same())return;
    const link=location.origin+'/#invite='+encodeURIComponent(invitation.token);
    showModal('Invitation created',`<p>Copy this link now and share it privately with <strong>${esc(invitation.email)}</strong>. It cannot be retrieved again; revoke and reissue if needed.</p><label for="invite-link">One-time invitation link</label><input id="invite-link" type="text" readonly value="${esc(link)}"><p class="hint">Expires ${esc(new Date(invitation.expires*1000).toLocaleString())}. No email has been sent. The recipient must be able to reach this deployment.</p>`,()=>$('#modal').close(),'Close');
  },'Create one-time link');
  if(action==='invite-revoke')return showModal('Revoke invitation','<p>This invalidates the unredeemed link. It does not remove an existing team membership.</p>',async()=>{
    if(!same())throw new Error('Workspace changed.');await act('invite.revoke',{id:el.dataset.id});if(!same())return;$('#modal').close();await refresh();
  },'Revoke link');
}
function hasInvitationHash(){return location.hash.startsWith('#invite=')}
function invitationMarkup(preview){
  return `<div class="authscreen"><section class="authstory"><div class="brand">VYBE Connect</div><h1>Join your team.</h1><p>Invitation to ${esc(preview.workspace)}</p></section><section class="authform"><form id="invitation-form"><h2>Accept workspace invitation</h2><p>${esc(preview.email)} · ${esc(preview.role)}</p><p class="hint">${preview.existing_account?'Enter your existing account password. This invitation does not reset it.':'Choose your own account password. This invitation grants access only to the named workspace.'}</p>${preview.existing_account?'':field('name','Your name')}${field('password',preview.existing_account?'Current password':'Choose password','','password')}${preview.existing_account?mfaCodeField():''}<p id="invitation-error" class="error"></p><button class="primary" type="submit">Join workspace</button><button id="invitation-cancel" type="button">Return to sign in</button></form></section></div>`;
}
async function openInvitation(){
  const token=new URLSearchParams(location.hash.slice(1)).get('invite');INV.token=token;S.data=null;S.workspace='';S.route='inbox';clearAnalyticsReport();$('#workspace-ai')?.remove();$('#modal').close();
  history.replaceState(null,'',location.pathname);$('#app').innerHTML=empty('Opening invitation','Checking this one-time link…');
  try{
    S.initialized=(await api('/api/bootstrap')).initialized;
    const preview=await api('/api/invitations/inspect',{method:'POST',body:JSON.stringify({token})});if(INV.token!==token)return;
    $('#app').innerHTML=invitationMarkup(preview);$('#f-password').autocomplete=preview.existing_account?'current-password':'new-password';
    $('#invitation-cancel').onclick=()=>{INV.token=null;renderAuth()};
    $('#invitation-form').onsubmit=async event=>{
      event.preventDefault();const submit=event.target.querySelector('button[type=submit]');submit.disabled=true;$('#invitation-cancel').disabled=true;
      try{
        if(INV.token!==token)throw new Error('Invitation changed. Reopen the link.');
        const values=Object.fromEntries(new FormData(event.target)),result=await api('/api/invitations/accept',{method:'POST',body:JSON.stringify({...values,token})});
        if(INV.token!==token)return;INV.token=null;S.initialized=true;S.workspace=result.tenant_id;S.route='inbox';location.hash='inbox';await refresh();
      }catch(error){if(INV.token===token){$('#invitation-error').textContent=error.message;submit.disabled=false;$('#invitation-cancel').disabled=false}}
    };
  }catch(error){if(INV.token===token){INV.token=null;renderAuth();toast(error.message)}}
}

function memberAccessControls(member){
  if(S.data.context.role!=='admin')return '';
  if(member.role==='admin'&&S.data.members.filter(m=>m.role==='admin').length===1)return '<span class="hint">Sole administrator</span>';
  return btn('Change role','member-role',`data-id="${esc(member.id)}"`,'small')+btn('Remove access','member-remove',`data-id="${esc(member.id)}"`,'small ghost danger');
}
function memberAccessAction(action,el){
  const member=S.data.members.find(m=>m.id===el.dataset.id);if(!member)throw new Error('Member no longer available.');
  const tenant=S.data.context.tenant_id,user=S.data.context.user.id,same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user;
  const perform=async(operation,data)=>{if(!same())throw new Error('Workspace changed.');await act(operation,{id:member.id,...data});if(!same())return;$('#modal').close();await refresh()};
  if(action==='member-role')return showModal('Change workspace role',`<p>${esc(member.name)} · ${esc(member.email)}</p>`+field('role','Role',member.role,'select',[['agent','Agent'],['admin','Administrator']])+'<p class="hint">Administrators manage configuration, campaigns, automations and team access. Losing administrator status revokes their pending invitations. Keep at least one administrator.</p>',data=>perform('member.role',data),'Save role');
  if(action==='member-remove')return showModal('Remove workspace access',`<p>Remove <strong>${esc(member.name)}</strong> from <strong>${esc(S.data.context.workspace.name)}</strong>?</p><p>Their account and other workspace memberships remain. Open assignments become unassigned; conversation history remains. Pending invitations issued by a removed administrator are revoked. Existing in-flight requests cannot be recalled.</p>`,()=>perform('member.remove',{}),'Remove workspace access');
}
