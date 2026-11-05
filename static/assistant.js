'use strict';
const A={tab:'ask',chat:null,agent:null,busy:false};
const AGENT_PRESETS=[
  ['Daily Digest','Summarize recorded inbox workload, recent conversation themes and campaign states. Highlight only supported priorities and clearly describe the partial conversation sample.'],
  ['Inbox Triage','Review the supplied open conversations. Suggest priority and an appropriate team response for each relevant contact. Give evidence and contact IDs. Never claim to assign or reply.'],
  ['Re-engagement Scout','Identify sampled conversations that may merit follow-up using message timestamps, consent and the 24-hour reply window. Suggest approved-template drafts where needed. Do not contact anyone.'],
  ['Urgency Watcher','Inspect the supplied conversations for explicit deadlines, unresolved complaints or time-sensitive requests. Report evidence and suggested human next steps. This is an on-demand review, not continuous monitoring.'],
  ['Top Topics','Group recurring questions in the supplied conversation sample. Cite contact IDs and observed counts. Do not extrapolate sample totals to the whole inbox.'],
  ['Spam Watcher','Identify likely unsolicited advertising or irrelevant messages in the supplied sample. Explain uncertainty and propose tags for human review. Never tag, block or delete contacts yourself.'],
  ['Ready-to-Buy','Look for explicit purchase intent in the supplied sample. List supported contact IDs, relevant message excerpts and a suggested sales response. Do not create a segment or send replies.'],
  ['Automation Health Check','Review supplied rules and graph summaries for missing coverage or conflicting keywords. Use sampled conversations to suggest improvements. Do not claim execution health from configuration alone and do not modify automation.'],
  ['Campaign Readiness Checker','Review campaign states, template approval, consent totals and recorded queue states. Identify visible launch blockers. Wallet balance and pricing are unavailable; never invent affordability or delivery results.'],
  ['Segment & Contact Checker','Review supplied tag counts and contact-field completeness. Propose cleanup or audience criteria for review. Saved advanced segments and full contact history are unavailable; do not invent match counts.'],
  ['Campaign Idea Finder','Suggest at most three draft campaign ideas based on actual sampled customer questions and recorded template/campaign facts. Specify evidence and proposed audience criteria. State that reach and cost need verification.'],
  ['Account Health Checker','Report configured credentials, live-send gate and recorded queue errors separately from provider health. Connection flags do not prove an active channel. State that wallet, billing and growth history are unavailable.']
];
function ensureAIScope(){
  if(!S.data)return;
  const scope=S.data.context.tenant_id+':'+S.data.context.user.id;
  if(A.scope!==scope)Object.assign(A,{scope,tab:'ask',chat:null,agent:null,purpose:'chat',busy:false,draft:'',mode:'ask',contextEnabled:true,expanded:false,collapsed:false,showArchived:false,agentCategory:'All',catalogExpanded:false,run:null,chatRevision:0,modeMenu:false,model:'',activityAgent:null});
}
function showAI(tab){
  ensureAIScope();if(tab)A.tab=tab;if(tab==='agents'&&S.route==='ai-agents'){$('#workspace-ai')?.remove();return renderAI()}
  let panel=$('#workspace-ai');if(!panel){panel=document.createElement('aside');panel.id='workspace-ai';panel.setAttribute('aria-label','Workspace AI assistant');document.body.append(panel)}renderAI();
}
function aiRuntimeLabel(){const a=S.data.ai||{};return a.enabled&&a.configured?(a.provider||'AI')+' configured':a.provider_id==='openai'&&!a.paid_allowed?'AI requests paused':'AI not connected'}
function agentStamp(stamp){return stamp?new Date(stamp*1000).toLocaleString():'—'}
const AGENT_CATALOG_INFO={
 'Daily Digest':['Overview','A clear snapshot of your inbox and campaigns.'],
 'Inbox Triage':['Support','Find unanswered chats and what needs a reply.'],
 'Re-engagement Scout':['Sales','Spot conversations worth following up.'],
 'Urgency Watcher':['Support','Surface urgent questions and time-sensitive issues.'],
 'Top Topics':['Overview','See the questions your customers ask most.'],
 'Spam Watcher':['Support','Flag conversations that may be spam.'],
 'Ready-to-Buy':['Sales','Find customers showing purchase intent.'],
 'Automation Health Check':['Operations','Review gaps in your automation setup.'],
 'Campaign Readiness Checker':['Marketing','Check templates and audiences before launch.'],
 'Segment & Contact Checker':['Operations','Find gaps in contact details and tags.'],
 'Campaign Idea Finder':['Marketing','Get campaign ideas from customer questions.'],
 'Account Health Checker':['Operations','Review connection settings and queue issues.']
};
function aiAgentCard(agent){
 const admin=S.data.context.role==='admin',status=S.data.ai||{},ready=status.enabled&&status.configured;
 const info=AGENT_CATALOG_INFO[agent.name],summary=info?.[1]||'Your custom workspace assistant.';
 const state=agent.archived?'Archived':agent.schedule_enabled?'Scheduled':'On demand';
 const more=admin?(agent.archived?btn('Restore','ai-restore-agent',`data-id="${agent.id}"`,'small'):btn('Edit','ai-edit-agent',`data-id="${agent.id}"`,'small')+btn('Duplicate','ai-copy-agent',`data-id="${agent.id}"`,'small')+btn(agent.schedule_enabled?'Pause schedule':'Schedule','ai-schedule-agent',`data-id="${agent.id}"`,'small')+btn('Archive','ai-archive-agent',`data-id="${agent.id}"`,'small')):'';
 return `<article class="ai-agent saved-agent-card" data-agent-directory="ai" data-agent-name="${esc(agent.name)}" data-agent-status="${agent.archived?'archived':agent.schedule_enabled?'scheduled':'manual'}"><header><div class="saved-agent-identity">${characterAvatar(agent.name)}<div><strong>${esc(agent.name)}</strong><span class="saved-agent-status">${state}</span></div></div></header><p class="agent-card-summary">${summary}</p><div class="buttons agent-card-actions">${agent.archived?'':btn('Ask','ai-use-agent',`data-id="${agent.id}"`,'small')+btn('Run now','ai-run-agent',`data-id="${agent.id}" ${!ready||A.busy?'disabled':''}`,'primary small')}${btn('Activity','ai-agent-activity',`data-id="${agent.id}"`,'small')}</div><details class="agent-manage"><summary>${admin?'Manage':'Details'}</summary><p class="knowledge-content">${esc(agent.instructions)}</p><div class="agent-meta"><span>Proposals: ${esc(agentActionSummary(agent))}</span><span>Next run: ${esc(agentStamp(agent.next_run))}</span><span>Last outcome: ${esc(agent.last_status||'Not run')}</span>${agent.last_error?`<span class="error">${esc(agent.last_error)}</span>`:''}</div>${more?`<div class="buttons">${more}</div>`:''}</details></article>`;
}
function aiAgentsPage(){
 const admin=S.data.context.role==='admin',agents=S.data.aiagents||[],status=S.data.ai||{},ready=status.enabled&&status.configured;
 const categories=['All','Overview','Sales','Support','Marketing','Operations'],category=categories.includes(A.agentCategory)?A.agentCategory:'All';
 const matches=AGENT_PRESETS.map(([name,instructions],index)=>({name,index,info:AGENT_CATALOG_INFO[name]})).filter(p=>category==='All'||p.info[0]===category);
 const visible=A.catalogExpanded?matches:matches.slice(0,6);
 const myAgents=agents.length?`${agentDirectoryToolbar('ai','AI agents',[['scheduled','Scheduled'],['manual','On demand'],['archived','Archived']])}<div class="saved-agent-grid">${agents.map(aiAgentCard).join('')}</div><p class="hint" data-agent-empty="ai" hidden>No agents match your search.</p>`:'<div class="agent-start"><span>Choose a ready-made agent below, or create your own.</span></div>';
 return `<div class="ai-page-title"><div><h2>Your AI team</h2><p class="hint">Small assistants. Big help.</p></div>${admin?btn('+ Create agent','ai-manual-agent','','primary small'):''}</div>${ready?'':`<div class="agent-runtime-note"><span>${status.provider_id==='openai'&&!status.paid_allowed?'AI requests are paused.':'Connect AI to run your agents.'}</span><a href="#settings" data-do="ai-open-settings">Connection settings →</a></div>`}${myAgents}<div class="agent-catalog-heading"><h3>Find your next assistant</h3><span>${AGENT_PRESETS.length} agents</span></div><div class="agent-categories" aria-label="Agent categories">${categories.map(name=>btn(name,'ai-agent-category',`data-category="${name}" aria-pressed="${category===name}"`,'small')).join('')}</div><div class="agent-preset-grid">${visible.map(({name,index,info})=>`<article class="agent-preset-card"><div class="agent-preset-top">${characterAvatar(name)}<span class="agent-category-tag ${info[0].toLowerCase()}">${info[0]}</span></div><h3>${esc(name)}</h3><p>${info[1]}</p>${admin?btn('Set up agent','ai-preset',`data-preset="${index}" aria-label="Set up ${esc(name)}"`,'small agent-preset-setup'):''}</article>`).join('')}</div>${matches.length>6?`<div class="agent-catalog-more">${btn(A.catalogExpanded?'Show fewer agents':'Show all '+matches.length+' agents','ai-catalog-toggle',`aria-expanded="${!!A.catalogExpanded}"`,'small ghost')}</div>`:''}<div class="agent-page-links">${btn('Review findings','review-open','','ghost small')}<a href="#customer-assistant" data-do="ai-open-customer">Customer reply settings →</a></div>`;
}

