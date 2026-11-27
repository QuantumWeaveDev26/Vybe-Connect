'use strict';
const SALES_STAGES=[['new','New'],['qualified','Qualified'],['proposal','Proposal'],['won','Won'],['lost','Lost']];
function salesStageOptions(){return S.data.pipeline?.stages?.map(stage=>[stage.id,stage.label])||SALES_STAGES}
const CRM_CURRENCIES=['INR','USD','EUR','GBP','AED','SGD','AUD','CAD'];
const crmContact=id=>(S.data.contacts||[]).find(c=>c.id===id);
const crmOwner=id=>(S.data.members||[]).find(m=>m.id===id)?.name||'Unassigned';
function dealMoney(deal){return new Intl.NumberFormat(undefined,{style:'currency',currency:deal.currency}).format(deal.amount_minor/100)}
function pipelinePage(){
  const deals=(S.data.deals||[]).filter(deal=>!S.pipelineOverdue||(deal.closure_due&&deal.closure_due<Date.now()/1000&&!['won','lost'].includes(deal.stage)));
  return pagehead('Sales pipeline','Track and follow up on deals.',(S.data.context.role==='admin'?btn('Pipeline settings','crm-pipeline-settings'):'')+btn(S.pipelineOverdue?'Show all deals':'Overdue deals','crm-overdue')+btn('+ Follow-up task','crm-new-task')+btn('+ New deal','crm-new-deal','','primary'))+
    `<details class="pipeline-about"><summary>About deal values</summary><p>Deal values are estimates entered by your team. Won deals are not verified payments or attributed campaign revenue.</p></details><div class="sales-board ${deals.length?'':'sales-board-empty'}">${salesStageOptions().map(([stage,label])=>{
      const list=deals.filter(d=>d.stage===stage),totals={};for(const d of list)totals[d.currency]=(totals[d.currency]||0)+d.amount_minor;
      return `<section class="sales-column"><header><h2>${esc(label)} ${badge(list.length,'gray')}</h2><p class="hint">${Object.entries(totals).map(([currency,amount_minor])=>esc(dealMoney({currency,amount_minor}))).join(' · ')}</p></header>${list.map(d=>`<article class="deal-card"><h3>${esc(d.title)}</h3><p>${esc(crmContact(d.contact_id)?.name||'Contact unavailable')}</p><strong>${esc(dealMoney(d))}</strong>${d.closure_due?`<p class="hint">Closure due ${esc(new Date(d.closure_due*1000).toLocaleString())}${!d.closed_at&&d.closure_due<Date.now()/1000?badge('Overdue','amber'):''}</p>`:''}<p class="hint">${esc(crmOwner(d.owner))}</p><label class="hint" for="stage-${d.id}">Sales stage</label><select id="stage-${d.id}" data-deal-stage="${d.id}">${salesStageOptions().map(([v,l])=>`<option value="${v}" ${v===d.stage?'selected':''}>${esc(l)}</option>`).join('')}</select><div class="buttons">${btn('Activity','crm-deal-activity',`data-id="${d.id}"`,'small')}${btn('Edit','crm-edit-deal',`data-id="${d.id}"`,'small')}${btn('Chat','open-chat',`data-id="${d.contact_id}"`,'small')}${btn('Follow up','crm-deal-task',`data-id="${d.id}"`,'small')}</div></article>`).join('')}</section>`
    }).join('')}</div>${deals.length?'':`<p class="pipeline-empty">${S.pipelineOverdue?'No overdue deals.':'No deals yet. Select New deal to get started.'}</p>`}`+taskSection();
}
function taskSection(){
  const tasks=[...(S.data.tasks||[])].sort((a,b)=>(a.status==='done')-(b.status==='done')||(a.due||Infinity)-(b.due||Infinity));
  return `<section class="card"><div class="cardhead"><h2>Follow-up tasks</h2>${btn('+ Add task','crm-new-task','','small')}</div><div class="tablewrap"><table><thead><tr><th>Task</th><th>Contact</th><th>Owner</th><th>Due</th><th>Status</th><th>Actions</th></tr></thead><tbody>${tasks.map(t=>`<tr><td><strong>${esc(t.title)}</strong>${t.deal_id?`<p class="hint">${esc((S.data.deals||[]).find(d=>d.id===t.deal_id)?.title||'Linked deal')}</p>`:''}</td><td>${esc(crmContact(t.contact_id)?.name||'—')}</td><td>${esc(crmOwner(t.owner))}</td><td>${t.due?esc(new Date(t.due*1000).toLocaleString()):'Unscheduled'}</td><td>${badge(t.status==='done'?'Done':t.due&&t.due<Date.now()/1000?'Overdue':'Open',t.status!=='done'&&t.due&&t.due<Date.now()/1000?'amber':'gray')}</td><td>${btn(t.status==='done'?'Reopen':'Complete','crm-complete-task',`data-id="${t.id}"`,'small')}${btn('Edit','crm-edit-task',`data-id="${t.id}"`,'small')}</td></tr>`).join('')||'<tr><td colspan="6" class="muted">No follow-up tasks. Create one from a deal or customer conversation.</td></tr>'}</tbody></table></div><div class="cardbody"><p class="hint">Tasks are local team reminders. They do not send WhatsApp messages or notifications automatically.</p></div></section>`;
}
function crmContactOptions(){return [['','Choose contact'],...S.data.contacts.map(c=>[c.id,c.name])];}
function crmOwnerOptions(){return [['','Unassigned'],...S.data.members.map(m=>[m.id,m.name])];}
function crmDealForm(deal={}){
  showModal(deal.id?'Edit deal':'Create deal',field('title','Opportunity title',deal.title||'')+field('contact_id','Contact',deal.contact_id||'','select',crmContactOptions())+field('amount','Estimated value',(deal.amount_minor||0)/100,'number')+field('currency','Currency',deal.currency||'INR','select',CRM_CURRENCIES.map(c=>[c,c]))+field('stage','Stage',deal.stage||'new','select',salesStageOptions())+field('closure_due','Closure due · new deals use the default when blank',deal.closure_due?new Date(deal.closure_due*1000-new Date(deal.closure_due*1000).getTimezoneOffset()*60000).toISOString().slice(0,16):'','datetime-local')+field('owner','Owner',deal.owner??S.data.context.user.id,'select',crmOwnerOptions()),async d=>{
    if(!/^\d+(\.\d{1,2})?$/.test(d.amount))throw new Error('Use a non-negative amount with up to two decimal places.');
    const [whole,fraction='']=d.amount.split('.');d.amount_minor=Number(whole)*100+Number(fraction.padEnd(2,'0'));
    if(!Number.isSafeInteger(d.amount_minor))throw new Error('Amount is too large.');
    delete d.amount;if(deal.id)d.id=deal.id;if(!deal.id&&!d.closure_due)delete d.closure_due;else d.closure_due=d.closure_due?new Date(d.closure_due).toISOString():'';await act('deal.save',d);$('#modal').close();await refresh();
  },'Save deal');$('#f-amount').step='0.01';$('#f-amount').min='0';$('#f-closure_due').required=false;
}
function crmTaskForm(task={}){
  const due=task.due?new Date(task.due*1000):null;const local=due?new Date(due.getTime()-due.getTimezoneOffset()*60000).toISOString().slice(0,16):'';
  showModal(task.id?'Edit follow-up':'Create follow-up',field('title','Task',task.title||'')+field('contact_id','Contact (optional)',task.contact_id||'','select',crmContactOptions())+field('deal_id','Deal (optional)',task.deal_id||'','select',[['','No deal'],...(S.data.deals||[]).map(d=>[d.id,d.title])])+field('owner','Owner',task.owner??S.data.context.user.id,'select',crmOwnerOptions())+field('due','Due in your local timezone (optional)',local,'datetime-local'),async d=>{
    if(task.id)d.id=task.id;d.due=d.due?new Date(d.due).toISOString():'';await act('task.save',d);$('#modal').close();await refresh();
  },'Save task');$('#f-due').required=false;
}
async function businessAction(action,el){
  const id=el.dataset.id;
  if(action==='crm-pipeline-settings')return pipelineSettingsForm();
  if(action==='crm-overdue'){S.pipelineOverdue=!S.pipelineOverdue;return render()}
  if(action==='crm-deal-activity')return showModal('Deal activity',pipelineActivity(id),()=>$('#modal').close(),'Close');
  if(action==='review-open'){$('#workspace-ai')?.remove();location.hash='findings';return}
  if(action==='review-run'){
    if(S.analysisBusy||S.review||!aiCanSubmit(S.data.ai||{}))return;
    const agent_id=$('#review-agent')?.value;if(!agent_id)throw new Error('Choose a saved agent first.');
    const workspace=S.workspace,user=S.data.context.user.id;
    const sameWorkspace=()=>S.workspace===workspace&&S.data?.context.user.id===user;
    const knownRuns=new Set((S.data.airuns||[]).map(run=>run.id));
    S.analysisBusy=true;S.analysisFeedback=null;render();
    let result,error;
    try{result=await act('ai.run',{agent_id},workspace)}catch(failure){error=failure.message}
    finally{S.analysisBusy=false}
    if(!sameWorkspace())return;
    await refresh();
    if(!sameWorkspace())return;
    const failedRun=error&&[...(S.data.airuns||[])].reverse().find(run=>
      !knownRuns.has(run.id)&&run.agent_id===agent_id&&run.started_by===user&&run.status==='failed');
    const runId=result?.id||failedRun?.id;
    if(runId){S.reviewRun=runId;S.findingFilter=result?'pending':'all'}
    S.analysisFeedback=error?{workspace,user,message:error,runId}:null;
    if(S.route==='findings'){
      render();
      ($('#analysis-run-result')||$('#analysis-run-feedback'))?.focus();
    }
    return;
  }
  if(action==='review-finding'){
    const f=(S.data.findings||[]).find(f=>f.id===id);if(!f)return;
    const approve=el.dataset.decision==='approve';
    if(el.closest('.finding-observations'))S.findingObservationsOpen=true;
    if(!f.action)return showModal(approve?'Acknowledge observation':'Dismiss observation',`<p><strong>${esc(f.title)}</strong></p><p>${esc(f.details)}</p>`,async()=>{await act('finding.review',{id,decision:approve?'approve':'dismiss'});$('#modal').close();await refresh();toast(approve?'Observation acknowledged.':'Observation dismissed.')},approve?'Acknowledge':'Dismiss observation');
    return showModal(approve?'Review proposed action':'Dismiss finding',`<p><strong>${esc(f.title)}</strong></p><p>${esc(f.details)}</p><p>Contact: ${esc(crmContact(f.contact_id)?.name||'Workspace observation')}</p><p class="finding-change"><strong>Proposed change</strong> ${esc(findingActionSummary(f.action))}</p><p class="hint">${approve?'This applies only the local action shown above. A draft reply is not sent.':'No customer record will be changed.'}</p>`,async()=>{await act('finding.review',{id,decision:approve?'approve':'dismiss'});$('#modal').close();await refresh();toast(approve?'Review recorded.':'Finding dismissed.')},approve?'Approve shown action':'Dismiss finding');
  }
  if(action==='handoff-takeover'||action==='handoff-resume'){
    return showModal(action==='handoff-takeover'?'Take over this conversation':'Resume conversation automation',`<p>${action==='handoff-takeover'?'Assign this chat to you and pause keyword and chatbot processing. Incoming customer messages will still arrive.':'Allow enabled keyword rules and chatbot flows to handle future incoming messages. Any previous flow session starts fresh.'}</p><p class="hint">Campaigns are managed separately.</p>`,async()=>{await act(action==='handoff-takeover'?'chat.takeover':'chat.resume',{id});$('#modal').close();await refresh()},action==='handoff-takeover'?'Take over':'Resume automation');
  }
  if(action==='crm-new-deal')return crmDealForm();
  if(action==='crm-contact-deal')return crmDealForm({contact_id:id});
  if(action==='crm-edit-deal')return crmDealForm(S.data.deals.find(d=>d.id===id));
  if(action==='crm-new-task')return crmTaskForm();
  if(action==='crm-contact-task')return crmTaskForm({contact_id:id});
  if(action==='crm-edit-task')return crmTaskForm(S.data.tasks.find(t=>t.id===id));
  if(action==='crm-deal-task'){const deal=S.data.deals.find(d=>d.id===id);return crmTaskForm({deal_id:id,contact_id:deal.contact_id,owner:deal.owner})}
  if(action==='crm-complete-task'){const task=S.data.tasks.find(t=>t.id===id);await act('task.complete',{id,completed:task.status!=='done'});return refresh()}
}
function analysisRunResult(run,status){
 const failed=['failed','interrupted'].includes(run.status);
 const finished=run.status==='completed';
 const next=failed?(status.provider_pause?aiPauseGuidance(status):'Check the error above before retrying.'):'';
 return `<section class="card analysis-run-result" id="analysis-run-result" tabindex="-1" aria-labelledby="analysis-run-heading"><div class="cardhead"><h2 id="analysis-run-heading">${esc(run.agent_name)}</h2>${badge(run.status,failed?'amber':finished?'green':'gray')}</div><div class="cardbody"><p>${esc(run.error||run.summary||'Analysis is running.')}</p>${next?`<p class="hint">${esc(next)}</p>`:''}<p class="hint">${run.sample_contacts} sampled contacts · ${date(run.created)} ${clock(run.created)}${finished&&Number.isInteger(run.finding_count)?` · ${run.finding_count} findings`:''}</p>${run.scope?`<details><summary>Analysis scope</summary><p class="hint">${esc(run.scope)}</p></details>`:''}</div></section>`;
}

