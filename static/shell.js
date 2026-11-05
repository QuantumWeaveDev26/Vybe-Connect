'use strict';
let mobileNavigationOpen=false;
const primaryDestinations=[
 ['campaigns','Campaigns','campaigns','Create broadcasts and manage approved templates'],
 ['inbox','Team Inbox','inbox','Read conversations, assign teammates and reply'],
 ['contacts','Contacts','contacts','Manage contacts, tags, fields and segments'],
 ['ai-agents','AI Agents','ai-agents','Open the AI assistant and manage background agents'],
 ['external-agents','Astra / Custom AI','astra','Connect external agents and review their drafts'],
 ['rules','Automations','rules','Build rules, chatbots, sequences and customer AI replies'],
 ['pipeline','Sales Pipeline','pipeline','Track deals, stages and follow-up tasks'],
 ['findings','AI Findings','findings','Review agent findings and proposed actions'],
 ['commerce','Commerce & Integrations','commerce','Manage connected services, products and orders'],
 ['analytics','Analytics','analytics','Review team activity and messaging reports'],
 ['developers','Connectors','developers','Open API, integrations and webhook delivery'],
 ['settings','Settings','settings','Configure WhatsApp and workspace access'],
 ['roadmap','Parity Status','roadmap','See implemented features and remaining release gaps']
];
function primaryNavigation(){const section=shellSection();return primaryDestinations.map(([route,label,glyph,description,action])=>{
 const selected=(route==='rules'?'automations':route)===section;
 const connector=route==='developers'?' data-connectors-trigger aria-expanded="false" aria-controls="connector-popover"':'';
 const attributes=`${connector} class="navlink${selected?' active':''}" ${selected?'aria-current="page" ':''}aria-label="${esc(label)}: ${esc(description)}" data-nav-label="${esc(label)}"`;
 const shortLabel={"Commerce & Integrations":"Commerce","Astra / Custom AI":"Custom AI","Sales Pipeline":"CRM & pipeline","Parity Status":"Release status"}[label]||label;
 const content=`<span class="rail-glyph" aria-hidden="true">${icon(glyph)}</span><span class="nav-text">${esc(shortLabel)}</span>`;
 return action?`<button type="button" ${attributes} data-do="${action}">${content}</button>`:`<a href="#${route}" ${attributes}>${content}</a>`;
}).join('')}
function shellSection(){if(['developers','webhooks'].includes(S.route))return 'developers';if(['campaigns','templates'].includes(S.route))return 'campaigns';if(['rules','flows','sequences','replies','customer-assistant'].includes(S.route))return 'automations';if(['contacts','segments'].includes(S.route))return 'contacts';if(['team','settings','services'].includes(S.route))return 'settings';return S.route}
function contextMenu(){const section=shellSection();let title='',items=[];if(section==='campaigns'){title='Campaigns';items=[['campaigns','Campaign Overview'],['templates','Template Messages']]}
if(section==='automations'){title='Automations';items=[['rules','Rules'],['flows','Chatbots'],['sequences','Sequences & Drip'],['replies','Reply Material'],['customer-assistant','AI Customer Replies'],['external-agents','Astra / Custom AI'],['findings','AI Agent Findings']]}
if(section==='contacts'){title='Contacts';items=[['contacts','All Contacts'],['segments','Segments & Filters']]}
if(section==='developers'){title='Developer console';items=[['developers','Get started & API'],['external-agents','API agents'],['webhooks','Webhooks & logs'],['commerce','Integrations']]}
if(section==='settings'){title='Settings';items=[['settings','WhatsApp Cloud API'],['team','Team & user management'],['services','Services & billing']]}
if(!items.length)return '';return `<aside class="context-nav" data-section="${section}"><h2>${title}</h2>${section==='campaigns'?btn('+ Create New Campaign','new-campaign','','primary'):''}${section==='automations'?'<div class="navlabel">TRIGGERS & ACTIONS LIBRARY</div>':''}${items.map(([route,label])=>`<a href="#${route}" ${S.route===route?'aria-current="page"':''} class="context-link ${S.route===route?'selected':''}">${icon(route)}<span>${label}</span></a>`).join('')}</aside>`}
function workspaceSearchEntries(query){
 const q=String(query||'').trim().toLocaleLowerCase();if(!q)return [];
 const routes=Object.entries(names).filter(([route,label])=>(route+' '+label).toLocaleLowerCase().includes(q)).map(([route,label])=>({route,label,kind:'Page'}));
 const contacts=(S.data?.contacts||[]).filter(c=>(c.name+' '+c.phone).toLocaleLowerCase().includes(q)).slice(0,6).map(c=>({id:c.id,label:c.name,kind:'Contact'}));
 const agents=(S.data?.aiagents||[]).filter(a=>!a.archived&&String(a.name).toLocaleLowerCase().includes(q)).slice(0,4).map(a=>({agentId:a.id,label:a.name,kind:'Agent'}));
 return [...routes,...contacts,...agents].slice(0,10);
}
function renderWorkspaceSearch(query){
 const box=document.querySelector('#workspace-search-results');if(!box)return;
 const items=workspaceSearchEntries(query);box.hidden=!query.trim();
 box.innerHTML=items.map(item=>item.agentId?`<button type="button" data-do="ai-open-agent" data-id="${esc(item.agentId)}"><span>${esc(item.label)}</span><small>Agent</small></button>`:item.id?`<button type="button" data-do="open-chat" data-id="${esc(item.id)}"><span>${esc(item.label)}</span><small>${item.kind}</small></button>`:`<a href="#${esc(item.route)}"><span>${esc(item.label)}</span><small>${item.kind}</small></a>`).join('')||'<p>No matches in this workspace.</p>';
}
function headerAccountMarkup(){
 const user=S.data.context.user,unread=(S.data.mention_notifications||[]).filter(n=>!n.read).length;
 return `<div class="header-account"><button type="button" class="header-bell" data-do="team-mentions" aria-label="${unread} unread notification${unread===1?'':'s'}" title="Mention notifications"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>${unread?'<i class="notification-dot"></i>':''}</button><div class="header-account-divider"></div><button type="button" id="header-profile-toggle" class="header-profile-toggle" aria-label="Open account menu" aria-expanded="false" aria-controls="header-profile-menu"><span class="header-user-avatar" aria-hidden="true">${esc(initials(user.name))}</span><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg></button><div id="header-profile-menu" class="header-profile-menu" hidden><div class="header-profile-info"><strong>${esc(user.name)}</strong><small>${esc(user.email||'')}</small></div><button type="button" data-do="account-profile">Your profile</button><button type="button" data-do="ai-open">Ask VYBE Connect AI</button><button type="button" data-do="account-security">Security</button><button type="button" data-do="refresh">Refresh workspace</button><button type="button" data-do="logout">Sign out</button></div></div>`;
}
function closeHeaderProfile(restoreFocus=false){
 const menu=document.querySelector('#header-profile-menu'),toggle=document.querySelector('#header-profile-toggle');
 if(menu)menu.hidden=true;if(toggle)toggle.setAttribute('aria-expanded','false');if(restoreFocus)toggle?.focus();
}
function installConceptHeader(){
 const bar=document.querySelector('.topbar');if(!bar||bar.querySelector('.header-brand'))return;
 bar.insertAdjacentHTML('afterbegin','<a class="header-brand" href="#campaigns" aria-label="VYBE Connect home"><span class="header-brand-v" aria-hidden="true">V</span><span>VYBE Connect</span></a><button type="button" class="header-mobile-menu ghost" data-do="nav-toggle" aria-label="Toggle navigation">☰</button>');
 const picker=bar.querySelector('.buttons');picker?.classList.add('header-workspace');
 picker?.insertAdjacentHTML('afterbegin','<span class="workspace-symbol" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 21V3h12v18M16 8h5v13H3M8 7h1m3 0h1M8 11h1m3 0h1M8 15h1m3 0h1M9 21v-3h3v3"/></svg></span>');
 picker?.insertAdjacentHTML('afterend',`<div class="workspace-search"><label for="workspace-search" class="sr-only">Search workspace</label>${icon('search')}<input id="workspace-search" type="search" autocomplete="off" placeholder="Search conversations, contacts, agents…" aria-controls="workspace-search-results"><div id="workspace-search-results" class="workspace-search-results" hidden></div></div><a class="header-whatsapp" href="#settings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M20 11.5a8.5 8.5 0 0 1-12 7.8L3 21l1.7-5a8.5 8.5 0 1 1 15.3-4.5Z"/><path d="m8 7 2 3-1 1q1.5 3 4 3l1-1 3 2q-1 3-4 2-6-2-7-7 0-2 2-3Z" stroke-width="1.2"/></svg><span>${S.data.meta?.configured?'WhatsApp settings':'Connect WhatsApp'}</span></a>`);
 const right=bar.querySelector('.topright');if(right){right.classList.add('header-account-host');right.innerHTML=headerAccountMarkup();}
 const search=bar.querySelector('#workspace-search');if(search)search.oninput=()=>renderWorkspaceSearch(search.value);
 const toggle=bar.querySelector('#header-profile-toggle');if(toggle)toggle.onclick=event=>{event.stopPropagation();const menu=bar.querySelector('#header-profile-menu');menu.hidden=!menu.hidden;toggle.setAttribute('aria-expanded',String(!menu.hidden));if(!menu.hidden)menu.querySelector('button')?.focus()};
}
function upgradeShell(){if(!S.data)return;installConceptHeader();closeConnectorMenu();applyNavigationPreference();const sidebar=$('.sidebar nav');if(!sidebar)return;const section=shellSection();sidebar.setAttribute("aria-label","Main navigation");sidebar.innerHTML=primaryNavigation();
const main=$('.main'),content=$('.content');main.querySelector('.context-nav')?.remove();const menu=contextMenu();main.classList.toggle('has-context',!!menu);if(menu)content.insertAdjacentHTML('beforebegin',menu); }