function agentWorkspacePage(){
 ensureAIScope();
 return `<div class="agent-workspace"><div class="agent-workspace-main"><section class="business-hero"><div><span class="eyebrow">YOUR BUSINESS. CONNECTED.</span><h1>Built for your business</h1><p>Conversations, AI assistants and your CRM.<br>One place to move work forward.</p></div><div class="hero-world" aria-hidden="true"></div></section><div id="agent-workspace-catalog">${aiAgentsPage()}</div></div><aside class="quick-setup"><span class="eyebrow">GET STARTED</span><h2>Quick setup</h2><p>Your workspace, in three steps.</p><ol><li><a href="#settings"><span>1</span><div>Connect WhatsApp<small>Your account and number</small></div><b aria-hidden="true">↗</b></a></li><li><button type="button" data-do="ai-setup-knowledge"><span>2</span><div>Add business knowledge<small>FAQs, products and policies</small></div><b aria-hidden="true">↗</b></button></li><li><button type="button" data-do="ai-manual-agent"><span>3</span><div>Choose your agents<small>Start with a ready-made assistant</small></div><b aria-hidden="true">↗</b></button></li></ol><div class="setup-character" aria-hidden="true"></div><a class="setup-help" href="#developers">Explore your developer tools →</a></aside></div>`;
}