function findingActionSummary(action){
 switch(action.type){
  case 'tag': return 'Add tag: '+action.tag;
  case 'assign': return 'Assign to '+(S.data.members?.find(member=>member.id===action.owner)?.name||'the selected teammate')+', set to Pending, and pause automation.';
  case 'note': return 'Add a private note: '+action.body;
  case 'draft_reply': return 'Save an unsent reply draft: '+action.body;
  case 'task': return 'Create a follow-up task for you: '+action.title;
  default: return 'Review the proposed change.';
 }
}
function findingReviewCard(f,admin,messages){
 const statuses={pending:f.action?'Needs review':'To acknowledge',acknowledged:'Acknowledged',applied:'Applied',dismissed:'Dismissed'};
 const tone=f.status==='pending'&&f.action?'amber':f.status==='applied'?'green':'gray';
 const details=(f.evidence_ids||[]).map(id=>messages.get(id));
 const evidence=details.length?`<details class="finding-evidence"><summary>Supporting messages (${details.length})</summary>${details.map(m=>`<blockquote>${esc(m?.body||'Message is outside the current inbox window.')}</blockquote>`).join('')}</details>`:'';
 const actions=(f.contact_id?btn('Open conversation','open-chat',`data-id="${esc(f.contact_id)}"`,'small'):'')+
  (admin&&f.status==='pending'?btn(f.action?'Review action':'Acknowledge','review-finding',`data-id="${esc(f.id)}" data-decision="approve"`,f.action?'primary small':'small')+
  btn('Dismiss','review-finding',`data-id="${esc(f.id)}" data-decision="dismiss"`,'small ghost'):'');
 return `<article class="finding-card review-finding-card"><header><div><p class="finding-meta">${esc(f.agent_name)} · ${date(f.created)} ${clock(f.created)}</p><h3>${esc(f.title)}</h3></div>${badge(statuses[f.status]||f.status,tone)}</header><p class="finding-details">${esc(f.details)}</p>${f.contact_id?`<p class="finding-meta">Contact · ${esc(crmContact(f.contact_id)?.name||'Conversation')}</p>`:''}${f.action?`<p class="finding-change"><strong>Proposed change</strong> ${esc(findingActionSummary(f.action))}</p>`:''}${evidence}${actions?`<div class="buttons finding-actions">${actions}</div>`:''}</article>`;
}

