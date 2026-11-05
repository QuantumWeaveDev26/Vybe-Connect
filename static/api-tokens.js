'use strict';
function apiTokenManagerMarkup(){
 if(S.data.context.role!=='admin')return '';
 const tokens=S.data.api_tokens||[],stamp=Date.now()/1000;
 return `<section class="card"><div class="cardhead"><h2>API tokens</h2>${btn('Generate token','api-token-create',S.review?'disabled':'','primary small')}</div><div class="cardbody"><p>Read-only access for your integrations.</p><div class="code">${esc(location.origin+'/api/v1')}</div><details><summary>Endpoints and scopes</summary><p><code>GET /contacts</code> · contacts:read<br><code>GET /messages</code> · messages:read<br><code>GET /analytics?from=YYYY-MM-DD&amp;to=YYYY-MM-DD</code> · analytics:read</p><p class="hint">Send Authorization: Bearer YOUR_TOKEN. Lists accept limit (1–100) and the returned after cursor. Messages exclude notes and unsent drafts. Each token allows 60 requests per minute. This API cannot send messages or change records.</p></details></div><div class="tablewrap"><table><caption class="sr-only">Workspace API tokens</caption><thead><tr><th>Name</th><th>Scopes</th><th>Expires</th><th>Last used</th><th>Status</th><th></th></tr></thead><tbody>${tokens.length?tokens.map(t=>`<tr><td>${esc(t.name)}</td><td>${t.scopes.map(esc).join('<br>')}</td><td>${esc(date(t.expires))}</td><td>${t.last_used?esc(date(t.last_used)):'Never'}</td><td>${t.revoked?'Revoked':t.expires<=stamp?'Expired':'Active'}</td><td>${!t.revoked?btn('Revoke','api-token-revoke',`data-id="${esc(t.id)}" ${S.review?'disabled':''}`,'small ghost'):''}</td></tr>`).join(''):'<tr><td colspan="6">No API tokens yet.</td></tr>'}</tbody></table></div></section>`;
}
function apiTokenScope(){return S.data?S.workspace+':'+S.data.context.user.id:''}
function clearApiTokenSecret(){const modal=document.querySelector('#modal');if(modal?.dataset?.apiTokenSecret||modal?.querySelector?.('#api-token-name')){modal.close();modal.innerHTML='';delete modal.dataset.apiTokenSecret}}
async function apiTokenAction(action,el){
 if(action==='api-token-create'){
  const scope=apiTokenScope();
  return showModal('Generate API token',`<div class="field"><label for="api-token-name">Name</label><input id="api-token-name" name="name" maxlength="80" required placeholder="CRM integration"></div><div class="field"><label for="api-token-days">Expires after</label><select id="api-token-days" name="days"><option value="7">7 days</option><option value="30">30 days</option><option value="90" selected>90 days</option><option value="365">365 days</option></select></div><fieldset><legend>Read-only permissions</legend>${['contacts:read','messages:read','analytics:read'].map(s=>`<label class="api-token-scope"><input type="checkbox" name="scopes" value="${s}"> ${s.replace(':read','')}</label>`).join('')}</fieldset><p class="hint">Choose only what your integration needs. Save the token privately; it is shown once.</p>`,async data=>{
   if(scope!==apiTokenScope())throw new Error('Workspace changed. Open token setup again.');
   const scopes=Array.from(document.querySelectorAll('#dialog-form input[name=scopes]:checked')).map(x=>x.value);
   const form=document.querySelector('#dialog-form');
   const result=await api('/api/developer/tokens',{method:'POST',body:JSON.stringify({name:data.name,days:Number(data.days),scopes})});
   await refresh();
   const modal=document.querySelector('#modal');
   if(scope!==apiTokenScope()||!modal.open||document.querySelector('#dialog-form')!==form)return;
   modal.dataset.apiTokenSecret=scope;
   modal.innerHTML=`<div class="modalhead"><h2>Save your API token</h2>${btn('Close','close','','ghost small')}</div><div class="modalbody"><p>This is the only time it will be shown. Keep it out of screenshots and source code.</p><label for="api-token-once">API token</label><textarea id="api-token-once" readonly spellcheck="false" autocomplete="off">${esc(result.token)}</textarea><p class="hint">Password resets, MFA enrollment/removal and loss of administrator access revoke this token.</p>${btn('Done','close','','primary')}</div>`;
   modal.addEventListener('close',()=>{if(modal.dataset.apiTokenSecret){modal.innerHTML='';delete modal.dataset.apiTokenSecret}},{once:true});
  },'Generate token');
 }
 if(action==='api-token-revoke'){
  await api('/api/developer/tokens/revoke',{method:'POST',body:JSON.stringify({id:el.dataset.id})});await refresh();toast('API token revoked.');
 }
}
document.addEventListener('change',e=>{if(e.target.id==='workspace')clearApiTokenSecret()});
document.addEventListener('click',e=>{if(e.target.closest?.('[data-do=logout]'))clearApiTokenSecret()});
window.addEventListener('hashchange',clearApiTokenSecret);
