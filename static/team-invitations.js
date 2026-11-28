'use strict';
const INV={token:null};
function invitationPanel(){
  if(S.data.context.role!=='admin')return '';
  const invitations=S.data.invitations||[];
  const totals=['pending','accepted','expired'].map(status=>invitations.filter(i=>i.status===status).length+' '+status);
  return `<section class="card"><div class="cardhead"><h2>Workspace invitations</h2>${btn('Invite teammate','invite-create','','primary small')}</div><div class="cardbody"><p class="hint">Share one-time links privately.</p>${invitations.length?`<p class="hint">${totals.join(' · ')}</p>`:''}${invitations.map(i=>`<div class="summaryrow"><span><strong>${esc(i.email)}</strong> · ${esc(i.role)} · ${esc(i.status)}<div class="sub">Expires ${esc(new Date(i.expires*1000).toLocaleString())}</div></span>${i.status==='pending'?btn('Revoke','invite-revoke',`data-id="${esc(i.id)}"`,'small'):''}</div>`).join('')||'<p>No invitations issued.</p>'}</div></section>`;
}
function showShareableInvitation(invitation,workspace,same){
  const link=location.origin+'/#invite='+encodeURIComponent(invitation.token);
  const shareText='Join me in '+workspace+' on VYBE Connect. Open this one-time link to accept your invitation:';
  const shareButton=typeof navigator.share==='function'?'<button id="invite-share" type="button" class="primary">Share invite</button>':'';
  showModal('Share your invitation',`<p>Send this one-time link privately to <strong>${esc(invitation.email)}</strong>.</p><div class="buttons">${shareButton}<button id="invite-copy" type="button">Copy link</button><a class="button" href="https://web.whatsapp.com/" target="_blank" rel="noopener noreferrer">Open WhatsApp Web</a></div><p id="invite-share-status" class="hint" role="status"></p><label for="invite-link">Invitation link</label><input id="invite-link" type="text" readonly value="${esc(link)}"><p class="hint">Expires ${esc(new Date(invitation.expires*1000).toLocaleString())}. Copy it before closing.</p>`,()=>$('#modal').close(),'Close');
  $('#dialog-form .modalfoot [data-do="close"]')?.remove();
  const field=$('#invite-link'), status=$('#invite-share-status');
  const current=()=>same()&&$('#invite-link')===field&&$('#modal').open;
  $('#invite-copy').onclick=async()=>{
    if(!current())return;
    try{
      await navigator.clipboard.writeText(link);
      if(current())status.textContent='Link copied. Paste it into your teammate’s WhatsApp chat.';
    }catch{
      if(!current())return;
      field.focus();field.select();
      status.textContent='Link selected. Copy it, then paste it into your teammate’s chat.';
    }
  };
  const share=$('#invite-share');
  if(share)share.onclick=async()=>{
    if(!current())return;
    try{await navigator.share({title:'VYBE Connect invitation',text:shareText,url:link})}
    catch(error){
      if(current()&&error.name!=='AbortError')status.textContent='Sharing is unavailable. Use Copy link instead.';
    }
  };
}
async function invitationAction(action,el){
  const tenant=S.data.context.tenant_id,user=S.data.context.user.id,same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user&&S.data.context.role==='admin';
  if(action==='invite-create'){
    let submitting=false;
    return showModal('Invite a workspace teammate',field('email','Recipient email','','email')+field('role','Workspace role','agent','select',[['agent','Agent'],['admin','Administrator']])+field('hours','Link expires after hours',24,'number')+'<p class="hint">Share the one-time link privately. The recipient chooses their password.</p>',async data=>{
      if(submitting)return;
      if(!same())throw new Error('Workspace changed. Reopen the invitation form.');
      submitting=true;
      let invitation;
      try {
        invitation=await act('invite.create',{email:data.email,role:data.role,hours:Number(data.hours)});
      } catch(error) {
        if(error.status===401)throw new Error('Your session expired. Sign in again, then reopen Team settings.');
        if(error.status>=500||!error.status||error.message.startsWith('The server returned an unreadable response')){
          throw new Error('VYBE could not confirm whether the link was created. Close this form and reload Team settings. If a pending invitation appears, revoke it before creating a new link.');
        }
        throw error;
      } finally {
        submitting=false;
      }
      if(!same())return;
      showShareableInvitation(invitation,S.data.context.workspace.name,same);
      void refresh().catch(error=>toast(error.message));
    },'Create one-time link');
  }
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
  return (member.role==='agent'?btn('Permissions','member-permissions',`data-id="${esc(member.id)}"`,'small'):'')+btn('Change role','member-role',`data-id="${esc(member.id)}"`,'small')+btn('Remove access','member-remove',`data-id="${esc(member.id)}"`,'small ghost danger');
}
function memberAccessAction(action,el){
  const member=S.data.members.find(m=>m.id===el.dataset.id);if(!member)throw new Error('Member no longer available.');
  const tenant=S.data.context.tenant_id,user=S.data.context.user.id,same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user;
  const perform=async(operation,data)=>{if(!same())throw new Error('Workspace changed.');await act(operation,{id:member.id,...data});if(!same())return;$('#modal').close();await refresh()};
  if(action==='member-permissions'){const p=member.permissions||{calling:true,reports:true,exports:true,version:0};return showModal('Workspace permissions',`<p>${esc(member.name)}</p>`+[['calling','Handle calls'],['reports','View reports'],['exports','Export data']].map(([key,label])=>field(key,label,p[key]!==false,'checkbox')).join(''),values=>perform('member.permissions',{version:p.version||0,permissions:values}),'Save permissions')}
  if(action==='member-role')return showModal('Change workspace role',`<p>${esc(member.name)} · ${esc(member.email)}</p>`+field('role','Role',member.role,'select',[['agent','Agent'],['admin','Administrator']])+'<p class="hint">Administrators manage configuration, campaigns, automations and team access. Losing administrator status revokes their pending invitations. Keep at least one administrator.</p>',data=>perform('member.role',data),'Save role');
  if(action==='member-remove')return showModal('Remove workspace access',`<p>Remove <strong>${esc(member.name)}</strong> from <strong>${esc(S.data.context.workspace.name)}</strong>?</p><p>Their account and other workspace memberships remain. Open assignments become unassigned; conversation history remains. Pending invitations issued by a removed administrator are revoked. Existing in-flight requests cannot be recalled.</p>`,()=>perform('member.remove',{}),'Remove workspace access');
}