function findingsPage(){
  const runs=[...(S.data.airuns||[])].reverse(),agents=(S.data.aiagents||[]).filter(a=>!a.archived),admin=S.data.context.role==='admin',status=S.data.ai||{};
  let findings=[...(S.data.findings||[])].reverse();
  const filter=S.findingFilter||'pending';if(filter!=='all')findings=findings.filter(f=>f.status===filter);
  if(S.reviewRun&&runs.some(r=>r.id===S.reviewRun))findings=findings.filter(f=>f.run_id===S.reviewRun);
  const selectedRun=runs.find(run=>run.id===S.reviewRun);
  const proposals=findings.filter(f=>f.action),observations=findings.filter(f=>!f.action);
  const messages=new Map((S.data.messages||[]).map(message=>[message.id,message]));
  const feedback=S.analysisFeedback;
  const analysisError=feedback?.workspace===S.workspace&&feedback.user===S.data.context.user.id&&
    (!feedback.runId||feedback.runId!==selectedRun?.id)?feedback.message:'';
  const configured=aiCanSubmit(status);
  const selected=S.findingAgent?.workspace===S.workspace&&agents.some(a=>a.id===S.findingAgent.id)?S.findingAgent.id:'';
  const guidance=!configured?aiSetupGuidance(status):!agents.length?'Set up an agent in the catalog to run an analysis.':'Analysis creates findings for review. An admin approves proposed changes.';
  const needsPlan=status.platform_managed&&!status.allowance?.active&&!status.allowance?.internal_use&&!status.provider_pause;
  return pagehead('AI findings & review','Inspect agent proposals before applying changes to customer records.',btn('Agent catalog','ai-agents-open','','small'))+
    `<section class="card"><div class="cardhead"><h2>Run an analysis</h2>${badge(aiRuntimeLabel(),configured?'':'gray')}</div><div class="cardbody"><div class="review-run-controls"><label for="review-agent">Saved agent</label><select id="review-agent" ${S.analysisBusy||!agents.length?'disabled':''}><option value="">Choose an agent</option>${agents.map(a=>`<option value="${esc(a.id)}" ${selected===a.id?'selected':''}>${esc(a.name)}</option>`).join('')}</select>${btn(S.analysisBusy?'Analyzing…':'Analyze now','review-run',!configured||S.analysisBusy||S.review||!selected?'disabled':'','primary')}</div><p class="hint">${esc(guidance)}${needsPlan?' Switch to your team workspace if you already have access there.':''}</p>${analysisError?`<p class="notice warn" role="alert" id="analysis-run-feedback" tabindex="-1">${esc(analysisError)}</p>`:''}${needsPlan&&admin?'<a href="#services" class="button small">Review subscription</a>':''}</div></section><div class="finding-filters"><label for="finding-run-history">Run history<select id="finding-run-history"><option value="">All runs</option>${runs.map(run=>`<option value="${esc(run.id)}" ${selectedRun?.id===run.id?'selected':''}>${esc(run.agent_name)} · ${date(run.created)} ${clock(run.created)} · ${esc(run.status)}</option>`).join('')}</select></label><label for="finding-status">Finding status<select id="finding-status">${Object.entries({pending:'Pending',applied:'Applied',dismissed:'Dismissed',acknowledged:'Acknowledged',all:'All statuses'}).map(([value,label])=>`<option value="${value}" ${filter===value?'selected':''}>${label}</option>`).join('')}</select></label></div>${selectedRun?analysisRunResult(selectedRun,status):''}${proposals.length?`<section class="finding-group"><h2>Proposed actions <span>${proposals.length}</span></h2>${proposals.some(f=>f.status==='pending')?'<p class="hint">Review within 24 hours. If the conversation changes, run a fresh analysis.</p>':''}${proposals.map(f=>findingReviewCard(f,admin,messages)).join('')}</section>`:''}${observations.length?`<details class="finding-group finding-observations" ${selectedRun||S.findingObservationsOpen?'open':''}><summary><span>Observations</span><span class="badge gray">${observations.length}</span></summary><div class="finding-observation-list">${observations.map(f=>findingReviewCard(f,admin,messages)).join('')}</div></details>`:''}${findings.length?'':empty('No findings in this view',agents.length?'Choose another run or status, or analyze a saved agent.':'Set up an agent from the catalog to begin.')}`;
}
document.addEventListener('change',async e=>{
  if(e.target.id==='finding-run-history'){
    S.reviewRun=e.target.value;
    if(S.reviewRun)S.findingFilter='all';
    render();
    $('#finding-run-history')?.focus();
    return;
  }
  if(e.target.id==='finding-status'){
    S.findingFilter=e.target.value;
    render();
    $('#finding-status')?.focus();
    return;
  }
  if(e.target.id==='review-agent'){
    S.findingAgent={workspace:S.workspace,id:e.target.value};
    const run=$('[data-do="review-run"]');
    if(run)run.disabled=!e.target.value||S.analysisBusy||S.review||!aiCanSubmit(S.data.ai||{});
    return;
  }
  if(!e.target.dataset.dealStage)return;try{await act('deal.save',{id:e.target.dataset.dealStage,stage:e.target.value});await refresh()}catch(err){toast(err.message);render()}});

