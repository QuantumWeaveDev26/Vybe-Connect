'use strict';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths={services:'M3 5h18v14H3z M3 9h18 M6 15h4',astra:'M12 2l9 5v10l-9 5-9-5V7z M3 7l9 5 9-5 M12 12v10 M7 5l10 5','ai-agents':'M5 7h14v13H5z M9 11h.01 M15 11h.01 M9 16h6 M12 3v4 M2 11v5 M22 11v5','external-agents':'M8 8H3V3 M3 8l6-6 M16 16h5v5 M21 16l-6 6 M8 16h8V8H8z',pipeline:'M3 4h5v16H3z M10 4h5v10h-5z M17 4h5v6h-5z',commerce:'M3 8h18l-2-5H5z M4 8v13h16V8 M9 21v-8h6v8',developers:'M8 6l-6 6 6 6 M16 6l6 6-6 6 M14 3l-4 18',campaigns:'M3 11l17-7v16L3 13z M7 14l2 7h3l-1-6',inbox:'M4 4h16v15H4z M4 12h5l2 3h2l2-3h5',contacts:'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M2 21v-3a6 6 0 0 1 12 0v3 M17 4a4 4 0 0 1 0 8 M18 15a5 5 0 0 1 4 5',templates:'M5 3h11l4 4v14H5z M15 3v5h5 M9 12h7 M9 16h7',rules:'M5 12h5 M14 5v14 M10 12l4-7 M10 12l4 7 M14 5h5 M14 19h5 M2 10h3v4H2z M19 3h3v4h-3z M19 17h3v4h-3z',flows:'M2 3h7v5H2z M15 16h7v5h-7z M2 16h7v5H2z M5 8v8 M5 12h13v4',analytics:'M4 20h17 M7 16V9 M12 16V4 M17 16v-5',team:'M8 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6 M2 20v-2a6 6 0 0 1 12 0v2 M16 4a3 3 0 0 1 0 6 M17 14a4 4 0 0 1 4 4v2',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M9 3h6l1 4 4 1 1 6-4 2-1 4H9l-1-4-4-1-1-6 4-2z',replies:'M3 4h18v13H9l-5 4v-4H3z M7 9h10 M7 12h6',sequences:'M4 4h16v4H4z M4 11h16v4H4z M4 18h16v4H4z',roadmap:'M4 21V3l15 4-15 4',plus:'M12 4v16 M4 12h16',check:'M4 12l5 5L20 6',arrow:'M5 12h14 M14 7l5 5-5 5',clock:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 7v5l3 2',search:'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6',logout:'M9 4H4v16h5 M9 12h12 M16 7l5 5-5 5',calendar:'M4 5h16v16H4z M4 10h16 M8 3v4 M16 3v4'};