function aiKnowledgePage(){
  const admin=S.data.context.role==='admin';
  return `<h2>Business knowledge</h2><p class="hint">Workspace FAQs, products and policies. Up to eight text sources, 4,000 characters each. Upload documents or index a public website page below. Full-site crawling remains pending.</p>${admin?btn('+ Add source','ai-knowledge-add','','primary small'):''}${(S.data.knowledges||[]).map(k=>`<article class="ai-agent"><strong>${esc(k.title)}</strong> ${badge(k.enabled?'Included':'Disabled',k.enabled?'':'gray')}<p class="knowledge-content">${esc(k.body)}</p>${admin?btn('Edit','ai-knowledge-edit',`data-id="${k.id}"`,'small')+btn('Delete','ai-knowledge-delete',`data-id="${k.id}"`,'small'):''}</article>`).join('')||'<p class="hint">No business sources yet.</p>'}${knowledgeDocumentsPanel()}${knowledgeUsagePanel()}`;
}
function aiActivityPage(){
  const runs=[...(S.data.airuns||[])].reverse().filter(r=>!A.activityAgent||r.agent_id===A.activityAgent),selected=runs.find(r=>r.id===A.run)||runs[0];
  if(!selected)return '<h2>Agent activity</h2><p class="hint">No recorded runs'+(A.activityAgent?' for this agent':'')+'. Choose an agent and run it or set a schedule.</p>'+btn('All activity','ai-all-activity','','small');
  const findings=(S.data.findings||[]).filter(f=>f.run_id===selected.id);
  return `<h2>Agent activity</h2>${A.activityAgent?btn('All activity','ai-all-activity','','small'):''}<div class="analysis-history">${runs.slice(0,20).map(r=>btn(esc(r.agent_name)+' · '+esc(r.status),'ai-run-history',`data-id="${r.id}"`,'small')).join('')}</div><article class="ai-agent"><strong>${esc(selected.agent_name)}</strong> ${badge(selected.status,selected.status==='failed'?'amber':'gray')}<p class="hint">${esc(agentStamp(selected.created))} · ${esc(selected.trigger||'manual')} · ${selected.sample_contacts} sampled contacts</p><p class="knowledge-content">${esc(selected.summary||selected.error||'Run in progress. An interrupted server may leave a run waiting for recovery.')}</p><p class="hint">${esc(selected.scope)}</p></article>${findings.map(f=>`<article class="finding-card"><strong>${esc(f.title)}</strong> ${badge(f.status,'gray')}<p class="hint">${esc(f.details)}</p>${f.action?`<pre class="finding-action">${esc(JSON.stringify(f.action,null,2))}</pre>`:''}</article>`).join('')}${btn('Open findings for review','review-open','','primary small')}`;
}
function activeAIJobs(){return (S.data.aijobs||[]).filter(j=>j.chat_id===A.chat&&['queued','running','waiting','cancelling'].includes(j.status))}
function agentProposalCard(message){
  const draft=message.agent_draft;if(!draft)return '';
  return `<article class="ai-agent"><strong>${esc(draft.name)}</strong><p class="knowledge-content">${esc(draft.instructions)}</p><p class="hint">Suggested cadence: ${esc(draft.cadence)}. Scheduling stays paused after saving.</p>${message.applied_agent_id?badge('Agent saved · review schedule separately','gray'):btn('Review agent','ai-review-proposal',`data-id="${esc(message.id)}" ${S.data.context.role==='admin'?'':'disabled'}`,'primary small')}</article>`;
}
function startAgentBuilder(){
  if(S.data.context.role!=='admin')throw new Error('Administrator access required to create agents.');
  A.chatRevision++;A.chat=null;A.agent=null;A.purpose='agent_builder';A.mode='ask';A.contextEnabled=false;A.modeMenu=false;A.tab='ask';A.draft='';return renderAI();
}
function reviewAgentProposal(messageId){
  const chatId=A.chat,chat=S.data.aichats.find(c=>c.id===chatId),message=chat?.messages.find(m=>m.id===messageId&&m.agent_draft);if(!message)throw new Error('Agent proposal is unavailable.');
  const proposal=message.agent_draft,tenant=S.data.context.tenant_id,user=S.data.context.user.id;
  showModal('Review agent before saving',field('name','Agent name',proposal.name)+field('instructions','Instructions',proposal.instructions,'textarea')+field('cadence','Suggested cadence',proposal.cadence,'select',[['manual','Manual only'],['hourly','Hourly'],['daily','Daily'],['weekly','Weekly']])+'<p class="hint">This saves a review-first agent. It does not run the agent or enable a schedule. Findings and proposed changes require human review.</p>',async data=>{
    if(S.data?.context.tenant_id!==tenant||S.data?.context.user.id!==user)throw new Error('Account changed. Reopen the proposal.');
    const agent=await act('ai.chat.install-agent',{chat_id:chatId,message_id:messageId,...data});$('#modal').close();await refresh();A.tab='agents';A.agent=agent.id;renderAI();toast('Agent saved with scheduling paused.');
  },'Save agent · keep paused');
}
function aiMessage(message){
  const answer=message.role==='assistant';
  return `<div class="ai-message ${message.role}"><b>${answer?'Assistant':'You'}</b><p>${esc(message.content)}</p>${answer&&message.steps?.length?`<details class="ai-steps"><summary>WORKED THROUGH ${message.steps.length} STEPS</summary>${message.steps.map(step=>`<div>${esc(step.name)} · ${esc(new Date(step.at*1000).toLocaleTimeString())}</div>`).join('')}</details>`:''}${answer?(message.references||[]).map(ref=>`<div class="ai-source"><strong>${esc(ref.label)}</strong><div class="buttons">${btn('Open messages','ai-open-source',`data-contact="${esc(ref.contact_id)}" data-ids="${esc(ref.message_ids.join(','))}"`,'small')}${btn('Open conversation','ai-source-conversation',`data-id="${esc(ref.contact_id)}"`,'small')}</div></div>`).join(''):''}${answer?knowledgeReferenceCards(message)+agentProposalCard(message):''}${answer&&message.id?`<div class="ai-feedback">${btn('Helpful','ai-feedback',`data-id="${message.id}" data-rating="helpful"`,message.rating==='helpful'?'primary small':'ghost small')}${btn('Not helpful','ai-feedback',`data-id="${message.id}" data-rating="not_helpful"`,message.rating==='not_helpful'?'primary small':'ghost small')}</div>`:''}</div>`;
}
function aiComposerTools(status,ready){
  const models=status.models||[];
  return `<div class="ai-compose-tools"><div class="ai-mode-control">${btn('+','ai-mode-menu','aria-label="Pick a mode" title="Pick a mode"','ai-mode-toggle')}${A.modeMenu?`<div class="ai-mode-menu" id="ai-mode-menu">${btn('<strong>Create an agent</strong><span>Create and configure an agent.</span>','ai-mode-agent',S.data.context.role==='admin'?'':'disabled','ghost')}${btn('<strong>Get insights</strong><span>Find trends and answers in your data.</span>','ai-mode-insights',ready?'':'disabled','ghost')}</div>`:''}</div><label class="sr-only" for="ai-model">Pick a model</label><select id="ai-model" aria-label="Pick a model" ${models.length?'':'disabled'}>${models.length?models.map(model=>`<option value="${esc(model)}" ${model===(A.model||status.model)?'selected':''}>${esc(model)}</option>`).join(''):'<option>Model unavailable</option>'}</select></div>`;
}
async function aiSubmitQuestion(question){
  if(!question||A.busy)return;
  const scope=A.scope,revision=A.chatRevision,status=S.data.ai||{};
  A.draft=question;A.busy=true;renderAI();
  try{const result=await act('ai.chat.start',{question,chat_id:A.chat,agent_id:A.agent,purpose:A.purpose||'chat',mode:A.mode,model:A.model||status.model,page:A.contextEnabled?S.route:'',contact_id:A.contextEnabled&&S.route==='inbox'?S.chat:null});if(A.scope===scope&&A.chatRevision===revision){A.chat=result.chat_id;A.draft=''}await refresh()}catch(error){if(A.scope===scope)toast(error.message)}finally{if(A.scope===scope){A.busy=false;renderAI()}}
}
function aiAskPage(){
  const status=S.data.ai||{},chat=(S.data.aichats||[]).find(c=>c.id===A.chat),agent=(S.data.aiagents||[]).find(a=>a.id===A.agent),ready=status.enabled&&status.configured&&!agent?.archived,jobs=activeAIJobs();
  const builder=(chat?.purpose||A.purpose)==='agent_builder';
  const suggestions=builder?['Create a daily agent that finds unanswered customer questions.','Create an hourly agent that flags urgent conversations for review.']:S.route==='inbox'?['Summarize this conversation.','Find unresolved customer questions.']:S.route==='templates'?['Which templates are approved?','Review my draft templates.']:['Show engagement from my recent campaigns.','Which campaigns need attention?'];
  const terminal=(S.data.aijobs||[]).filter(j=>j.chat_id===A.chat&&['failed','unknown','cancelled','cancel_unconfirmed'].includes(j.status)).slice(-3);
  return `<div class="ai-transcript">${chat?.messages.length?chat.messages.map(aiMessage).join(''):`<div class="ai-welcome"><span>✧</span><h2>${builder?'Describe the agent you want':agent?'Ask '+esc(agent.name):'How can I help you?'}</h2><p class="hint">${builder?'Describe its task and preferred cadence. Review the generated proposal before saving.':'Ask about actual workspace information. Sources are linked when supported by supplied messages.'}</p>${builder?btn('Configure manually','ai-manual-agent','','ghost small'):''}${suggestions.map(q=>btn(esc(q),'ai-suggest',`data-question="${esc(q)}"`,'ai-suggestion')).join('')}</div>`}${jobs.map(job=>`<div class="ai-message user"><b>You</b><p>${esc(job.question)}</p></div><div class="ai-job-phase" role="status"><span>${esc(job.phase)}</span><small>${Math.max(0,Math.floor(Date.now()/1000-job.created))}s · ${esc(job.status)}</small></div>`).join('')}${terminal.map(job=>`<div class="ai-job-result"><strong>${esc(job.phase)}</strong>${job.error?`<p>${esc(job.error)}</p>`:''}${job.can_cancel?btn('Retry Stop','ai-stop','','small'):''}${job.cancel_outcome==='local_discarded'?'<p>The late answer was discarded. Local model generation may have continued.</p>':job.cancel_outcome==='provider_completed'?'<p>The provider had already finished. The answer was discarded.</p>':job.status==='cancel_unconfirmed'?'<p>Provider cancellation could not be confirmed.</p>':''}</div>`).join('')}</div><div class="ai-compose">${A.contextEnabled?`<span class="tag">${esc(S.route==='inbox'&&S.chat?'Selected conversation':S.route)} ${btn('×','ai-dismiss-context','','ghost small')}</span>`:''}${agent?`<span class="tag">${esc(agent.name)}</span>`:''}${!ready?'<p class="hint">Configure an active AI provider. OpenAI also requires workspace paid-call approval. No answer is simulated.</p>':''}<form id="ai-form"><textarea id="ai-question" maxlength="8000" aria-label="Ask me anything" placeholder="Ask me anything…" ${A.busy?'disabled':''}>${esc(A.draft)}</textarea><button type="submit" class="primary" ${!ready||A.busy?'disabled':''}>${A.busy?'Queueing…':jobs.length?'Append message':'Send message'}</button>${jobs.length?btn('Stop','ai-stop',jobs.every(j=>j.status==='cancelling')?'disabled':'','small'):''}</form>${aiComposerTools(status,ready)}</div>`;
}
async function aiExecutionAction(action,el){
  if(action==='ai-stop'){await act('ai.chat.cancel',{chat_id:A.chat});await refresh();return renderAI()}
  if(action==='ai-feedback'){await act('ai.chat.feedback',{chat_id:A.chat,message_id:el.dataset.id,rating:el.dataset.rating});await refresh();return renderAI()}
  if(action==='ai-source-conversation'){$('#modal')?.close();$('#workspace-ai')?.remove();S.chat=el.dataset.id;S.search='';S.filter='all';location.hash='inbox';if(S.route==='inbox')render();return}
  if(action==='ai-open-source'){
    const scope=A.scope,tenant=S.data.context.tenant_id,owner=S.data.context.user.id;const result=await api('/api/chat-source?contact_id='+encodeURIComponent(el.dataset.contact)+'&ids='+encodeURIComponent(el.dataset.ids));if(A.scope!==scope||!S.data||S.data.context.tenant_id!==tenant||S.data.context.user.id!==owner||!$('#workspace-ai'))return;
    return showModal('Sources · '+result.contact.name,result.messages.map(m=>`<article class="ai-source"><strong>${esc(m.direction)} · ${esc(new Date(m.ts*1000).toLocaleString())}</strong><p class="knowledge-content">${esc(m.body)}</p></article>`).join('')+btn('Open conversation','ai-source-conversation',`data-id="${result.contact.id}"`,'small'),()=>$('#modal').close(),'Close');
  }
}
let aiJobPolling=false;
setInterval(async()=>{
  if(aiJobPolling||!S.data||!$('#workspace-ai')||$('#modal')?.open||!activeAIJobs().length)return;
  const scope=A.scope;aiJobPolling=true;
  try{const state=await api('/api/state');if(S.data&&$('#workspace-ai')&&A.scope===scope&&state.context.tenant_id===S.data.context.tenant_id&&state.context.user.id===S.data.context.user.id){S.data.aichats=state.aichats;S.data.aijobs=state.aijobs;renderAI()}}catch(error){if(error.status===401)$('#workspace-ai')?.remove()}finally{aiJobPolling=false}
},1500);
function renderAI(){
  ensureAIScope();const panel=$('#workspace-ai');if(!S.data)return;if(S.route==='ai-agents'){const catalog=$('#agent-workspace-catalog');if(catalog){catalog.innerHTML=aiAgentsPage();filterAgentDirectory('ai')}}if(panel&&S.route==='ai-agents'&&A.tab==='agents'){panel.remove();return}if(!panel){if(S.route==='ai-agents'&&A.tab!=='agents')return showAI(A.tab);return}const previousQuestion=$('#ai-question'),restoreFocus=previousQuestion&&document.activeElement===previousQuestion,caret=previousQuestion?.selectionStart;
  panel.classList.toggle('ai-expanded',!!A.expanded);panel.classList.toggle('ai-collapsed',!!A.collapsed);
  const status=S.data.ai||{},runs=[...(S.data.airuns||[])].reverse();
  panel.innerHTML=`<div class="ai-header"><strong>✧ VYBE Connect AI</strong><div>${badge(aiRuntimeLabel(),status.enabled&&status.configured?'':'gray')}${btn(A.expanded?'Restore':'Expand','ai-expand','','ghost small')}${btn('✕','ai-close','aria-label="Close AI assistant"','ghost')}</div></div><div class="ai-layout"><nav class="ai-nav">${btn(A.collapsed?'›':'‹','ai-collapse',`aria-label="${A.collapsed?'Expand':'Collapse'} AI navigation" aria-expanded="${!A.collapsed}"`,'ghost small')}<div class="ai-nav-content"><div class="ai-tabs">${btn('Ask','ai-tab','data-tab="ask"',A.tab==='ask'?'primary small':'small')}${btn('Agents','ai-tab','data-tab="agents"',A.tab==='agents'?'primary small':'small')}</div>${btn('+ New chat','ai-new','','ghost small')}${btn('Daily Digest','ai-digest','','ghost small')}${btn('Knowledge','ai-tab','data-tab="knowledge"','ghost small')}${btn('Agent activity','ai-tab','data-tab="activity"','ghost small')}<div class="navlabel">RECENT</div>${(S.data.aichats||[]).slice(-12).reverse().map(c=>btn(esc(c.name),'ai-history',`data-id="${c.id}"`,'ai-history')).join('')}${runs.slice(0,5).map(r=>btn(esc(r.agent_name)+' · '+esc(r.status),'ai-run-history',`data-id="${r.id}"`,'ai-history')).join('')}</div></nav><main class="ai-body">${A.tab==='agents'?aiAgentsPage():A.tab==='knowledge'?aiKnowledgePage():A.tab==='activity'?aiActivityPage():aiAskPage()}</main></div>`;
  const f=$('#ai-form');if(f)f.onsubmit=e=>{e.preventDefault();return aiSubmitQuestion($('#ai-question').value.trim())};
  const question=$('#ai-question');if(question){question.oninput=()=>A.draft=question.value;if(restoreFocus){question.focus();if(typeof caret==='number')question.setSelectionRange(caret,caret)}}
  filterAgentDirectory('ai');
  const model=$('#ai-model');if(model)model.onchange=()=>A.model=model.value;
}
function editAIAgent(agent={}){
  if(S.data.context.role!=='admin')throw new Error('Administrator access required to configure agents.');
  const tenant=S.data.context.tenant_id,user=S.data.context.user.id,same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user;
  showModal(agent.id?'Edit agent':'New agent',field('name','Agent name',agent.name||'')+`<details class="agent-setup-options" ${agent.instructions?'':'open'}><summary>Instructions & permissions</summary>${field('instructions','Instructions',agent.instructions||'','textarea')}${agentActionFields(agent)}</details><p class="hint">Runs create findings for your review. Nothing is sent automatically.</p>`,async d=>{if(!same())throw new Error('Workspace changed. Reopen agent setup.');if(agent.id)d.id=agent.id;d.allowed_actions=[...document.querySelectorAll('[data-agent-action]:checked')].map(e=>e.dataset.agentAction);await act('aiagent.save',d);if(!same())return;$('#modal').close();A.tab='agents';await refresh();if(same())renderAI()},agent.id?'Save agent':'Create agent');
  $('#f-name').maxLength=100;$('#f-instructions').maxLength=6000;
}
const agentActionLabels={tag:'Add a contact tag',assign:'Assign a teammate and pause automation',note:'Add an internal note',draft_reply:'Create an unsent reply draft',task:'Create an internal follow-up task'};
function agentActionFields(agent){
  const selected=agent.allowed_actions??Object.keys(agentActionLabels);
  return '<h3>Allowed action proposals</h3>'+Object.entries(agentActionLabels).map(([type,label])=>`<label class="summaryrow"><span>${esc(label)}</span><input type="checkbox" data-agent-action="${type}" ${selected.includes(type)?'checked':''}></label>`).join('')+'<p class="hint">Choose no actions for information-only findings. Removing permission also blocks approval of pending proposals for that action.</p>';
}
function agentActionSummary(agent){const allowed=agent.allowed_actions??Object.keys(agentActionLabels);return allowed.length?allowed.map(type=>agentActionLabels[type]||type).join(', '):'Information-only findings'}
async function aiAction(action,el){
  ensureAIScope();const id=el.dataset.id;if(['ai-stop','ai-feedback','ai-open-source','ai-source-conversation'].includes(action))return aiExecutionAction(action,el);
  if(action==='ai-setup-knowledge')return showAI('knowledge');
  if(action==='ai-open-agent'){const agent=(S.data.aiagents||[]).find(a=>a.id===id&&!a.archived);if(!agent)throw new Error('This agent is unavailable. Refresh the workspace.');A.chatRevision++;A.agent=id;A.chat=null;A.purpose='chat';A.tab='ask';A.draft='';return showAI('ask')}
  if(action==='ai-open')return showAI();
  if(action==='ai-agent-category'){A.tab='agents';const choices=['All','Overview','Sales','Support','Marketing','Operations'];if(!choices.includes(el.dataset.category))return;A.agentCategory=el.dataset.category;A.catalogExpanded=false;return renderAI()}
  if(action==='ai-catalog-toggle'){A.tab='agents';A.catalogExpanded=!A.catalogExpanded;return renderAI()}
  if(action==='ai-open-settings'||action==='ai-open-customer'){$('#workspace-ai')?.remove();location.hash=action==='ai-open-settings'?'settings':'customer-assistant';return}
  if(action.startsWith('ai-document-'))return documentKnowledgeAction(action,el);
  if(action==='ai-mode-menu'){A.modeMenu=!A.modeMenu;return renderAI()}
  if(action==='ai-mode-agent'||action==='ai-new-agent')return startAgentBuilder();
  if(action==='ai-review-proposal')return reviewAgentProposal(id);
  if(action==='ai-manual-agent')return editAIAgent();
  if(action==='ai-mode-insights'){if(A.purpose==='agent_builder'){A.chatRevision++;A.chat=null;A.agent=null;A.purpose='chat';}A.modeMenu=false;A.mode='analysis';A.tab='ask';return aiSubmitQuestion('Summarize my inbox, highlight trends and identify what needs attention.')}

  if(action==='ai-close')return $('#workspace-ai')?.remove();
  if(action==='ai-expand'){A.expanded=!A.expanded;return renderAI()}
  if(action==='ai-collapse'){A.collapsed=!A.collapsed;return renderAI()}
  if(action==='ai-tab'){A.activityAgent=null;A.tab=el.dataset.tab;return renderAI()}
  if(action==='ai-dismiss-context'){A.contextEnabled=false;return renderAI()}
  if(action==='ai-archived-toggle'){A.showArchived=!A.showArchived;return renderAI()}
  if(action==='ai-new'){A.chatRevision++;A.chat=null;A.agent=null;A.purpose='chat';A.draft='';A.tab='ask';return renderAI()}
  if(action==='ai-history'){A.chatRevision++;const chat=S.data.aichats.find(c=>c.id===id);A.chat=id;A.agent=chat?.agent_id||null;A.purpose=chat?.purpose||'chat';A.draft='';A.tab='ask';return renderAI()}
  if(action==='ai-suggest'){A.draft=el.dataset.question;renderAI();return $('#ai-question').focus()}
  if(action==='ai-use-agent'){A.chatRevision++;A.agent=id;A.chat=null;A.purpose='chat';A.draft='';A.tab='ask';return renderAI()}
  if(action==='ai-run-history'){A.run=id;A.tab='activity';return renderAI()}
  if(action==='ai-agent-activity'){A.activityAgent=id;A.run=null;A.tab='activity';return renderAI()}
  if(action==='ai-all-activity'){A.activityAgent=null;A.run=null;A.tab='activity';return renderAI()}
  if(action==='ai-copy-agent')return editAIAgent(agentCopyDraft(S.data.aiagents.find(a=>a.id===id)));
  if(action==='ai-edit-agent')return editAIAgent(S.data.aiagents.find(a=>a.id===id));
  if(action==='ai-preset'){const preset=AGENT_PRESETS[Number(el.dataset.preset)];if(preset)return editAIAgent({name:preset[0],instructions:preset[1]});return}
  if(action==='ai-digest'){
    const agent=S.data.aiagents.find(a=>a.name==='Daily Digest'&&!a.archived);
    if(agent){A.chatRevision++;A.agent=agent.id;A.chat=null;A.purpose='chat';A.tab='ask';A.draft='Give me a daily digest from the recorded workspace facts.';return renderAI()}
    if(S.data.context.role!=='admin')throw new Error('Ask an administrator to create a Daily Digest agent.');
    return editAIAgent({name:AGENT_PRESETS[0][0],instructions:AGENT_PRESETS[0][1]});
  }
  if(action==='ai-run-agent'){
    if(A.busy)return;const scope=A.scope;A.busy=true;renderAI();
    try{const run=await act('ai.run',{agent_id:id});if(A.scope===scope){A.run=run.id;A.tab='activity'}}finally{if(A.scope===scope)A.busy=false;await refresh();renderAI()}return;
  }
  if(action==='ai-schedule-agent'){
    const agent=S.data.aiagents.find(a=>a.id===id);
    if(agent.schedule_enabled){await act('aiagent.schedule',{id,enabled:false});await refresh();return renderAI()}
    return showModal('Schedule '+agent.name,field('interval','Run interval',String(agent.interval||86400),'select',[['3600','Every hour'],['86400','Every 24 hours'],['604800','Every 7 days']])+'<p class="hint">Runs begin after one interval. The server and configured AI provider must be available. Missed intervals are skipped after downtime. Findings still require human review.</p>',async d=>{await act('aiagent.schedule',{id,enabled:true,interval:Number(d.interval)});$('#modal').close();await refresh();renderAI()},'Enable schedule');
  }
  if(action==='ai-archive-agent'||action==='ai-restore-agent')return showModal(action==='ai-archive-agent'?'Archive agent':'Restore agent','<p>Existing chats and run history are retained. Schedules remain paused. Archiving prevents findings from an in-flight run being published.</p>',async()=>{await act('aiagent.archive',{id,archived:action==='ai-archive-agent'});$('#modal').close();await refresh();renderAI()},action==='ai-archive-agent'?'Archive':'Restore');
  if(action==='ai-knowledge-add'||action==='ai-knowledge-edit'){
    const source=S.data.knowledges.find(k=>k.id===id)||{enabled:true};
    showModal(source.id?'Edit source':'Add source',field('title','Source title',source.title||'')+field('body','Business information',source.body||'','textarea')+field('enabled','Include in AI context',source.enabled,'checkbox'),async d=>{if(source.id)d.id=source.id;await act('knowledge.save',d);$('#modal').close();await refresh();renderAI()},'Save source');$('#f-title').maxLength=120;$('#f-body').maxLength=4000;return;
  }
  if(action==='ai-knowledge-delete')return showModal('Delete source','<p>This removes the source from new model requests. Existing chat answers remain.</p>',async()=>{await act('entity.delete',{kind:'knowledge',id});$('#modal').close();await refresh();renderAI()},'Delete source');
}

function knowledgeUsagePanel(){
  const usage=S.data.knowledge_usage||{},sources=usage.sources||[];
  return `<section class="card"><div class="cardhead"><h3>Knowledge usage · last ${usage.window_days||30} days</h3></div><p class="hint">Recorded customer-AI outputs: ${usage.drafts||0} drafts, ${usage.accepted_submissions||0} accepted submissions, ${usage.handoffs||0} human handoffs and ${usage.uncertain||0} uncertain jobs. Acceptance is not delivery or answer quality.</p>${sources.map(source=>`<div class="summaryrow"><span>${esc(source.title)} ${badge(source.enabled?'Enabled':'Disabled','gray')}</span><span>${source.referenced_replies} replies with validated document references</span></div>`).join('')||'<p class="hint">No indexed document sources.</p>'}<p class="hint">Each reply counts once per document, even with multiple passage links. ${usage.manual_source_count||0} manual text sources have no structured document-usage count. Zero references does not prove a source was never read. ${usage.removed_source_references||0} references belong to removed sources.</p></section>`;
}