function aiConnectionCard(){
 if(S.data.services?.internal_use)return S.data.ai?.enabled&&!S.data.ai?.provider_pause?'':'<p class="notice">AI usage is paused. Check your workspace AI status.</p>';

 if(S.data.services?.platform_ai_mode&&!S.data.ai?.platform_managed){const a=S.data.ai||{};return `<section class="card"><div class="cardhead"><h2>VYBE AI</h2>${badge(a.provider_pause?'Temporarily paused':a.enabled&&a.configured?'Configured':'Paused',!a.provider_pause&&a.enabled&&a.configured?'':'gray')}</div><div class="cardbody"><p>Your platform provides AI for subscribed customers.</p><details class="operator-settings"><summary>Manage platform AI</summary>${operatorAIConnectionCard()}</details></div></section>`;}
 if(S.data.ai?.platform_managed){const a=S.data.ai,limit=a.allowance||{};return `<section class="card"><div class="cardhead"><h2>VYBE AI</h2>${badge(a.provider_pause?'Temporarily paused':limit.active?'Included with your plan':'Subscription needed',a.enabled&&!a.provider_pause?'':'gray')}</div><div class="cardbody"><p>AI is provided by VYBE Connect. No API key needed.</p>${a.provider_pause?'<p class="hint">AI is temporarily paused. Contact support.</p>':''}${limit.active?`<p>${esc(limit.remaining)} of ${esc(limit.limit)} included requests remaining this billing cycle.</p>`:'<a class="button primary workspace-connection-action" href="#services">Choose your subscription</a>'}</div></section>`;}
 return operatorAIConnectionCard();
}
function operatorAIConnectionCard(){
 const a=S.data.ai||{},admin=S.data.context.role==='admin',managed=a.credential_source==='workspace';
 return `<section class="card"><div class="cardhead"><h2>AI assistant connection</h2>${badge(aiRuntimeLabel(),a.enabled&&a.configured?'':'gray')}</div><div class="cardbody"><p><strong>Provider:</strong> ${esc(a.provider||'Not selected')} &middot; <strong>Model:</strong> ${esc(a.model||'Not configured')}</p><p class="hint">${a.configured?'Credentials are configured. A real model response has not been verified by this screen.':'Connect your own OpenAI project key to use AI in this workspace.'}</p>${admin?`<div class="buttons"><button data-ai-connection="save" ${S.review?'disabled':''}>${a.provider_id==='gateway'?'Switch to OpenAI':managed&&a.configured?'Update OpenAI connection':'Connect OpenAI'}</button>${managed&&a.configured?`<button data-ai-connection="pause" ${!a.paid_allowed||S.review?'disabled':''} title="Pauses new requests; running provider work may continue">Pause AI</button><button data-ai-connection="disconnect" ${S.review?'disabled':''}>Remove connection</button>`:''}</div>`:'<p class="hint">A workspace administrator can configure AI.</p>'}<p class="hint">Keys stay on the server. Saving a key does not run a test. Real AI usage may incur provider charges.</p>${aiGatewayControls(a,admin)}${!a.requested_enabled?'<p class="hint">AI processing is currently paused by the platform operator.</p>':''}</div></section>`;
}
document.addEventListener('click',async event=>{
 const el=event.target.closest?.('[data-ai-connection]');if(!el||el.disabled||!S.data)return;
 const operation=el.dataset.aiConnection,scope=S.workspace+':'+S.data.context.user.id,same=()=>S.data&&scope===S.workspace+':'+S.data.context.user.id;
 if(S.data.context.role!=='admin'||S.review)return;
 if(operation==='gateway'){
  const a=S.data.ai||{},options=a.gateway_options||[];if(!options.length)return;const saved=a.provider_id==='gateway'&&a.configured;
  showModal('Connect an approved AI gateway',field('gateway_id','Gateway',a.gateway_id||options[0].id,'select',options.map(g=>[g.id,g.label]))+`<div class="field"><label for="ai-connection-key">Workspace gateway key${saved?' (blank keeps current key)':''}</label><input id="ai-connection-key" name="key" type="password" autocomplete="off" spellcheck="false" maxlength="512" ${saved?'':'required'}><button type="button" data-ai-key-visible aria-controls="ai-connection-key" aria-pressed="false">Show key</button></div>`+field('model','Approved model ID',saved?a.model:options[0].models[0])+`<p class="hint">${options.map(g=>esc(g.label)+': '+g.models.map(esc).join(', ')+'; '+g.requests_per_day+' requests/day').join('<br>')}</p><label class="auth-remember"><input type="checkbox" name="enabled"><span>Enable real usage, including enabled schedules. Provider charges may apply.</span></label><p class="hint">Only platform-approved gateways are accepted. Saving sends no test request.</p>`,async data=>{
   if(!same())throw new Error('Workspace changed. Reopen AI settings.');try{await act('ai.connection.save',{...data,provider:'gateway'});if(!same())return;$('#modal').close();await refresh();toast('Gateway connection saved. No test was sent.')}finally{const input=$('#ai-connection-key');if(input)input.value='';data.key=''}
  },'Save gateway');$('#modal').dataset.aiConnectionScope=scope;return;
 }
 if(operation==='save'){
  const a=S.data.ai||{},saved=a.credential_source==='workspace'&&a.configured;
  showModal('Connect your OpenAI account',`<p>Use a project key from your OpenAI account. It will not be displayed again.</p><div class="field"><label for="ai-connection-key">Project API key${saved?' (leave blank to keep existing)':''}</label><input id="ai-connection-key" name="key" type="password" autocomplete="off" spellcheck="false" maxlength="515" ${saved?'':'required'}><button type="button" data-ai-key-visible aria-controls="ai-connection-key" aria-pressed="false">Show key</button></div><div class="field"><label for="ai-connection-model">Model ID</label><input id="ai-connection-model" name="model" required maxlength="100" value="${esc(a.model||'')}"></div><label class="auth-remember"><input type="checkbox" name="enabled"><span>Enable real AI usage, including enabled schedules. Provider charges may apply.</span></label><p class="hint">Leave unchecked to save with AI paused. No test prompt will be sent.</p>`,async data=>{
   if(!same())throw new Error('Workspace changed. Reopen AI settings.');
   try{await act('ai.connection.save',data);if(!same())return;$('#modal').close();await refresh();toast(data.enabled?'AI enabled for real usage. No test was sent.':'AI key saved. Usage remains paused.')}finally{const input=$('#ai-connection-key');if(input)input.value='';data.key=''}
  },'Save connection');$('#modal').dataset.aiConnectionScope=scope;return;
 }
 if(operation==='disconnect'&&!confirm('Remove this workspace AI connection? AI requests will stop here. Revoke the API key in OpenAI as well if it is no longer needed.'))return;
 try{await act('ai.connection.'+operation,{});if(same())await refresh()}catch(error){if(same())toast(error.message)}
});
document.addEventListener('click',event=>{const button=event.target.closest?.('[data-ai-key-visible]');if(!button)return;const input=$('#ai-connection-key');if(!input)return;const visible=input.type==='password';input.type=visible?'text':'password';button.textContent=visible?'Hide key':'Show key';button.setAttribute('aria-pressed',String(visible))});
function clearAIConnectionDialog(){const modal=$('#modal');if(!modal?.dataset?.aiConnectionScope)return;const scope=S.data?S.workspace+':'+S.data.context.user.id:'';if(!modal.open||modal.dataset.aiConnectionScope!==scope){const input=$('#ai-connection-key');if(input)input.value='';modal.close();modal.innerHTML='';delete modal.dataset.aiConnectionScope;formSubmit=null}}
document.addEventListener('close',event=>{if(event.target.id==='modal')clearAIConnectionDialog()},true);

