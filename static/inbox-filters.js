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