function navigationToggleMarkup(expanded){
 return btn('<b class="nav-toggle-mark" aria-hidden="true">&#9776;</b><span>Navigation</span>','nav-toggle',`aria-label="${expanded?'Collapse':'Expand'} navigation" title="${expanded?'Collapse':'Expand'} navigation" aria-expanded="${expanded}"`,'navlink ghost');
}
function applyNavigationPreference(){
 const preference=localStorage.getItem('vybe-nav-expanded');const narrow=typeof innerWidth!=='undefined'&&innerWidth<=1050;const expanded=narrow?mobileNavigationOpen:preference!=='false';
 document.querySelector('.shell')?.classList?.toggle('nav-expanded',expanded);
 const bottom=document.querySelector('.sidebar-bottom');
 if(bottom&&!bottom.querySelector('[data-do="nav-toggle"]'))bottom.insertAdjacentHTML('afterbegin',navigationToggleMarkup(expanded));
 if(bottom&&!bottom.querySelector('[data-do="launch-preview"]'))bottom.insertAdjacentHTML('beforeend',btn(icon('sparkles')+'<span>Opening animation</span>','launch-preview','aria-label="Replay opening animation" data-nav-label="Opening animation"','navlink ghost'));
 const button=document.querySelector('[data-do="nav-toggle"]');
 if(button){button.setAttribute('aria-expanded',String(expanded));button.setAttribute('aria-label',(expanded?'Collapse':'Expand')+' navigation');button.setAttribute('title',(expanded?'Collapse':'Expand')+' navigation')}
}
function toggleNavigation(){if(typeof innerWidth!=='undefined'&&innerWidth<=1050)mobileNavigationOpen=!mobileNavigationOpen;else localStorage.setItem('vybe-nav-expanded',String(!document.querySelector('.shell')?.classList.contains('nav-expanded')));applyNavigationPreference()}

if(typeof document!=='undefined'){
document.addEventListener('click',event=>{if(!mobileNavigationOpen)return;if(event.target.closest?.('.sidebar .navlink')||(!event.target.closest?.('.sidebar')&&!event.target.closest?.('[data-do="nav-toggle"]'))){mobileNavigationOpen=false;applyNavigationPreference()}});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&mobileNavigationOpen){mobileNavigationOpen=false;applyNavigationPreference()}});

document.addEventListener('keydown',event=>{if(event.key==='Escape'){closeHeaderProfile();const box=document.querySelector('#workspace-search-results');if(box)box.hidden=true}});
document.addEventListener('click',event=>{if(!event.target.closest?.('#header-profile-toggle'))closeHeaderProfile();if(!event.target.closest?.('.workspace-search')){const box=document.querySelector('#workspace-search-results');if(box)box.hidden=true}});

}