function pipelineSettingsForm(){
  if(S.data.context.role!=='admin')throw new Error('Administrator access required.');
  const tenant=S.data.context.tenant_id,user=S.data.context.user.id,stages=(S.data.pipeline?.stages||SALES_STAGES.map(([id,label])=>({id,label}))).map(stage=>({...stage}));
  const same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user;
  showModal('Sales pipeline settings',stages.map(stage=>field('label_'+stage.id,stage.label+' · name',stage.label)+(!['new','won','lost'].includes(stage.id)?field('remove_'+stage.id,'Remove '+stage.label,false,'checkbox'):'')).join('')+field('new_stages','Add open stages · one name per line','','textarea')+field('closure_days','Default closure period · days (0 disables)',S.data.pipeline?.closure_days||0,'number')+'<p class="hint">New, Won and Lost stay available. A stage with existing deals cannot be removed. The default deadline applies only to newly created deals. Existing history remains.</p>',async values=>{
    if(!same())throw new Error('Workspace changed. Reopen pipeline settings.');
    const kept=stages.filter(stage=>!values['remove_'+stage.id]).map(stage=>({id:stage.id,label:values['label_'+stage.id]}));
    const added=pipelineNewStageNames(values.new_stages).map(label=>({id:'custom_'+crypto.randomUUID().replaceAll('-','').slice(0,24),label}));
    await act('pipeline.save',{stages:[...kept.filter(stage=>!['won','lost'].includes(stage.id)),...added,...kept.filter(stage=>['won','lost'].includes(stage.id))],closure_days:Number(values.closure_days)});
    if(!same())return;$('#modal').close();await refresh();toast('Pipeline settings saved.');
  },'Save pipeline');$('#f-new_stages').required=false;$('#f-closure_days').min='0';$('#f-closure_days').max='365';
}
function pipelineActivity(id){
  const labels=Object.fromEntries(salesStageOptions());
  const events=(S.data.pipeline?.events||[]).filter(event=>event.deal_id===id);
  return '<p class="hint">Latest 100 workspace stage events; this view shows the selected deal.</p>'+(!events.length?'<p>No recorded stage changes.</p>':'')+events.map(event=>`<div class="summaryrow"><span>${esc(labels[event.from_stage]||event.from_stage||'Created')} → ${esc(labels[event.to_stage]||event.to_stage)}</span><span>${esc(crmOwner(event.actor))} · ${esc(new Date(event.created*1000).toLocaleString())}</span></div>`).join('');
}
function pipelineNewStageNames(value){return value.split(/\r?\n/).map(label=>label.trim()).filter(Boolean)}

function aiGatewayControls(a,admin){
 const gateways=a.gateway_options||[],usage=S.data.gateway_usage||{};
 return (admin&&gateways.length?'<div class="buttons"><button data-ai-connection="gateway" '+(S.review?'disabled':'')+'>Use an AI gateway</button></div>':'')+(a.provider_id==='gateway'?'<p class="hint">Gateway requests today: '+esc(usage.requests||0)+' (UTC). Limits count uncertain requests too. Tokens shown in reports are provider-reported, not verified costs.</p>':'');
}
