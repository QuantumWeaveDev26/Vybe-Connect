'use strict';
const primaryDestinations=[
 ['campaigns','Campaigns','campaigns','Create broadcasts and manage approved templates'],
 ['inbox','Team Inbox','inbox','Read conversations, assign teammates and reply'],
 ['contacts','Contacts','contacts','Manage contacts, tags, fields and segments'],
 ['ai-agents','AI Agents','ai-agents','Open the AI assistant and manage background agents','ai-agents-open'],
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
 const content=`${icon(glyph)}<span class="nav-text">${esc(label)}</span>`;
 return action?`<button type="button" ${attributes} data-do="${action}">${content}</button>`:`<a href="#${route}" ${attributes}>${content}</a>`;
}).join('')}
function shellSection(){if(['developers','webhooks'].includes(S.route))return 'developers';if(['campaigns','templates'].includes(S.route))return 'campaigns';if(['rules','flows','sequences','replies','customer-assistant'].includes(S.route))return 'automations';if(['contacts','segments'].includes(S.route))return 'contacts';if(['team','settings','services'].includes(S.route))return 'settings';return S.route}
function contextMenu(){const section=shellSection();let title='',items=[];if(section==='campaigns'){title='Campaigns';items=[['campaigns','Campaign Overview'],['templates','Template Messages']]}
if(section==='automations'){title='Automations';items=[['rules','Rules'],['flows','Chatbots'],['sequences','Sequences & Drip'],['replies','Reply Material'],['customer-assistant','AI Customer Replies'],['external-agents','Astra / Custom AI'],['findings','AI Agent Findings']]}
if(section==='contacts'){title='Contacts';items=[['contacts','All Contacts'],['segments','Segments & Filters']]}
if(section==='developers'){title='Developer console';items=[['developers','Get started & API'],['external-agents','API agents'],['webhooks','Webhooks & logs'],['commerce','Integrations']]}
if(section==='settings'){title='Settings';items=[['settings','WhatsApp Cloud API'],['team','Team & user management'],['services','Services & billing']]}
if(!items.length)return '';return `<aside class="context-nav" data-section="${section}"><h2>${title}</h2>${section==='campaigns'?btn('+ Create New Campaign','new-campaign','','primary'):''}${section==='automations'?'<div class="navlabel">TRIGGERS & ACTIONS LIBRARY</div>':''}${items.map(([route,label])=>`<a href="#${route}" ${S.route===route?'aria-current="page"':''} class="context-link ${S.route===route?'selected':''}">${icon(route)}<span>${label}</span></a>`).join('')}</aside>`}
function upgradeShell(){if(!S.data)return;closeConnectorMenu();applyNavigationPreference();const sidebar=$('.sidebar nav');if(!sidebar)return;const section=shellSection();sidebar.setAttribute("aria-label","Main navigation");sidebar.innerHTML=primaryNavigation();
const main=$('.main'),content=$('.content');main.querySelector('.context-nav')?.remove();const menu=contextMenu();main.classList.toggle('has-context',!!menu);if(menu)content.insertAdjacentHTML('beforebegin',menu);const aiButton=$('[data-do="ai-open"]');if(aiButton){aiButton.classList.add('header-assistant');aiButton.innerHTML=`<span>✧ VYBE Connect AI</span><span class="ai-context-label">${esc(S.route==='templates'?'Review templates and suggest improvements':S.route==='inbox'?'Find recent chats with buying intent':'Review campaign engagement and insights')}</span>`;$('.topbar').prepend(aiButton)} }

function navigationToggleMarkup(expanded){
 return btn('<b class="nav-toggle-mark" aria-hidden="true">&#9776;</b><span>Navigation</span>','nav-toggle',`aria-label="${expanded?'Collapse':'Expand'} navigation" title="${expanded?'Collapse':'Expand'} navigation" aria-expanded="${expanded}"`,'navlink ghost');
}
function applyNavigationPreference(){
 const expanded=localStorage.getItem('vybe-nav-expanded')==='true';
 document.querySelector('.shell')?.classList?.toggle('nav-expanded',expanded);
 const bottom=document.querySelector('.sidebar-bottom');
 if(bottom&&!bottom.querySelector('[data-do="nav-toggle"]'))bottom.insertAdjacentHTML('afterbegin',navigationToggleMarkup(expanded));
 if(bottom&&!bottom.querySelector('[data-do="launch-preview"]'))bottom.insertAdjacentHTML('beforeend',btn(icon('sparkles')+'<span>Opening animation</span>','launch-preview','aria-label="Replay opening animation" data-nav-label="Opening animation"','navlink ghost'));
 const button=document.querySelector('[data-do="nav-toggle"]');
 if(button){button.setAttribute('aria-expanded',String(expanded));button.setAttribute('aria-label',(expanded?'Collapse':'Expand')+' navigation');button.setAttribute('title',(expanded?'Collapse':'Expand')+' navigation')}
}
function toggleNavigation(){localStorage.setItem('vybe-nav-expanded',String(localStorage.getItem('vybe-nav-expanded')!=='true'));applyNavigationPreference()}