Object.assign(paths,{recipes:'M4 3h6v6H4z M14 15h6v6h-6z M7 9v9h7 M14 6h6 M17 3v6','support-tools':'M4 13v-2a8 8 0 0 1 16 0v2 M4 12H2v6h4v-6z M18 12h4v6h-4z M18 18v3h-6',branches:'M12 3v6 M4 15v6 M20 15v6 M4 15h16V9H4z M9 3h6','help-centre':'M3 4h7l2 2 2-2h7v16h-7l-2 2-2-2H3z M12 6v16',attribution:'M3 20h18 M6 16l5-6 4 2 5-8 M16 4h4v4','whatsapp-forms':'M5 3h14v18H5z M8 7h8 M8 11h2 M13 11h3 M8 15h2 M13 15h3',security:'M12 2l8 3v6c0 6-8 11-8 11S4 17 4 11V5z M8 11l3 3 5-6',password:'M8 10V7a4 4 0 0 1 8 0v3 M5 10h14v12H5z M12 14v4',webhooks:'M6 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6 M18 14a3 3 0 1 0 0 6 3 3 0 0 0 0-6 M6 10v7h9 M9 7h9v7',segments:'M4 4h16 M7 10h10 M10 16h4 M12 16v5','customer-assistant':'M5 7h14v13H5z M9 11h.01 M15 11h.01 M9 16h6 M12 3v4',findings:'M5 3h14v18H5z M8 8l1 1 2-2 M13 8h3 M8 14l1 1 2-2 M13 14h3',sparkles:'M12 2l2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5z',commerce:'M3 3h2l3 12h11l3-9H6 M9 20h.01 M18 20h.01'});
const icon=n=>`<span class="icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[n]||paths.inbox}"/></svg></span>`;
const badge=(text,kind='')=>`<span class="badge ${kind}">${esc(text)}</span>`;
const initials=n=>esc((n||'?').split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase());
const btn=(text,action,extra='',cls='')=>`<button type="button" class="${cls}" data-do="${action}" ${extra}>${text}</button>`;
const empty=(title,body,action)=>`<div class="empty">${icon('inbox')}<h3>${esc(title)}</h3><p>${esc(body)}</p>${action||''}</div>`;
const tags=list=>(list||[]).map(t=>`<span class="tag ${t==='Priority'?'vip':''}">${esc(t)}</span>`).join('');
const date=t=>new Date(t*1000).toLocaleDateString(undefined,{month:'short',day:'numeric'});
const clock=t=>new Date(t*1000).toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'});
const names={'working-hours':'Working hours & SLA','google-connections':'Google connections','semantic-knowledge':'Semantic knowledge',recipes:'Integration recipes','support-tools':'Support tools',branches:'Branches',attribution:'Lead attribution','help-centre':'Help centre','whatsapp-forms':'WhatsApp forms','ai-agents':'AI Agents',webhooks:'Webhooks',services:'Services & billing','customer-assistant':'Customer support AI',segments:'Contact segments','external-agents':'Custom AI Agents',developers:'Developers',commerce:'Commerce & Integrations',pipeline:'Sales Pipeline',findings:'AI Findings',campaigns:'Campaigns',inbox:'Team Inbox',contacts:'Contacts',templates:'Template Messages',rules:'Rules',flows:'Chatbot Builder',sequences:'Sequences & Drip',replies:'Reply Material',analytics:'Analytics',team:'Team & Workspaces',settings:'Meta Connection',roadmap:'Feature Roadmap'};
const S={review:false,reviewAvailable:false,passwordRecoveryAvailable:false,signupAvailable:false,data:null,initialized:true,setupTokenRequired:false,deployment:'local',workspace:localStorage.getItem('tw_workspace')||'',route:location.hash.startsWith('#invite=')?'inbox':location.hash.slice(1)||'campaigns',chat:null,search:'',filter:'all',campaignView:'list',preview:null,draft:'',mode:'reply'};
let formSubmit=null,toastTimer;
function toast(message){$('#toast').textContent=message;$('#toast').style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').style.display='none',6000)}
async function api(path,options={}){if(S.review&&path.startsWith('/api/')){const name=path.split('?')[0];if((options.method||'GET')!=='GET'||!['/api/state','/api/analytics','/api/chat-source','/api/knowledge-source','/api/export'].includes(name))throw new Error('Live review is read-only. Complete owner setup to save changes or connect providers.');path='/api/review/'+path.slice(5)}const r=await fetch(path,{...options,headers:{'Content-Type':'application/json',...(S.workspace?{'X-Workspace':S.workspace}:{}),...(options.headers||{})}});let data;try{data=await r.json()}catch(error){if(options.signal?.aborted)throw options.signal.reason||error;const e=new Error([502,503,504].includes(r.status)?'The service is restarting. Try again in a moment.':'The server returned an unreadable response. Refresh and try again.');e.status=r.status;throw e}if(!r.ok){const e=new Error(data.error||'Request failed');e.status=r.status;throw e}return data}
async function refresh({starting=false, signal}={}) {
  try {
    const next=await api('/api/state',{signal});
    const changed=JSON.stringify(next)!==JSON.stringify(S.data);
    S.data=next;
    S.workspace=next.context.tenant_id;
    localStorage.setItem('tw_workspace',S.workspace);
    if (starting||changed) render();
    return true;
  } catch (error) {
    if (error.status===401) {
      S.data=null;
      if (S.reviewAvailable&&location.pathname!=='/owner') await openPublicReview();
      else renderAuth();
    } else if (error.status===403) {
      const hadWorkspace=!!S.workspace;
      S.data=null;
      S.workspace='';
      clearAnalyticsReport();
      localStorage.removeItem('tw_workspace');
      $('#workspace-ai')?.remove();
      if (hadWorkspace) return refresh({starting,signal});
      renderAuth();
      toast('Workspace access is unavailable. Sign in with an authorized account.');
    } else if (starting) {
      throw error;
    } else {
      toast(error.message);
    }
    return false;
  }
}
async function act(action,data){return api('/api/action',{method:'POST',body:JSON.stringify({action,data})})}
function pagehead(title,description,buttons=''){return `<div class="pagehead"><div><h1>${title}</h1><p>${description}</p></div><div class="buttons">${buttons}</div></div>`}
function tabs(items){return `<div class="tabs">${items.map(([route,label])=>`<a href="#${route}" class="${S.route===route?'active':''}">${label}</a>`).join('')}</div>`}
function campaignTabs(){return tabs([['campaigns','Campaign overview'],['templates','Your templates']])}
function automationTabs(){return tabs([['rules','Rules'],['flows','Chatbots'],['sequences','Sequences & drip'],['replies','Reply material']])}
function stat(label,value,caption,ico){const art=metricIllustration(label);return `<div class="stat${art?' stat-featured':''}"><div class="stat-top"><span>${label}</span>${art?'':`<span class="stat-icon">${icon(ico)}</span>`}</div><strong>${value}</strong><small>${caption}</small>${art}</div>`}
function renderAuth(signup=false){if(typeof clearGrowthDialogIfScopeChanged==='function')clearGrowthDialogIfScopeChanged();clearApiTokenSecret();clearAIConnectionDialog();stopVoiceLocal();clearClientInvitationIfScopeChanged();clearHelpWidget();clearPasswordRecovery();clearAnalyticsReport();closeConnectorMenu();$('#workspace-ai')?.remove();renderAccountEntry(!S.initialized,signup&&S.signupAvailable)}
function render(){if(typeof clearGrowthDialogIfScopeChanged==='function')clearGrowthDialogIfScopeChanged();clearAIConnectionDialog();checkVoiceScope();if(!S.data)return renderAuth();if(!names[S.route])S.route='campaigns';const ctx=S.data.context;$('#app').innerHTML=`<div class="shell"><aside class="sidebar"><a href="#campaigns" class="brand"><span class="brandmark" aria-hidden="true"><svg viewBox="0 0 140 140" width="25" height="25"><path d="M18 24h29l23 66 23-66h29L83 118H57Z" fill="currentColor"/></svg></span><span class="brandname">VYBE Connect</span></a><nav>${['campaigns','inbox','contacts','templates'].map(n=>nav(n)).join('')}<div class="navlabel">AUTOMATION</div>${['rules','flows','sequences','replies'].map(n=>nav(n)).join('')}<div class="navlabel">WORKSPACE</div>${['analytics','team','settings','roadmap'].map(n=>nav(n)).join('')}</nav><div class="sidebar-bottom"><div class="pilot"><strong>Your business. Your platform.</strong><br>${S.deployment==='hosted'?'Hosted workspace':'Local workspace'}<br>${S.data.meta.configured?'Meta settings configured':'Meta setup needed'}</div>${mentionNavigationButton()}<button class="navlink ghost" data-do="account-security" title="Account security: authenticator MFA and recovery codes" aria-label="Account security">${icon('security')}<span>Security</span></button><button class="navlink ghost" data-do="account-password" title="Change account password" aria-label="Change account password">${icon('password')}<span>Password</span></button><button class="navlink ghost" data-do="logout" title="Sign out of this account" aria-label="Sign out">${icon('logout')}<span>Sign out</span></button></div></aside><main class="main"><header class="topbar"><div class="buttons"><span class="muted">⌂</span><select class="workselect" id="workspace" aria-label="Business workspace">${ctx.workspaces.map(w=>`<option value="${w.id}" ${w.id===S.workspace?'selected':''}>${esc(w.name)}</option>`).join('')}</select></div><div class="topright">${badge(S.data.meta.live?'Live send enabled':S.data.sandbox?'Sandbox':S.data.meta.configured?'Meta configured · sending off':'Meta setup needed',S.data.meta.live?'amber':'')}${btn('✧ VYBE Connect AI','ai-open','','small')}${btn('Refresh','refresh','','ghost small')}<button type="button" class="avatar profile-trigger" data-do="account-profile" aria-label="Open your profile" title="Your profile">${initials(ctx.user.name)}</button></div></header><div class="content">${page()}<div class="footerline">VYBE Connect · ${S.deployment==='hosted'?'Hosted workspace':'Local workspace'} · ${esc(ctx.workspace.name)} · ${S.review?'read-only review':esc(ctx.role)+' access'}</div></div></main></div>`;$('#workspace').onchange=async e=>{S.workspace=e.target.value;S.chat=null;S.draft='';await refresh()};if(S.route==='inbox'){const m=$('.messages');if(m)m.scrollTop=m.scrollHeight}upgradeShell();renderPublicReviewNotice();filterAgentDirectory('external');filterAgentDirectory('ai');renderHelpWidget();if($('#workspace-ai'))renderAI()}
function nav(n){return `<a class="navlink ${S.route===n?'active':''}" href="#${n}" title="${names[n]}">${icon(n)}<span>${n==='settings'?'Meta connection':names[n]}</span></a>`}
function page(){return ({'working-hours':workingHoursPage,'google-connections':googleConnectionsPage,'semantic-knowledge':semanticKnowledgePage,recipes:recipesPage,'support-tools':supportToolsPage,branches:branchesPage,attribution:attributionPage,'help-centre':helpCentrePage,'whatsapp-forms':whatsappFormsPage,'ai-agents':agentWorkspacePage,webhooks:webhooksPage,services:servicesPage,'customer-assistant':customerAssistantPage,segments:segmentsPage,'external-agents':externalAgentPage,developers:developerPage,commerce:commercePage,pipeline:pipelinePage,findings:findingsPage,campaigns:campaignPage,inbox:inboxPage,contacts:contactsPage,templates:templatePage,rules:()=>automationPage('rule'),flows:flowPage,sequences:sequencePage,replies:repliesPage,analytics:analyticsPage,team:teamPage,settings:settingsPage,roadmap:roadmapPage}[S.route])()}
function trend(){const days=Array.from({length:7},(_,i)=>{const d=new Date();d.setDate(d.getDate()-6+i);return d});const counts=days.map(d=>{const a=S.data.messages.filter(m=>new Date(m.ts*1000).toDateString()===d.toDateString()&&m.direction!=='note');return [a.filter(m=>m.direction==='out').length,a.filter(m=>m.direction==='in').length]});const max=Math.max(1,...counts.flat());return `<div class="chart">${counts.map(c=>`<div class="chartcol"><div class="bar" style="height:${Math.max(2,c[0]/max*95)}%" title="${c[0]} outbound"></div><div class="bar light" style="height:${Math.max(2,c[1]/max*95)}%" title="${c[1]} inbound"></div></div>`).join('')}</div><div class="chartlabels">${days.map(d=>`<span>${d.toLocaleDateString(undefined,{weekday:'short'})}</span>`).join('')}</div>`}
function campaignPageBase(){const d=S.data;const all=d.messages.filter(m=>m.direction==='out'&&m.status!=='draft');return pagehead('Campaign overview','Send approved WhatsApp campaigns.',btn('+ Create campaign','new-campaign','','primary'))+campaignTabs()+`<div class="notice">${icon('check')}<span><strong>${d.meta.live?'Live sending is enabled.':d.meta.configured?'Sending is off.':'Connect WhatsApp to send campaigns.'}</strong> ${d.meta.live?'Send only to opted-in contacts.':'Review your WhatsApp connection in Settings.'}</span>${d.sandbox&&!d.contacts.length?btn('Load sandbox samples','seed','','small'):''}</div><div class="stats">${stat('Total contacts',d.contacts.length,'Across this business workspace','contacts')}${stat('Campaigns',d.campaigns.length,'Saved campaign records','campaigns')}${stat('Queued messages',(d.queue||[]).filter(m=>m.status==='queued').length,'Persistent outbound queue','inbox')}${stat('Opted-in audience',d.contacts.filter(c=>c.optin).length,'Eligible campaign recipients','check')}</div><div class="grid2"><section class="card"><div class="cardhead"><div><h2>Message activity</h2><p class="sub">Last 7 days · recorded workspace activity</p></div><div class="legend"><span><i class="dot"></i>Outbound</span><span><i class="dot light"></i>Inbound</span></div></div><div class="cardbody">${trend()}</div></section><section class="card"><div class="cardhead"><h2>Delivery overview</h2>${badge('Provider evidence only','gray')}</div><div class="cardbody">${['accepted','delivered','read','failed'].map(status=>`<div class="summaryrow"><span class="muted">${status[0].toUpperCase()+status.slice(1)}</span><strong>${all.filter(m=>m.status===status).length}</strong></div>`).join('')}</div></section></div><section class="card"><div class="cardhead"><div><h2>Campaign planner</h2><p class="sub">Schedules use your selected local time, stored with a timezone offset</p></div><div class="buttons">${btn('List','campaign-view','data-view="list"','small')}${btn('Calendar','campaign-view','data-view="calendar"','small')}</div></div>${S.campaignView==='calendar'?calendar():campaignTable()}</section>`}
function campaignLaunchBlock(c){if(S.review)return 'Sign in to manage campaigns.';if(S.data.sandbox)return '';if(!S.data.meta.live)return 'Connect WhatsApp and enable sending first.';const t=S.data.templates.find(t=>t.id===c.template_id);return t?.status==='APPROVED'&&t.meta_id?'':'Wait for Meta template approval.'}
function campaignTable(){return S.data.campaigns.length?`<div class="tablewrap"><table><thead><tr><th>Campaign name</th><th>Audience</th><th>Status</th><th>Schedule</th><th>Actions</th></tr></thead><tbody>${S.data.campaigns.map(c=>`<tr><td><strong>${esc(c.name)}</strong><div class="sub">${esc(S.data.templates.find(t=>t.id===c.template_id)?.name||'Template')}</div></td><td>${c.audience} contacts ${c.tag?tags([c.tag]):''}</td><td>${badge(c.status==='draft'?'Draft':c.status==='demo_complete'?'Sandbox complete':c.status,c.status==='draft'?'amber':'')}</td><td>${c.schedule?esc(c.schedule.replace('T',' ')):'Not scheduled'}</td><td>${c.status==='draft'?btn(S.data.sandbox?'Run sandbox':'Launch campaign','run-campaign',`data-id="${c.id}" ${campaignLaunchBlock(c)?`disabled title="${esc(campaignLaunchBlock(c))}"`:``}`,'small'):(badge(c.mode==='live'?'Live campaign':c.simulated+' simulated','gray')+(c.status==='queued'?btn('Cancel queued','cancel-campaign',`data-id="${c.id}"`,'small'):''))}</td></tr>`).join('')}</tbody></table></div>`:empty('Your first campaign starts here','Create a template, choose an opted-in audience, and preview a campaign.',btn('Create campaign','new-campaign','','primary small'))}
function calendar(){const today=new Date(),start=new Date(today.getFullYear(),today.getMonth(),1),offset=(start.getDay()+6)%7;const total=new Date(today.getFullYear(),today.getMonth()+1,0).getDate();return `<div class="cardbody"><h3>${today.toLocaleDateString(undefined,{month:'long',year:'numeric'})}</h3><div class="calendar">${['MON','TUE','WED','THU','FRI','SAT','SUN'].map(day=>`<div class="day header">${day}</div>`).join('')}${Array.from({length:Math.ceil((offset+total)/7)*7},(_,i)=>{const n=i-offset+1;return `<div class="day ${n===today.getDate()?'today':''}">${n>0&&n<=total?n:''}${S.data.campaigns.filter(c=>c.schedule&&new Date(c.schedule).getDate()===n&&new Date(c.schedule).getMonth()===today.getMonth()&&new Date(c.schedule).getFullYear()===today.getFullYear()).map(c=>`<div class="calitem">${esc(c.name)} · ${esc(c.status==='draft'?'Draft':c.status)}</div>`).join('')}</div>`}).join('')}</div></div>`}
function contactsPage(){const list=S.data.contacts.filter(c=>(c.name+' '+c.phone+' '+c.tags.join(' ')).toLowerCase().includes(S.search.toLowerCase()));return pagehead('Contacts','Your customer relationships, organized in one place.',btn('Import CSV','import-contacts')+btn('Export CSV','export-contacts')+btn('+ Add contact','new-contact','','primary'))+`<div class="toolbar"><input class="search" data-search placeholder="Search name, number or tag…" aria-label="Search contacts" value="${esc(S.search)}">${badge(list.length+' contacts','gray')}</div><section class="card">${list.length?`<div class="tablewrap"><table><thead><tr><th>Contact</th><th>Phone number</th><th>Tags / segment</th><th>Consent</th><th>Actions</th></tr></thead><tbody>${list.map(c=>`<tr><td><div class="person"><div class="avatar green">${initials(c.name)}</div><div><strong>${esc(c.name)}</strong><small>${esc(c.source)}</small></div></div></td><td>+${esc(c.phone)}</td><td>${tags(c.tags)||'<span class="muted">No tags</span>'}</td><td>${badge(c.optin?'Opted in':'No consent',c.optin?'':'gray')}</td><td>${btn('Edit','edit-contact',`data-id="${c.id}"`,'small')}${btn('Open chat','open-chat',`data-id="${c.id}"`,'small ghost')}</td></tr>`).join('')}</tbody></table></div>`:empty('No contacts found','Add a contact or import a CSV to start your workspace.',btn('Add contact','new-contact','','primary small'))}</section><div class="notice">${icon('contacts')}<span>Tags act as dynamic audience segments. Custom contact attributes are stored with each profile. A phone number alone does not establish marketing consent.</span></div>`}

function renderBubbleBody(m){
  let text = m.body || '';
  let btnMarkup = '';
  if (text.includes('\n\n🔘 ')) {
    const parts = text.split('\n\n🔘 ');
    text = parts[0];
    const buttons = (parts[1] || '').split(' · ').map(b => b.trim()).filter(Boolean);
    if (buttons.length) {
      btnMarkup = `<div class="msg-btn-bar">${buttons.map(b => `<button type="button" class="btn-pill" data-do="click-msg-button" data-val="${esc(b)}">${esc(b)}</button>`).join('')}</div>`;
    }
  }
  let voiceMarkup = '';
  if (text.startsWith('🎙️ [Voice note')) {
    voiceMarkup = `<div class="voice-note-badge">🎙️ Voice Note</div> `;
  }
  return voiceMarkup + esc(text) + btnMarkup;
}

function smartRepliesBar(messages){
  const lastIn = (messages || []).filter(m => m.direction === 'in').at(-1);
  if (!lastIn) return '';
  const body = (lastIn.body || '').toLowerCase();
  let suggestions = [];
  if (body.includes('price') || body.includes('pricing') || body.includes('cost') || body.includes('plan')) {
    suggestions = ['Our starter plan begins at $29/mo with unlimited chats.', 'Here is our full pricing breakdown: starter, pro, and enterprise.', 'Would you like to schedule a quick demo with our sales team?'];
  } else if (body.includes('order') || body.includes('track') || body.includes('shipping') || body.includes('delivery')) {
    suggestions = ['I would be happy to check your order status! What is your order ID?', 'Your order has been confirmed and is scheduled for prompt dispatch.', 'Tracking updates are sent automatically via WhatsApp.'];
  } else if (body.includes('help') || body.includes('agent') || body.includes('human') || body.includes('support')) {
    suggestions = ['Hello! A support specialist is right here to assist you.', 'How can we best help you today?', 'I will take personal ownership of resolving this issue for you.'];
  } else if (body.includes('rating') || body.includes('star') || body.includes('csat') || body.includes('satisfied') || /^[1-5]$/.test(body.trim())) {
    suggestions = ['Thank you so much for your feedback! It means a lot to our team.', 'We appreciate your rating. Let us know if we can do anything else!'];
  } else {
    suggestions = [
      'Thanks for reaching out! How can I assist you today?',
      'Understood, let me check the details and get right back to you.',
      'Is there anything else I can help you with?'
    ];
  }
  return `<div class="smart-replies-bar"><span class="smart-label">💡 AI Suggestions:</span>${suggestions.map(s => `<button type="button" class="smart-chip" data-do="use-smart-chip" data-val="${esc(s)}">${esc(s.length > 38 ? s.slice(0, 35) + '…' : s)}</button>`).join('')}</div>`;
}

function inboxPage(){const d=S.data;const all=d.contacts;const view=ensureInboxView(),list=selectInboxContacts(d,view,S.filter,S.search);if(!d.sandbox&&S.mode==='reply')S.mode='live';if(!all.some(c=>c.id===S.chat))S.chat=list[0]?.id;const c=all.find(c=>c.id===S.chat);const messages=d.messages.filter(m=>m.contact===c?.id);const collisions=(d.active_presences||[]).filter(p=>p.contact_id===c?.id);const typingMembers=collisions.filter(p=>p.status==='typing');return pagehead('Team Inbox','One place for every conversation and every teammate.','<a class="button" href="#support-tools">Support tools</a>'+btn('New contact','new-contact','','small')+btn('Import CSV','open-csv-importer','','small')+btn('⚡ Sandbox','open-sandbox-modal','','small'))+`<div class="inbox"><section class="chatlist"><div class="listhead"><input data-search placeholder="Search conversations…" aria-label="Search conversations" value="${esc(S.search)}"><div class="chatfilters">${['all','open','pending','mine'].map(v=>btn(v[0].toUpperCase()+v.slice(1),'filter',`data-filter="${v}"`,S.filter===v?'primary':'')).join('')}</div>${inboxAdvancedFilters(list,all.length)}</div>${list.map(p=>{const last=d.messages.filter(m=>m.contact===p.id).at(-1);return `<button class="chatrow ${S.chat===p.id?'selected':''}" data-do="select-chat" data-id="${p.id}"><span class="avatar green">${initials(p.name)}</span><span><strong>${esc(p.name)}</strong><div class="snippet">${esc(last?.body||'Start a conversation')}</div><div class="sub">${esc(p.status)} · ${last?clock(last.ts):'New'}</div></span></button>`}).join('')||empty('No conversations','Add a contact to begin.')}</section>${c?`<section class="conversation">${inboxSelectionNote(list,S.chat)}<div class="conversationhead"><div class="person"><div class="avatar green">${initials(c.name)}</div><div><strong>${esc(c.name)}</strong><div class="sub">+${esc(c.phone)} · WhatsApp</div></div></div><select data-chat-status="${c.id}" aria-label="Conversation status">${['open','pending','solved'].map(v=>`<option ${v===c.status?'selected':''}>${v}</option>`).join('')}</select></div>${collisions.length?`<div class="collision-banner">⚠️ <strong>Collision warning:</strong> ${collisions.map(a=>`<span>${esc(a.user_name)} (${esc(a.status)})</span>`).join(', ')}</div>`:''}<div class="messages">${messages.length?messages.map(m=>`<div class="bubble ${m.direction==='out'?'out':''} ${m.direction==='note'?'note':''} ${m.status==='draft'?'draft':''}">${commentAttribution(m)}${renderBubbleBody(m)}${receivedAttachment(m)}<small>${clock(m.ts)} · ${esc(m.direction==='note'?'Private note':m.status)}${m.status==='draft'?` · ${btn('Use draft','use-message',`data-id="${m.id}"`,'small ghost')}`:''}</small></div>`).join(''):'<div class="hint">No recorded messages yet.</div>'}${typingMembers.length?`<div class="typing-indicator"><span>${typingMembers.map(a=>esc(a.user_name)).join(', ')} is typing</span><span class="typing-dots"><span>.</span><span>.</span><span>.</span></span></div>`:''}</div><form class="composer" id="composer"><div class="buttons">${btn('Attachment','media-open','','small ghost')}${btn('Quick reply','choose-reply','','small ghost')}${btn('Template','choose-template','','small ghost')}${btn('🔘 Quick buttons','composer-add-buttons','','small ghost')}${btn('⚡ Sandbox simulator','open-sandbox-modal','','small ghost')}${d.sandbox?btn('Simulate inbound','simulate-inbound','','small ghost'):''}</div><textarea id="compose" aria-label="Message" placeholder="Type a reply or internal note… Type @ to mention a teammate." required>${esc(S.draft)}</textarea><div class="composerfoot"><select id="message-mode" aria-label="Message mode">${d.sandbox?`<option value="reply" ${S.mode==='reply'?'selected':''}>Sandbox reply</option>`:''}<option value="note" ${S.mode==='note'?'selected':''}>Private note</option><option value="live" ${S.mode==='live'?'selected':''}>${d.meta.live?'LIVE WhatsApp':'WhatsApp · not connected'}</option></select><button class="primary" type="submit" ${S.mode==='live'&&!d.meta.live?'disabled':''}>${S.mode==='note'?'Add note':S.mode==='live'?'Send live message':'Send sandbox reply'} →</button></div></form></section><aside class="contactpanel"><div class="avatar green">${initials(c.name)}</div><h3>${esc(c.name)}</h3><div style="text-align:center">${badge(c.status)}</div><div class="sectionlabel">CONTACT INFO</div><div class="profileline"><b>Phone number</b>+${esc(c.phone)}</div><div class="profileline"><b>Source</b>${esc(c.source)}</div><div class="profileline"><b>Marketing consent</b>${c.optin?'Opted in':'Not opted in'}</div><div class="profileline"><b>Customer CSAT</b>${c.csat_score ? `⭐ ${c.csat_score}/5` : 'Not rated yet'}${c.csat_comment ? `<br><small class="sub">${esc(c.csat_comment)}</small>` : ''}</div><div class="sectionlabel">ASSIGNED OPERATOR</div><select data-chat-assignee="${c.id}" aria-label="Assigned operator"><option value="">Unassigned</option>${d.members.map(m=>`<option value="${m.id}" ${m.id===c.assignee?'selected':''}>${esc(m.name)}</option>`).join('')}</select><div class="sectionlabel">TAGS</div>${tags(c.tags)||'<p class="sub">No tags</p>'}<div class="sectionlabel">CONTACT ATTRIBUTES</div>${Object.entries(c.attributes||{}).map(([k,v])=>`<div class="profileline"><b>${esc(k)}</b>${esc(typeof v==='object'?JSON.stringify(v):v)}</div>`).join('')||'<p class="sub">No custom attributes</p>'}${btn('Edit profile','edit-contact',`data-id="${c.id}"`,'small')}<div class="sectionlabel">CONVERSATION CONTROL</div>${badge(c.automation_hold?'Human handling':'Automation available',c.automation_hold?'amber':'gray')}<div class="handoff-controls">${btn(c.automation_hold?'Resume automation':'Take over',c.automation_hold?'handoff-resume':'handoff-takeover',`data-id="${c.id}"`,'small')}${btn('Follow-up task','crm-contact-task',`data-id="${c.id}"`,'small')}</div>${customerHandoffInfo(c)}${teamOperationsContact(c)}${flowWaitInfo(c)}<div class="sectionlabel">SERVICE WINDOW</div><p class="hint">${c.last_real_inbound&&Date.now()/1000-c.last_real_inbound<86400?'Real inbound event received within 24 hours.':'No active live service window. Use an approved template to start a conversation.'}</p></aside>`:`<div>${empty('Your inbox is ready',d.meta.configured?'No messages received yet. Check your webhook subscription if expected messages are missing.':'Connect your WhatsApp account to receive messages.',d.sandbox?btn('Load sandbox samples','seed','','primary small'):btn('Add contact','new-contact','','primary small'))}</div>`}</div>`}
function templatePageBase(){const list=S.data.templates;const t=list.find(t=>t.id===S.preview)||list[0];return pagehead('Template messages','Create, organize and preview your message templates.',btn('Sync from Meta','sync-templates',S.data.meta.configured&&!S.review?'':'disabled title="Connect Meta in an owner workspace before syncing"')+btn('+ New template','new-template','','primary'))+campaignTabs()+`<div class="notice template-guidance">${icon('templates')}<span>Templates need Meta approval before you can send them.</span></div><div class="split"><section class="card template-list-card"><div class="cardhead"><h2>Your templates</h2>${badge(list.length+(list.length===1?' template':' templates'),'gray')}</div>${list.length?`<div class="tablewrap"><table><thead><tr><th>Name</th><th>Category</th><th>Actions</th></tr></thead><tbody>${list.map(t=>`<tr><td><strong>${esc(t.name)}</strong><div class="sub">${esc(t.language)} · ${esc(t.status)}</div></td><td>${badge(t.category,'blue')}</td><td>${btn('Preview','preview-template',`data-id="${t.id}"`,'small ghost')}${t.meta_id?'':btn('Edit','edit-template',`data-id="${t.id}"`,'small')+btn('Submit to Meta','submit-template',`data-id="${t.id}" ${!S.data.meta.configured||S.review?'disabled title="Connect WhatsApp before submitting"':''}`,'small')}</td></tr>`).join('')}</tbody></table></div>`:empty('Start with a template','Write your first reusable customer message.')}</section><section class="template-preview-card card"><div class="cardhead"><h2>Message preview</h2>${t?badge(t.status,'gray'):''}</div><div class="templatepreview"><div class="phone"><div class="phonehead"><span class="preview-business-mark">${icon('contacts')}</span><span>${esc(S.data.context.workspace.name)}<small>Business account</small></span></div><div class="phonebody"><div class="phonebubble">${t?.header?`<strong class="preview-header">${esc(t.header)}</strong>`:''}<div>${esc(t?.body||'Choose a template to see your message.')}</div>${t?.footer?`<p class="preview-footer">${esc(t.footer)}</p>`:''}<small>Message preview</small></div>${(t?.buttons||[]).map(b=>`<div class="template-preview-button">${esc(b.text)}</div>`).join('')}</div></div></div><p class="preview-caption">${t?.body?.includes('{{')?'Variables are filled with contact details when sent.':'How your message will appear to customers.'}</p></section></div>`}
function automationPage(kind){const list=[...S.data[kind+'s']].sort((a,b)=>(a.priority??100)-(b.priority??100));return pagehead('Automation rules','Run local actions after message, contact, attribute or conversation events.',btn('+ Create rule','new-rule','','primary'))+automationTabs()+`<div class="notice">${icon('rules')}<span>Enabled rules can update contacts, create tasks and drafts, assign chats or hand off to a human. Nothing is automatically sent to WhatsApp. STOP and unsubscribe messages suppress automation and remove campaign consent.</span></div><section class="card">${list.length?`<div class="tablewrap"><table><thead><tr><th>Rule name</th><th>Trigger</th><th>Action</th><th>Status</th><th>Executed</th><th>Actions</th></tr></thead><tbody>${list.map(r=>`<tr><td><strong>${esc(r.name)}</strong></td><td>${ruleTriggerSummary(r)}<div class="sub">Priority ${r.priority??100}${r.segment_id?' · '+esc((S.data.segments||[]).find(s=>s.id===r.segment_id)?.name||'Missing segment · blocked'):''}</div></td><td>${ruleActionSummary(r)}</td><td>${badge(r.enabled?'Enabled':'Disabled',r.enabled?'':'gray')}</td><td>${r.executions||0}</td><td>${btn('Edit','edit-rule',`data-id="${r.id}"`,'small')}${btn('Delete','delete',`data-kind="rule" data-id="${r.id}"`,'small ghost danger')}</td></tr>`).join('')}</tbody></table></div>`:empty('Automate the first response',S.data.sandbox?'Create a rule, then simulate an inbound message from the inbox.':'Create a rule to act on incoming WhatsApp events.')}</section>`+ruleExecutionPanel()+noResponseHistoryPanel()}
function flowPage(){return graphPage()}
function sequencePage(){return dripSequencePage()}
function repliesPage(){return pagehead('Reply material','Helpful answers your whole team can reuse.',btn('+ Add reply','new-reply','','primary'))+automationTabs()+`<div class="roadmap">${S.data.replies.map(r=>`<section class="card"><div class="cardbody">${badge('Text reply','gray')}<h3 style="margin-top:18px">${esc(r.name)}</h3><p style="white-space:pre-wrap">${esc(r.body)}</p>${btn('Edit','edit-reply',`data-id="${r.id}"`,'small')}${btn('Delete','delete',`data-kind="reply" data-id="${r.id}"`,'small ghost danger')}</div></section>`).join('')}</div>${S.data.replies.length?'':empty('A library of helpful replies','Save business hours, pricing answers and common support responses.')}`}
function analyticsPage(){return realAnalyticsPage()}
function teamPage(){return pagehead('Your team & workspaces','Give every business its own customer data and team access.',btn('+ New workspace','new-workspace')+btn('Add team member','new-member'))+`<section class="card"><div class="cardhead"><h2>${esc(S.data.context.workspace.name)} · Team members</h2>${badge(S.data.members.length+' members','gray')}</div><div class="tablewrap"><table><thead><tr><th>Team member</th><th>Email</th><th>Role</th><th>Workspace access</th><th>Actions</th></tr></thead><tbody>${S.data.members.map(m=>`<tr><td><div class="person"><span class="avatar">${initials(m.name)}</span><strong>${esc(m.name)}</strong></div></td><td>${esc(m.email)}</td><td>${badge(m.role,m.role==='admin'?'':'gray')}</td><td>${esc(S.data.context.workspace.name)}</td><td>${memberAccessControls(m)}</td></tr>`).join('')}</tbody></table></div></section><div class="grid2"><section class="card"><div class="cardhead"><h2>Business workspaces</h2></div><div class="cardbody">${S.data.context.workspaces.map(w=>`<div class="summaryrow"><strong>${esc(w.name)}</strong>${badge(w.role,'gray')}</div>`).join('')}</div></section><section class="card"><div class="cardhead"><h2>Access controls</h2></div><div class="cardbody"><p class="hint"><strong>Administrator:</strong> workspace configuration, templates, campaigns, automations, team and contacts.</p><p class="hint"><strong>Agent:</strong> contacts, inbox replies, notes and assignment.</p><p class="hint">Invite teammates with a private, one-time link. Administrators manage workspace settings; agents handle conversations. Account recovery is available when email delivery is configured.</p></div></section></div>`+invitationPanel()+teamOperationsPanel()}
function settingsPage(){const m=S.data.meta;return aiConnectionCard()+pagehead('Connect your Meta account','Your own credentials, stored only on the server.',btn('Refresh status','refresh','','small'))+`<div class="notice ${m.live?'warn':''}">${icon('settings')}<span>${m.live?'Live sending has been enabled in the server environment. Verify recipients before sending.':'Sending is off. Check your Meta connection before activation.'}</span></div><section class="card"><div class="cardhead"><h2>WhatsApp Cloud API connection</h2>${badge(m.configured?'Credentials configured':'Not configured',m.configured?'':'gray')}</div><div class="cardbody"><div class="connection">${Object.entries(m.present).map(([k,v])=>`<div class="connection-item"><span>${esc(k.replaceAll('_',' '))}</span>${badge(m.invalid?.[k]?'Invalid format':v?'Set':'Missing',m.invalid?.[k]?'amber':v?'':'gray')}</div>`).join('')}</div>${Object.keys(m.invalid||{}).length?`<div class="notice warn" style="margin-top:16px"><div><strong>Correct these settings in the private server environment</strong>${Object.entries(m.invalid).map(([key,message])=>`<p class="hint"><strong>${esc(key)}</strong>: ${esc(message)}</p>`).join('')}</div></div>`:''}<h3 style="margin-top:25px">Workspace environment variables</h3><p class="hint">Set these values in the private server environment. Never paste credentials into the website or commit them to GitHub.</p><div class="code">${Object.keys(m.present).map(k=>esc(m.prefix+k)+'=YOUR_VALUE').join('\n')}\n${esc(m.prefix)}LIVE=false</div><h3 style="margin-top:25px">Signed webhook route</h3><div class="code">/webhook/${esc(S.workspace)}</div><p class="hint">${S.deployment==='hosted'?'Use this route on your deployed HTTPS domain for Meta webhook setup.':'Local development still needs a publicly reachable HTTPS callback before Meta can deliver webhook events.'}</p></div></section><section class="card"><div class="cardhead"><h2>Recent workspace activity</h2></div><div class="cardbody">${S.data.audit.slice(0,8).map(a=>`<div class="summaryrow"><span>${esc(a.actor)} · ${esc(a.action)}</span><span class="muted">${date(a.ts)} ${clock(a.ts)}</span></div>`).join('')||'<p class="hint">Your activity will appear here.</p>'}</div></section>`}
function roadmapPage(){
 const areas=[
 ['Shared inbox','Assignment history, private comments/authors/mentions, recipient notifications, inbound/outbound attachments, drafts and team routing.','Calls, groups, collaborator permissions, richer inbox filters and additional channels.'],
 ['Contacts','CSV import, tags, consent, custom attributes, saved filter segments, branch routing and acquisition-source capture.','Complete WATI field/filter and lifecycle equivalence.'],
 ['Templates & campaigns','Text-template creation/submission/sync, approved-template queue, schedules and signed delivery/read updates.','Rich media/carousels, Flow templates outside the service window, advanced targeting, SMS fallback and equivalent campaign analytics.'],
 ['Drip sequences','Ordered template steps, relative waits, immutable run snapshots, pause/resume/cancel and consent rechecks.','Live-provider acceptance and WATI-specific enrollment/branching controls.'],
 ['AI Ask','Queued jobs, progress, Stop, model selection, citations, feedback and private history.','Visual comparison, live model acceptance and full WATI tool coverage.'],
 ['AI agents','Observed preset catalog, proposals, schedules, findings/action approval, grounded customer drafts and gated automatic replies.','Equivalent hiring/authorization lifecycle, live model acceptance and full tool coverage.'],
 ['Business knowledge','Text, DOCX and text-based PDF sources, reviewed website ingestion/refresh, lexical retrieval, citations and source-usage analytics.','OCR for scanned PDFs, full-site crawling, semantic retrieval and complete WATI training workflows.'],
 ['Growth & support','Authenticated webhook recipes for contacts/leads/drafts; snooze, macros, expiring feedback links; public help articles; static WhatsApp form draft/export/create/upload/publish/send adapters.','Native Google/Zoho/WooCommerce authorization, live Meta Flow acceptance, calendar bookings, branch-specific visibility permissions and ad-spend/revenue attribution.'],
 ['External agents & Developers','Scoped, expiring read-only API tokens; connection records, signed event outbox, delivery history, retries and reply-draft callbacks.','API write/send operations, MCP connectivity, live endpoint acceptance and WATI protocol equivalence.'],
 ['Chatbot builder','Questions, conditions, waits, contact actions, gated text/media/template delivery, separate drafts, immutable publications and restore-to-draft.','External API/action nodes, full media/template vocabulary and exact runtime/provider parity.'],
 ['Commerce & integrations','Own catalogue, stock-aware orders, scoped Razorpay links/refunds/webhooks, Shiprocket booking/AWB/pickup/labels/tracking, read-only Shopify.','Approved payment/shipping acceptance, Meta catalogue selling and more provider adapters.'],
 ['Analytics','Full-history traffic reports, daily chart/CSV, recorded acquisition-source funnel counts, branch totals, support resolution samples and CSAT ratings.','Historical response/resolution, advanced team/campaign reports, sales attribution and AI quality verification.'],
 ['Client services','Isolated operator-provisioned clients, owner invitations, Razorpay subscriptions, password lifecycle, optional MFA/recovery, SMTP recovery adapter and HTTPS deployment.','Self-service Meta onboarding, organization MFA policy, live subscription acceptance, backup restore drill and production operations.'],['Calls & channels','Official WhatsApp text/media/template adapters, signed webhooks, inbound/outbound call signaling, permission requests and browser audio.','Transfers, recordings, other channels and live audio/provider acceptance.'],['Sales & team operations','Sales stages/deadlines/history, structured teams, expiring availability, workload caps, team routing and assignment history.','Collaborator visibility, browser presence, business hours, automatic backlog redistribution and advanced pipeline automation.']
 ];
 return pagehead('WATI parity checklist','Current implemented behavior and the remaining work for each product area.')+`<div class="notice"><span>Local automated checks establish implementation behavior. Live provider acceptance and current visual parity remain pending. API tokens are available under Connectors. Configured services still require their own provider acceptance.</span></div><section class="card"><div class="tablewrap"><table><thead><tr><th>Feature area</th><th>Implemented</th><th>Still required</th></tr></thead><tbody>${areas.map(([name,done,next])=>`<tr><td><strong>${esc(name)}</strong></td><td>${esc(done)}</td><td>${esc(next)}</td></tr>`).join('')}</tbody></table></div></section>`;
}
function showModal(title,html,submit,label='Save'){$('#modal').classList.remove('agent-template-modal');formSubmit=submit;$('#modal').innerHTML=`<div class="modalhead"><h2>${esc(title)}</h2>${btn('✕','close','','ghost small')}</div><form id="dialog-form" class="modalbody">${html}<p class="error" id="formerror"></p><div class="modalfoot">${btn('Cancel','close')}<button class="primary" type="submit">${label}</button></div></form>`;$('#modal').showModal()}
function field(name,label,value='',type='text',options){const id='f-'+name;let input;if(type==='textarea'||type==='json')input=`<textarea id="${id}" name="${name}" ${type==='json'?'data-json':''} required>${esc(type==='json'?JSON.stringify(value||{},null,2):value)}</textarea>`;else if(type==='checkbox')input=`<label class="check" for="${id}"><input id="${id}" name="${name}" type="checkbox" ${value?'checked':''}><span>${esc(label)}</span></label>`;else if(type==='select')input=`<select id="${id}" name="${name}">${options.map(([v,l])=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(l)}</option>`).join('')}</select>`;else input=`<input id="${id}" name="${name}" type="${type||'text'}" value="${esc(value)}" ${['tag','tags','schedule','target'].includes(name)?'':'required'} ${name==='password'?'minlength="12" maxlength="256" autocomplete="new-password"':''}>`;if(type==='password')input=passwordControlMarkup(input,id,label);return `<div class="field">${type==='checkbox'?'':`<label for="${id}">${esc(label)}</label>`}${input}</div>`}
function entityForm(title,action,fields,initial={}){showModal(title,fields.map(f=>field(f[0],f[1],initial[f[0]]??f[4]??'',f[2]||'text',f[3])).join(''),async data=>{if(initial.id)data.id=initial.id;if(data.schedule)data.schedule=new Date(data.schedule).toISOString();await act(action,data);$('#modal').close();await refresh();toast('Saved to this workspace.')})}
function contactForm(c={}){entityForm(c.id?'Edit contact':'Add a contact','contact.save',[['name','Full name'],['phone','International phone number'],['tags','Tags, separated by commas'],['optin','This contact explicitly opted in to campaigns','checkbox'],['attributes','Custom attributes (JSON)','json']],{...c,tags:(c.tags||[]).join(', ')})}
function templateForm(t={}){return startTemplateEditor(t)}
function campaignForm(){if(!S.data.templates.length){toast('Create a local template first.');location.hash='templates';return}const options=S.data.templates.map(t=>[t.id,t.name]);entityForm('Create campaign','campaign.save',[['name','Campaign name'],['template_id','Message template','select',options],['segment_id','Saved audience','select',[['','All opted-in contacts'],...(S.data.segments||[]).map(s=>[s.id,s.name])]],['tag','Also require tag (optional)'],['schedule','Scheduled date and local time','datetime-local']],{})}
function ruleForm(kind,r={}){if(kind==='rule')return richRuleForm(r);if(kind==='flow')return flowSettingsForm(r);entityForm(r.id?'Edit '+kind:'Create '+kind,kind+'.save',[['name','Name'],['keyword','Incoming message contains'],['reply','Suggested reply','textarea'],['enabled','Enable suggested reply drafts','checkbox']],{enabled:true,...r})}
function openSandboxModal(){
  const contact=S.data.contacts.find(c=>c.id===S.chat)||S.data.contacts[0]||{phone:'15550100',name:'Test Customer',id:''};
  showModal('⚡ WhatsApp Sandbox Simulator',`
    <div class="sandbox-card">
      <p><strong>Simulate Real Inbound & Outbound Events</strong> without Meta approval.</p>
      <div class="field"><label for="sb-phone">Customer Phone Number</label><input id="sb-phone" value="${esc(contact.phone||'15550100')}"></div>
      <div class="field"><label for="sb-body">Customer Message Body</label><textarea id="sb-body" placeholder="e.g. Hi, I need help with my order.">Hi</textarea></div>
      <div class="sandbox-pills">
        <button type="button" class="sandbox-pill" onclick="$('#sb-body').value='Hi'">Greeting</button>
        <button type="button" class="sandbox-pill" onclick="$('#sb-body').value='Where is my order?'">Order status</button>
        <button type="button" class="sandbox-pill" onclick="$('#sb-body').value='Talk to human'">Talk to human</button>
        <button type="button" class="sandbox-pill" onclick="$('#sb-body').value='I have a complaint, connect me to agent'">Complaint</button>
      </div>
    </div>
    <div class="field">
      <label>Delivery Status Webhooks</label>
      <div class="buttons">
        <button type="button" class="button small ghost" id="sb-btn-delivered">Simulate 'Delivered'</button>
        <button type="button" class="button small ghost" id="sb-btn-read">Simulate 'Read'</button>
      </div>
    </div>
  `,async()=>{
    const phone=$('#sb-phone').value.trim();
    const body=$('#sb-body').value.trim();
    if(!phone||!body)throw new Error('Phone and message text are required.');
    await act('sandbox.simulate_inbound',{phone,body});
    $('#modal').close();
    await refresh();
    toast('Simulated WhatsApp message received and processed.');
  },'Send Inbound Message');
  $('#sb-btn-delivered')?.addEventListener('click',async()=>{
    const lastOut=S.data.messages.filter(m=>m.contact===contact.id&&m.direction==='out').at(-1);
    if(!lastOut)return toast('No outbound message found for this contact.');
    await act('sandbox.simulate_status',{message_id:lastOut.id,status:'delivered'});
    await refresh();
    toast('Status updated to Delivered.');
  });
  $('#sb-btn-read')?.addEventListener('click',async()=>{
    const lastOut=S.data.messages.filter(m=>m.contact===contact.id&&m.direction==='out').at(-1);
    if(!lastOut)return toast('No outbound message found for this contact.');
    await act('sandbox.simulate_status',{message_id:lastOut.id,status:'read'});
    await refresh();
    toast('Status updated to Read.');
  });
}

function openCsvImporterModal(){
  let previewData=null;
  showModal('Dynamic CSV Contact Importer',`
    <p>Upload a CSV file or paste CSV text with dynamic column mappings.</p>
    <div class="field"><label for="csv-file-input">Choose CSV File</label><input type="file" id="csv-file-input" accept=".csv,text/csv"></div>
    <div class="field"><label for="csv-raw">Or Paste CSV Text</label><textarea id="csv-raw" placeholder="name,phone,City,Plan&#10;Alice,+15550101,New York,Pro&#10;Bob,+15550102,London,Starter" style="height:90px"></textarea></div>
    <div class="buttons" style="margin-bottom:12px"><button type="button" class="button small primary" id="btn-parse-csv">Analyze Columns</button></div>
    <div id="csv-mapping-area" style="display:none">
      <div class="sectionlabel">COLUMN MAPPINGS</div>
      <div class="field"><label for="map-phone">Phone Column (Required)</label><select id="map-phone"></select></div>
      <div class="field"><label for="map-name">Name Column</label><select id="map-name"></select></div>
      <div class="field"><label for="batch-tag">Batch Tag (Optional)</label><input id="batch-tag" placeholder="e.g. Nov-Campaign"></div>
      <div class="sectionlabel">PREVIEW (FIRST 3 ROWS)</div>
      <div id="csv-preview-table" class="tablewrap" style="max-height:160px;overflow:auto"></div>
    </div>
  `,async()=>{
    const raw=$('#csv-raw').value.trim();
    if(!raw)throw new Error('Please provide CSV content.');
    const phoneCol=$('#map-phone').value;
    const nameCol=$('#map-name').value;
    const tag=$('#batch-tag').value.trim();
    const mapping={phone:phoneCol,name:nameCol,attributes:{}};
    if(previewData?.headers){
      for(const h of previewData.headers){
        if(h!==phoneCol&&h!==nameCol){
          mapping.attributes[h.toLowerCase().replace(/[^a-z0-9_]/g,'_')]=h;
        }
      }
    }
    const res=await act('contacts.import',{csv:raw,mapping,tags:tag?[tag]:[]});
    $('#modal').close();
    await refresh();
    toast('Successfully imported '+res.imported+' contacts! ('+(res.errors?.length||0)+' errors)');
  },'Import Contacts');

  const parseCsv=async()=>{
    const raw=$('#csv-raw').value.trim();
    if(!raw)return toast('Paste CSV content or select a file first.');
    const res=await act('contacts.import',{csv:raw,preview:true});
    previewData=res;
    const mapArea=$('#csv-mapping-area');
    mapArea.style.display='block';
    const phoneSel=$('#map-phone'), nameSel=$('#map-name');
    phoneSel.innerHTML=res.headers.map(h=>`<option value="${esc(h)}" ${['phone','mobile','whatsapp','number','tel'].includes(h.toLowerCase())?'selected':''}>${esc(h)}</option>`).join('');
    nameSel.innerHTML=res.headers.map(h=>`<option value="${esc(h)}" ${['name','full_name','customer_name','first_name'].includes(h.toLowerCase())?'selected':''}>${esc(h)}</option>`).join('');
    $('#csv-preview-table').innerHTML=`<table><thead><tr>${res.headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${res.preview.map(r=>`<tr>${res.headers.map(h=>`<td>${esc(r[h]||'')}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  };

  $('#btn-parse-csv')?.addEventListener('click',parseCsv);
  $('#csv-file-input')?.addEventListener('change',async e=>{
    const file=e.target.files[0];
    if(file){$('#csv-raw').value=await file.text();void parseCsv()}
  });
}

async function handleAction(el){const a=el.dataset.do,id=el.dataset.id;try{
if(a==='open-sandbox-modal')return openSandboxModal();
if(a==='open-csv-importer')return openCsvImporterModal();
if(a.startsWith('auth-'))return authEntryAction(a);
if(a.startsWith('service-'))return await serviceAction(a,el);
if(a.startsWith('voice-'))return await voiceAction(a,el);
if(a==='logout'&&VOICE.id)await voiceAction('voice-end',{dataset:{}});
if(a.startsWith('commerce-'))return await ownedCommerceAction(a,el);
if(a==='nav-toggle')return toggleNavigation();
if(a.startsWith('help-'))return await helpAction(a,el);
if(a.startsWith('received-media-'))return await receivedMediaAction(a,el);
if(a.startsWith('extension-'))return await extensionAction(a,el);
if(a.startsWith('growth-'))return await growthAction(a,el);
if(a.startsWith('password-'))return passwordRecoveryAction(a);
if(a.startsWith('analytics-'))return await analyticsAction(a);
if(a.startsWith('member-'))return await memberAccessAction(a,el);
if(a.startsWith('invite-'))return await invitationAction(a,el);
if(a.startsWith('crm-')||a.startsWith('review-')||a.startsWith('handoff-'))return await businessAction(a,el);
if(a.startsWith('template-'))return await templateAction(a,el);
if(a==='media-open'||a.startsWith('integration-'))return await integrationAction(a,el);
if(a.startsWith('team-'))return await teamOperationAction(a,el);
if(a.startsWith('drip-'))return await dripAction(a,el);
if(a.startsWith('customer-'))return await customerAction(a,el);
if(a.startsWith('segment-'))return await segmentAction(a,el);
if(a.startsWith('external-'))return await externalAction(a,el);
if(a.startsWith('graph-'))return await graphAction(a,el);
if(a==='ai-agents-open'){location.hash='ai-agents';return}
if(a.startsWith('ai-'))return await aiAction(a,el);
if(a==='cancel-campaign'){await act('campaign.cancel',{id});await refresh();toast('Unsent queued recipients cancelled. In-flight messages may already have been submitted.');return}
if(a==='sync-templates'){const r=await act('templates.sync',{});await refresh();toast(r.synced+' Meta templates synced.'+(r.has_more?' More templates remain at the provider.':''));return}
if(a==='submit-template')return showModal('Submit this template to Meta','<p>This creates a real template review request in your Meta account.</p>',async()=>{await act('template.submit',{id});$('#modal').close();await refresh()},'Submit to Meta');
if(a.startsWith('api-token-'))return await apiTokenAction(a,el);
if(a==='close')return $('#modal').close();if(a==='refresh')return refreshWorkspace(el);
if(a==='account-profile')return accountProfileForm();
if(a==='account-security')return accountSecurityForm();
if(a==='account-password')return accountPasswordForm();
if(a==='logout'){await api('/api/logout',{method:'POST',body:'{}'});clearAccountSession();renderAuth();return}
if(a==='seed'){await act('demo.seed',{});await refresh();toast('Synthetic sample data loaded. No real messages sent.');return}
if(a==='new-contact')return contactForm();if(a==='edit-contact')return contactForm(S.data.contacts.find(c=>c.id===id));
if(a==='new-template')return templateForm();if(a==='edit-template')return templateForm(S.data.templates.find(t=>t.id===id));
if(a==='preview-template'||a==='preview-flow'){S.preview=id;return render()}
if(a==='new-campaign')return campaignForm();
if(a==='run-campaign'){const c=S.data.campaigns.find(c=>c.id===id);return showModal(S.data.sandbox?'Run a sandbox campaign':'Launch a real WhatsApp campaign',`<p>Campaign: <strong>${esc(c.name)}</strong>.</p><p class="hint">${S.data.sandbox?'Sandbox only.':'This queues real messages for opted-in contacts. A synced Meta-approved text template and enabled server credentials are required. Meta message charges may apply.'}</p>`,async()=>{const r=await act(S.data.sandbox?'campaign.run':'campaign.launch',{id});$('#modal').close();await refresh();toast(r.audience+' recipients '+(S.data.sandbox?'simulated.':'queued.'))},S.data.sandbox?'Run sandbox':'Launch campaign')}
if(a==='new-rule'||a==='new-flow')return ruleForm(a==='new-rule'?'rule':'flow');
if(a==='edit-rule'||a==='edit-flow'){const kind=a==='edit-rule'?'rule':'flow';return ruleForm(kind,S.data[kind+'s'].find(r=>r.id===id))}
if(a==='new-sequence'||a==='edit-sequence')return dripSequenceEditor(S.data.sequences.find(s=>s.id===id)||{});
if(a==='new-reply'||a==='edit-reply')return entityForm('Reusable reply','reply.save',[['name','Reply name'],['body','Reply content','textarea']],S.data.replies.find(r=>r.id===id)||{});
if(a==='new-member')return entityForm('Add a local team account','member.add',[['name','Full name'],['email','Email address','email'],['password','Initial password · 12+ characters','password'],['role','Access role','select',[['agent','Agent'],['admin','Administrator']]]]);
if(a==='new-workspace')return showModal('Create a business workspace',field('name','Business name'),async data=>{const w=await act('workspace.create',data);S.workspace=w.id;S.chat=null;$('#modal').close();await refresh();toast('New isolated workspace created.');});
if(a==='delete')return showModal('Delete local record','<p>This removes the selected record from this local workspace.</p>',async()=>{await act('entity.delete',{kind:el.dataset.kind,id});$('#modal').close();await refresh()},'Delete record');
if(a==='campaign-view'){S.campaignView=el.dataset.view;return render()}
if(a==='open-chat'){const searchBox=$('#workspace-search-results');if(searchBox)searchBox.hidden=true;S.chat=id;S.search='';S.filter='all';location.hash='inbox';if(S.route==='inbox')render();return}
if(a==='select-chat'){S.chat=id;S.draft='';void act('chat.presence',{contact_id:id,status:'viewing'});return render()}
if(a==='filter'){S.filter=el.dataset.filter;return render()}
if(a==='simulate-inbound')return showModal('Simulate an incoming message',field('body','Customer message','','textarea')+'<p class="hint">Local simulation only. Keywords may generate a draft. This does not open a real Meta service window.</p>',async data=>{await act('message.simulate',{contact_id:S.chat,body:data.body});$('#modal').close();await refresh()},'Simulate inbound');
if(a==='use-message'){S.draft=S.data.messages.find(m=>m.id===id).body;S.mode='reply';return render()}
if(a==='choose-reply'||a==='choose-template'){const isTemplate=a==='choose-template',list=isTemplate?S.data.templates:S.data.replies;showModal(isTemplate?'Choose a local template':'Choose a reusable reply',list.map(x=>`<div class="summaryrow"><span>${esc(x.name)}</span>${btn('Use text',isTemplate?'use-template':'use-reply',`data-id="${x.id}"`,'small')}</div>`).join('')||'<p class="hint">No saved items yet.</p>',()=>$('#modal').close(),'Close');return}
if(a==='use-reply'||a==='use-template'){const item=(a==='use-reply'?S.data.replies:S.data.templates).find(x=>x.id===id);const contact=S.data.contacts.find(c=>c.id===S.chat);S.draft=item.body.replaceAll('{{name}}',contact?.name||'');$('#modal').close();return render()}
if(a==='import-contacts')return showModal('Import contacts from CSV',field('csv','CSV content · name,phone,tags,optin','','textarea')+'<div class="field"><label for="csvfile">Or choose a CSV file</label><input type="file" id="csvfile" accept=".csv,text/csv"></div><p class="hint">Up to 5,000 rows per import. Existing numbers are skipped and reported. Consent defaults to false unless optin is true.</p>',async data=>{const r=await act('contacts.import',data);await refresh();showModal('Import complete',`<div class="importresult"><strong>${r.imported} contacts imported</strong><br>${r.errors.length} rows skipped${r.errors.length?'<p>'+r.errors.slice(0,40).map(esc).join('<br>')+'</p>':''}</div>`,()=>$('#modal').close(),'Done')},'Import contacts');
if(a==='export-contacts'){const r=await fetch('/api/export?workspace='+encodeURIComponent(S.workspace));if(!r.ok)throw new Error('Export failed.');const url=URL.createObjectURL(await r.blob());const link=document.createElement('a');link.href=url;link.download='teamwave-contacts.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return}
}catch(e){toast(e.message)}}
document.addEventListener('click',e=>{const el=e.target.closest('[data-do]');if(el){e.preventDefault();handleAction(el)}});
document.addEventListener('submit',async e=>{if(e.target.id==='dialog-form'){e.preventDefault();const f=e.target;const submit=e.submitter||f.querySelector('button[type=submit]');if(submit)submit.disabled=true;try{const data=Object.fromEntries(new FormData(f));for(const input of f.querySelectorAll('input[type=checkbox]'))data[input.name]=input.checked;for(const input of f.querySelectorAll('[data-json]'))data[input.name]=JSON.parse(input.value);await formSubmit(data)}catch(err){const errorBox=$('#formerror');if(errorBox)errorBox.textContent=err.message;else toast(err.message);if(submit)submit.disabled=false}}
if(e.target.id==='composer'){e.preventDefault();const body=$('#compose').value.trim();if(!body)return;const send=async()=>{await act('message.send',{contact_id:S.chat,body,note:S.mode==='note',live:S.mode==='live'});void act('chat.presence',{contact_id:S.chat,status:'viewing'});S.draft='';$('#modal').close();await refresh()};try{if(S.mode==='live')showModal('Send a real WhatsApp message',`<p>This sends to <strong>${esc(S.data.contacts.find(c=>c.id===S.chat)?.name)}</strong>.</p><div class="code">${esc(body)}</div>`,send,'Send live message');else await send()}catch(err){toast(err.message)}}});
let typingPresenceTimer=null;
document.addEventListener('input',e=>{if(e.target.id==='compose'){S.draft=e.target.value;if(S.chat){clearTimeout(typingPresenceTimer);if(e.target.value.trim()){typingPresenceTimer=setTimeout(()=>{void act('chat.presence',{contact_id:S.chat,status:'typing'})},500)}else{void act('chat.presence',{contact_id:S.chat,status:'viewing'})}}}if(e.target.matches('[data-search]')){S.search=e.target.value;const caret=e.target.selectionStart;render();const target=$('[data-search]');target.focus();target.setSelectionRange(caret,caret)}});
document.addEventListener('change',async e=>{try{if(e.target.dataset.chatStatus){await act('chat.update',{id:e.target.dataset.chatStatus,status:e.target.value});await refresh()}if(e.target.dataset.chatAssignee){await act('chat.update',{id:e.target.dataset.chatAssignee,assignee:e.target.value});await refresh()}if(e.target.id==='message-mode'){S.mode=e.target.value;render()}if(e.target.id==='csvfile'){const file=e.target.files[0];if(file){if(file.size>1000000)throw new Error('CSV file is too large (maximum 1 MB).');$('#f-csv').value=await file.text()}}}catch(err){toast(err.message)}});
window.addEventListener('hashchange',()=>{if(hasPasswordResetHash())return openPasswordReset();if(location.hash==='#signup'&&S.signupAvailable){S.data=null;return renderAuth(true)}if(RECOVERY.mode)return;if(hasInvitationHash())return openInvitation();if(INV.token)return;S.route=location.hash.slice(1)||'campaigns';S.search='';S.preview=null;if(window.innerWidth<=700)localStorage.setItem('vybe-nav-expanded','false');render();window.scrollTo({top:0,behavior:'auto'})});
$('#modal').addEventListener('cancel',()=>formSubmit=null);
$('#modal').addEventListener('close',clearSecurityDialog);
async function retryStartupRequest(request) {
  for (let attempt=0; ; attempt++) {
    try {
      const signal=typeof AbortSignal!=='undefined'&&AbortSignal.timeout ? AbortSignal.timeout(4000) : undefined;
      return await request(signal);
    } catch (error) {
      const temporary=error.name==='TypeError'||error.name==='TimeoutError'||[500,502,503,504].includes(error.status);
      if (!temporary||attempt===2) throw error;
      await new Promise(resolve=>setTimeout(resolve,400*(attempt+1)));
    }
  }
}
function showStartupError() {
  const app=$('#app');
  app.innerHTML=empty('Could not open VYBE Connect','The workspace could not load. Check your connection and try again.','<button class="primary" type="button" id="startup-retry">Try again</button>');
  $('#startup-retry').addEventListener('click',()=>{
    app.innerHTML='<div class="loading" role="status">Opening your workspace…</div>';
    void boot();
  });
}
async function boot() {
  try {
    if (hasPasswordResetHash()) return openPasswordReset();
    if (hasInvitationHash()) return openInvitation();
    const bootstrap=await retryStartupRequest(signal=>api('/api/bootstrap',{signal}));
    S.reviewAvailable=bootstrap.review_available===true;
    S.passwordRecoveryAvailable=bootstrap.password_recovery_available===true;
    S.signupAvailable=bootstrap.signup_available===true;
    S.initialized=bootstrap.initialized;
    S.setupTokenRequired=bootstrap.setup_token_required===true;
    S.deployment=bootstrap.deployment||'local';
    if (location.hash==='#signup'&&S.signupAvailable) return renderAuth(true);
    await retryStartupRequest(signal=>refresh({starting:true,signal}));
  } catch {
    S.data=null;
    showStartupError();
  }
}

boot();
setInterval(async()=>{if(!S.data||$('#modal').open)return;if(!document.activeElement?.matches('input,textarea,select')&&!S.draft)return refresh();if(S.route==='inbox'&&S.chat){try{const res=await act('chat.presence',{contact_id:S.chat,status:S.draft?'typing':'viewing'});if(res&&res.active){S.data.active_presences=res.active;const col=res.active.filter(p=>p.contact_id===S.chat);const typ=col.filter(p=>p.status==='typing');const b=$('.collision-banner');if(col.length){const h=`⚠️ <strong>Collision warning:</strong> ${col.map(a=>`<span>${esc(a.user_name)} (${esc(a.status)})</span>`).join(', ')}`;if(b)b.innerHTML=h;else $('.conversationhead')?.insertAdjacentHTML('afterend',`<div class="collision-banner">${h}</div>`);}else if(b)b.remove();const tEl=$('.typing-indicator');if(typ.length){const th=`<span>${typ.map(a=>esc(a.user_name)).join(', ')} is typing</span><span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>`;if(tEl)tEl.innerHTML=th;else $('.messages')?.insertAdjacentHTML('beforeend',`<div class="typing-indicator">${th}</div>`);}else if(tEl)tEl.remove();}}catch(_){}}},4000);

function campaignPage(){return campaignPageBase()+`<section class="card"><div class="cardhead"><h2>Outbound delivery queue</h2>${badge((S.data.queue||[]).length+' jobs','gray')}</div><div class="tablewrap"><table><thead><tr><th>Contact</th><th>Status</th><th>Due</th><th>Provider message ID</th><th>Detail</th></tr></thead><tbody>${(S.data.queue||[]).map(q=>`<tr><td>${esc(S.data.contacts.find(c=>c.id===q.contact)?.name||q.contact)}</td><td>${badge(q.status,q.status==='unknown'||q.status==='failed'?'amber':'gray')}</td><td>${date(q.due)} ${clock(q.due)}</td><td>${esc(q.external_id||'—')}</td><td>${esc(q.error||'')}</td></tr>`).join('')||'<tr><td colspan="5" class="muted">No messages have been queued in this workspace.</td></tr>'}</tbody></table></div></section>`}

function templatePage(){return TE?templateEditorPage():templatePageBase()}

async function openPublicReview(){
 const state=await api('/api/review/state');S.review=true;S.data=state;S.workspace=state.context.tenant_id;S.deployment='hosted';render();
}
function renderPublicReviewNotice(){
 if(!S.review)return;
 const content=document.querySelector('.content');
 content?.insertAdjacentHTML('afterbegin','<section class="notice review-notice" aria-label="Live review workspace"><div><strong>Preview</strong><span>Read-only workspace preview · Messaging and AI are disconnected.</span></div><a href="/owner" class="primary">Owner setup / sign in</a></section>');
 document.querySelectorAll('.sidebar-bottom [data-do="account-security"],.sidebar-bottom [data-do="account-password"],.sidebar-bottom [data-do="logout"]').forEach(button=>button.hidden=true);
}
