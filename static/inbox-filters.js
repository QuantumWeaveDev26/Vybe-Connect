'use strict';
const INBOX_VIEW_DEFAULTS={assignment:'any',team:'',tag:'',attention:'any',window:'any',consent:'any',sort:'recent'};
let INBOX_VIEW={scope:null,expanded:false,...INBOX_VIEW_DEFAULTS};
function ensureInboxView(){
 const scope=S.data.context.tenant_id+':'+S.data.context.user.id;
 if(INBOX_VIEW.scope!==scope){INBOX_VIEW={scope,expanded:false,...INBOX_VIEW_DEFAULTS};S.filter='all';S.search=''}
 return INBOX_VIEW;
}
function inboxMessageIndex(messages){
 const index=new Map();
 for(const message of messages||[]){
  const id=message.contact;if(!id)continue;
  const row=index.get(id)||{activity:0,incoming:0,reply:0,draft:false,text:[]};
  const stamp=Number(message.ts)||0;row.text.push(String(message.body||''));
  if(message.status==='draft'){row.draft=true;index.set(id,row);continue}
  if(message.direction==='in'||message.direction==='out')row.activity=Math.max(row.activity,stamp);
  if(message.direction==='in')row.incoming=Math.max(row.incoming,stamp);
  if(message.direction==='out'&&['accepted','submitted','sent','delivered','read'].includes(message.status))row.reply=Math.max(row.reply,stamp);
  index.set(id,row);
 }
 return index;
}
function selectInboxContacts(data,options={},mainFilter='all',query='',stamp=Date.now()/1000){
 const view={...INBOX_VIEW_DEFAULTS,...options},index=inboxMessageIndex(data.messages),needle=String(query).trim().toLocaleLowerCase();
 const user=data.context.user.id,team=(data.team_operations?.teams||[]).find(t=>t.id===view.team);
 const list=(data.contacts||[]).filter(contact=>{
  if(contact.snoozed_until>stamp)return false;
  const messages=index.get(contact.id)||{activity:0,incoming:0,reply:0,draft:false,text:[]};
  if(mainFilter==='mine'&&contact.assignee!==user)return false;
  if(['open','pending','solved'].includes(mainFilter)&&contact.status!==mainFilter)return false;
  if(needle&&![contact.name,contact.phone,...(contact.tags||[]),...messages.text].join(' ').toLocaleLowerCase().includes(needle))return false;
  if(view.assignment==='unassigned'&&contact.assignee)return false;
  if(view.assignment==='mine'&&contact.assignee!==user)return false;
  if(view.assignment.startsWith('user:')&&contact.assignee!==view.assignment.slice(5))return false;
  if(view.team&&(!team||!contact.assignee||!team.members.includes(contact.assignee)))return false;
  if(view.tag==='none'&&(contact.tags||[]).length)return false;
  if(view.tag.startsWith('tag:')&&!(contact.tags||[]).includes(view.tag.slice(4)))return false;
  const inbound=Number(contact.last_real_inbound)||0,open=inbound>0&&inbound<=stamp&&stamp-inbound<86400;
  if(view.window==='open'&&!open||view.window==='closed'&&open)return false;
  if(view.consent==='yes'&&!contact.optin||view.consent==='no'&&contact.optin)return false;
  if(view.attention==='awaiting-reply'&&!(messages.incoming>0&&messages.incoming<=stamp&&messages.incoming>messages.reply&&contact.status!=='solved'))return false;
  if(view.attention==='draft'&&!messages.draft)return false;
  if(view.attention==='human'&&!contact.automation_hold||view.attention==='automation'&&contact.automation_hold)return false;
  return true;
 });
 return list.sort((a,b)=>{const left=index.get(a.id)?.activity||0,right=index.get(b.id)?.activity||0;return(view.sort==='oldest'?left-right:right-left)||String(a.name).localeCompare(String(b.name))||a.id.localeCompare(b.id)});
}
function inboxSavedViewKey(){
 return 'vybe-inbox-views:'+ensureInboxView().scope;
}
function inboxSavedViews(){
 try {
  const views=JSON.parse(workspaceStorage.getItem(inboxSavedViewKey())||'[]');
  return Array.isArray(views)?views:[];
 } catch {return []}
}
function inboxSavedViewMarkup(){
 const saved=inboxSavedViews();
 return `<div class="inbox-saved-views"><label>Saved views<select data-inbox-saved-view><option value="">Choose a view</option><option value="mine">My open chats</option><option value="unassigned">Unassigned chats</option><option value="waiting">Waiting for a reply</option>${saved.map((entry,index)=>`<option value="saved:${index}">${esc(entry.name)}</option>`).join('')}</select></label><details><summary>Save current filters</summary><form data-inbox-save-view><label>View name<input name="name" required maxlength="40"></label><button type="submit">Save view</button></form>${saved.length?`<ul>${saved.map((entry,index)=>`<li><span>${esc(entry.name)}</span><button type="button" data-inbox-delete-view="${index}" aria-label="Remove view ${esc(entry.name)}">Remove</button></li>`).join('')}</ul>`:''}<small>Custom views are saved in this browser for your account and workspace.</small></details></div>`;
}
document.addEventListener('submit',event=>{
 const form=event.target;if(!form.matches?.('[data-inbox-save-view]'))return;
 event.preventDefault();
 const name=form.elements.name.value.trim();if(!name)return;
 const view=ensureInboxView(),saved=inboxSavedViews();
 const filters=Object.fromEntries(Object.keys(INBOX_VIEW_DEFAULTS).map(key=>[key,view[key]]));
 const next={name,filters,status:S.filter};
 const existing=saved.findIndex(entry=>entry.name.toLowerCase()===name.toLowerCase());
 if(existing>=0)saved[existing]=next;else {if(saved.length>=12)return toast('Remove a saved view before adding another.');saved.push(next)}
 workspaceStorage.setItem(inboxSavedViewKey(),JSON.stringify(saved));render();document.querySelector('[data-inbox-saved-view]')?.focus();
});
document.addEventListener('change',event=>{
 if(!event.target.matches?.('[data-inbox-saved-view]'))return;
 const value=event.target.value;
 const presets={mine:{filters:{assignment:'mine'},status:'open'},unassigned:{filters:{assignment:'unassigned'},status:'open'},waiting:{filters:{attention:'awaiting-reply'},status:'all'}};
 const selection=value.startsWith('saved:')?inboxSavedViews()[Number(value.slice(6))]:presets[value];
 if(!selection)return;
 const scope=ensureInboxView().scope;
 INBOX_VIEW={...INBOX_VIEW_DEFAULTS,...selection.filters,scope,expanded:true};
 S.filter=selection.status;S.search='';S.mobileChatOpen=false;
 render();document.querySelector('[data-inbox-saved-view]')?.focus();
});
document.addEventListener('click',event=>{
 const control=event.target.closest?.('[data-inbox-delete-view]');if(!control)return;
 const saved=inboxSavedViews();saved.splice(Number(control.dataset.inboxDeleteView),1);
 workspaceStorage.setItem(inboxSavedViewKey(),JSON.stringify(saved));render();document.querySelector('[data-inbox-saved-view]')?.focus();
});
function inboxAdvancedFilters(list,total){
 const view=ensureInboxView(),active=Object.keys(INBOX_VIEW_DEFAULTS).filter(k=>view[k]!==INBOX_VIEW_DEFAULTS[k]).length;
 const select=(key,label,options)=>`<label>${label}<select data-inbox-field="${key}" aria-label="${label}">${options.map(([value,text])=>`<option value="${esc(value)}" ${view[key]===value?'selected':''}>${esc(text)}</option>`).join('')}</select></label>`;
 const tags=[...new Set((S.data.contacts||[]).flatMap(c=>c.tags||[]))].sort();
 return `<details class="inbox-advanced" ${view.expanded?'open':''}><summary>Filters & sort${active?` <span>${active}</span>`:''}</summary><div class="inbox-filter-fields">${select('assignment','Assigned to',[['any','Anyone'],['unassigned','Unassigned'],['mine','Me'],...(S.data.members||[]).map(m=>['user:'+m.id,m.name])])}${select('team','Agent team',[['','All teams'],...(S.data.team_operations?.teams||[]).filter(t=>t.enabled!==false).map(t=>[t.id,t.name])])}${select('tag','Contact tag',[['','All tags'],['none','No tags'],...tags.map(t=>['tag:'+t,t])])}${select('attention','Attention',[['any','All conversations'],['awaiting-reply','Awaiting reply'],['draft','Has a draft'],['human','Human handling'],['automation','Automation available']])}${select('window','24-hour service window',[['any','Any window'],['open','Open'],['closed','Closed']])}${select('consent','Marketing consent',[['any','Any consent'],['yes','Opted in'],['no','No consent']])}${select('sort','Conversation order',[['recent','Recent activity first'],['oldest','Oldest activity first']])}<button type="button" data-inbox-reset>Reset filters</button></div></details><p class="inbox-filter-count" role="status" aria-live="polite">${list.length} of ${total} conversations</p>`;
}
function inboxSelectionNote(list,id){return id&&!list.some(c=>c.id===id)?'<div class="inbox-selection-note">This conversation is outside your filters. <button type="button" data-inbox-reset>Clear filters</button></div>':''}
document.addEventListener('change',event=>{
 const key=event.target.dataset?.inboxField;if(!key||!Object.hasOwn(INBOX_VIEW_DEFAULTS,key))return;
 ensureInboxView();INBOX_VIEW[key]=event.target.value;INBOX_VIEW.expanded=true;render();document.querySelector(`[data-inbox-field="${key}"]`)?.focus();
});
document.addEventListener('click',event=>{if(!event.target.closest?.('[data-inbox-reset]'))return;ensureInboxView();INBOX_VIEW={scope:INBOX_VIEW.scope,expanded:true,...INBOX_VIEW_DEFAULTS};S.filter='all';S.search='';render()});
document.addEventListener('toggle',event=>{if(event.target.matches?.('.inbox-advanced'))INBOX_VIEW.expanded=event.target.open},true);

function inboxQueueNavigation(){
 const view=ensureInboxView(),base={...view,assignment:'any',team:''};
 const count=assignment=>selectInboxContacts(S.data,{...base,assignment},S.filter==='mine'?'all':S.filter,S.search).length;
 const teamCount=teamId=>selectInboxContacts(S.data,{...base,team:teamId},S.filter==='mine'?'all':S.filter,S.search).length;
 const teams=(S.data.team_operations?.teams||[]).filter(t=>t.enabled!==false).slice(0,4);
 return '<details class="inbox-queues-group" open><summary class="inbox-queues-summary"><span>Conversations</span></summary><nav class="inbox-queues" aria-label="Conversation queues"><h2>Conversations</h2>'+[['unassigned','Unassigned'],['mine','Assigned to me'],['any','All']].map(([value,label])=>`<button type="button" data-inbox-queue="${value}" aria-pressed="${view.assignment===value&&!view.team}">${icon(value==='any'?'inbox':'contacts')}<span>${label}</span><small>${count(value)}</small></button>`).join('')+teams.map(t=>`<button type="button" data-inbox-team="${esc(t.id)}" aria-pressed="${view.team===t.id}"><span class="queue-hash" aria-hidden="true">#</span><span>${esc(t.name)}</span><small>${teamCount(t.id)}</small></button>`).join('')+'</nav></details>';
}
function selectInboxQueue(value){
 if(!['any','unassigned','mine'].includes(value))return;
 const view=ensureInboxView();
 view.assignment=value;
 view.team='';
 if(S.filter==='mine')S.filter='all';
 S.mobileChatOpen=false;
 render();
}
function selectInboxTeamQueue(teamId){
 const view=ensureInboxView();
 view.team=view.team===teamId?'':String(teamId||'');
 view.assignment='any';
 if(S.filter==='mine')S.filter='all';
 S.mobileChatOpen=false;
 render();
}
document.addEventListener('click',event=>{
 const control=event.target.closest?.('[data-inbox-queue]');
 if(control){selectInboxQueue(control.dataset.inboxQueue);return}
 const teamBtn=event.target.closest?.('[data-inbox-team]');
 if(teamBtn)selectInboxTeamQueue(teamBtn.dataset.inboxTeam);
});
