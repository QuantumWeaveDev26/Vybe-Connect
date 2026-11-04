'use strict';
const SALES_STAGES=[['new','New'],['qualified','Qualified'],['proposal','Proposal'],['won','Won'],['lost','Lost']];
function salesStageOptions(){return S.data.pipeline?.stages?.map(stage=>[stage.id,stage.label])||SALES_STAGES}
const CRM_CURRENCIES=['INR','USD','EUR','GBP','AED','SGD','AUD','CAD'];
const crmContact=id=>(S.data.contacts||[]).find(c=>c.id===id);
const crmOwner=id=>(S.data.members||[]).find(m=>m.id===id)?.name||'Unassigned';
function dealMoney(deal){return new Intl.NumberFormat(undefined,{style:'currency',currency:deal.currency}).format(deal.amount_minor/100)}
function pipelinePage(){
  const deals=(S.data.deals||[]).filter(deal=>!S.pipelineOverdue||(deal.closure_due&&deal.closure_due<Date.now()/1000&&!['won','lost'].includes(deal.stage)));
  return pagehead('Sales pipeline','Track real opportunities from first inquiry to closure.',(S.data.context.role==='admin'?btn('Pipeline settings','crm-pipeline-settings'):'')+btn(S.pipelineOverdue?'Show all deals':'Overdue deals','crm-overdue')+btn('+ Follow-up task','crm-new-task')+btn('+ New deal','crm-new-deal','','primary'))+
    `<p class="hint">Deal values are estimates entered by your team. Won deals are not verified payments or attributed campaign revenue.</p><div class="sales-board">${salesStageOptions().map(([stage,label])=>{
      const list=deals.filter(d=>d.stage===stage),totals={};for(const d of list)totals[d.currency]=(totals[d.currency]||0)+d.amount_minor;
      return `<section class="sales-column"><header><h2>${esc(label)} ${badge(list.length,'gray')}</h2><p class="hint">${Object.entries(totals).map(([currency,amount_minor])=>esc(dealMoney({currency,amount_minor}))).join(' · ')||'No deals'}</p></header>${list.map(d=>`<article class="deal-card"><h3>${esc(d.title)}</h3><p>${esc(crmContact(d.contact_id)?.name||'Contact unavailable')}</p><strong>${esc(dealMoney(d))}</strong>${d.closure_due?`<p class="hint">Closure due ${esc(new Date(d.closure_due*1000).toLocaleString())}${!d.closed_at&&d.closure_due<Date.now()/1000?badge('Overdue','amber'):''}</p>`:''}<p class="hint">${esc(crmOwner(d.owner))}</p><label class="hint" for="stage-${d.id}">Sales stage</label><select id="stage-${d.id}" data-deal-stage="${d.id}">${salesStageOptions().map(([v,l])=>`<option value="${v}" ${v===d.stage?'selected':''}>${esc(l)}</option>`).join('')}</select><div class="buttons">${btn('Activity','crm-deal-activity',`data-id="${d.id}"`,'small')}${btn('Edit','crm-edit-deal',`data-id="${d.id}"`,'small')}${btn('Chat','open-chat',`data-id="${d.contact_id}"`,'small')}${btn('Follow up','crm-deal-task',`data-id="${d.id}"`,'small')}</div></article>`).join('')||'<p class="hint">No opportunities in this stage.</p>'}</section>`
    }).join('')}</div>`+taskSection();
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
    if(S.analysisBusy)return;
    const agent_id=$('#review-agent').value;if(!agent_id)throw new Error('Choose a saved agent first.');
    S.analysisBusy=true;render();
    try{await act('ai.run',{agent_id});toast('Analysis saved. Findings are waiting for review.')}catch(err){toast(err.message)}finally{S.analysisBusy=false;await refresh();render()}
    return;
  }
  if(action==='review-filter'){S.findingFilter=el.dataset.filter;return render()}
  if(action==='review-select-run'){S.reviewRun=id||'';return render()}
  if(action==='review-finding'){
    const f=(S.data.findings||[]).find(f=>f.id===id);if(!f)return;
    const approve=el.dataset.decision==='approve';
    return showModal(approve?'Review proposed action':'Dismiss finding',`<p><strong>${esc(f.title)}</strong></p><p>${esc(f.details)}</p><p>Contact: ${esc(crmContact(f.contact_id)?.name||'Workspace observation')}</p><pre class="finding-action">${esc(JSON.stringify(f.action,null,2))}</pre><p class="hint">${approve?'This applies only the local action shown above. A draft reply is not sent.':'No customer record will be changed.'}</p>`,async()=>{await act('finding.review',{id,decision:approve?'approve':'dismiss'});$('#modal').close();await refresh();toast(approve?'Review recorded.':'Finding dismissed.')},approve?'Approve shown action':'Dismiss finding');
  }
  if(action==='handoff-takeover'||action==='handoff-resume'){
    return showModal(action==='handoff-takeover'?'Take over this conversation':'Resume conversation automation',`<p>${action==='handoff-takeover'?'Assign this chat to you and pause keyword and chatbot processing. Incoming customer messages will still arrive.':'Allow enabled keyword rules and chatbot flows to handle future incoming messages. Any previous flow session starts fresh.'}</p><p class="hint">Campaigns are managed separately.</p>`,async()=>{await act(action==='handoff-takeover'?'chat.takeover':'chat.resume',{id});$('#modal').close();await refresh()},action==='handoff-takeover'?'Take over':'Resume automation');
  }
  if(action==='crm-new-deal')return crmDealForm();
  if(action==='crm-edit-deal')return crmDealForm(S.data.deals.find(d=>d.id===id));
  if(action==='crm-new-task')return crmTaskForm();
  if(action==='crm-contact-task')return crmTaskForm({contact_id:id});
  if(action==='crm-edit-task')return crmTaskForm(S.data.tasks.find(t=>t.id===id));
  if(action==='crm-deal-task'){const deal=S.data.deals.find(d=>d.id===id);return crmTaskForm({deal_id:id,contact_id:deal.contact_id,owner:deal.owner})}
  if(action==='crm-complete-task'){const task=S.data.tasks.find(t=>t.id===id);await act('task.complete',{id,completed:task.status!=='done'});return refresh()}
}
function findingsPage(){
  const runs=[...(S.data.airuns||[])].reverse(),agents=(S.data.aiagents||[]).filter(a=>!a.archived),admin=S.data.context.role==='admin',status=S.data.ai||{};
  let findings=[...(S.data.findings||[])].reverse();
  const filter=S.findingFilter||'pending';if(filter!=='all')findings=findings.filter(f=>f.status===filter);
  if(S.reviewRun&&runs.some(r=>r.id===S.reviewRun))findings=findings.filter(f=>f.run_id===S.reviewRun);
  const configured=status.enabled&&status.configured;
  return pagehead('AI findings & review','Inspect agent proposals before applying changes to customer records.',btn('Agent catalog','ai-agents-open','','small'))+
    `<section class="card"><div class="cardhead"><h2>Run an analysis</h2>${badge(aiRuntimeLabel(),configured?'':'gray')}</div><div class="cardbody"><div class="review-run-controls"><label for="review-agent">Saved agent</label><select id="review-agent" ${S.analysisBusy?'disabled':''}><option value="">Choose an agent</option>${agents.map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join('')}</select>${btn(S.analysisBusy?'Analyzing…':'Analyze now','review-run',!configured||S.analysisBusy?'disabled':'','primary')}</div><p class="hint">On-demand analysis of a bounded conversation sample. Nothing is sent, assigned or tagged during analysis. An administrator must approve each proposed action. Scheduled agents also create pending findings here while the server is running.</p></div></section><div class="analysis-history">${btn('All runs','review-select-run','','small')}${runs.slice(0,15).map(r=>btn(esc(r.agent_name)+' · '+esc(r.status),'review-select-run',`data-id="${r.id}"`,'small')).join('')}</div>${runs.filter(r=>r.id===S.reviewRun).map(r=>`<section class="card"><div class="cardbody"><strong>${esc(r.agent_name)} · ${esc(r.status)}</strong><p>${esc(r.summary||r.error||'Analysis is running. If the server restarted, this run may have been interrupted.')}</p><p class="hint">${esc(r.scope)} · ${r.sample_contacts} sampled contacts · ${date(r.created)} ${clock(r.created)}</p></div></section>`).join('')}<div class="buttons">${['pending','applied','dismissed','acknowledged','all'].map(v=>btn(v[0].toUpperCase()+v.slice(1),'review-filter',`data-filter="${v}"`,filter===v?'primary small':'small')).join('')}</div>${findings.map(f=>`<article class="finding-card"><div class="cardhead"><h2>${esc(f.title)}</h2>${badge(f.status,f.status==='pending'?'amber':'gray')}</div><p>${esc(f.details)}</p><p class="hint">${esc(f.agent_name)} · ${esc(crmContact(f.contact_id)?.name||'Workspace observation')} · ${date(f.created)} ${clock(f.created)}</p>${f.action?`<pre class="finding-action">${esc(JSON.stringify(f.action,null,2))}</pre>`:'<p class="hint">Information only. No proposed mutation.</p>'}<details><summary>Supporting messages (${f.evidence_ids.length})</summary>${f.evidence_ids.map(id=>{const m=S.data.messages.find(m=>m.id===id);return `<p class="hint">${m?esc(m.body):'Message no longer in the current message window.'} <code>${esc(id)}</code></p>`}).join('')||'<p class="hint">Workspace-level observation; no contact message references.</p>'}</details><div class="buttons">${f.contact_id?btn('Open conversation','open-chat',`data-id="${f.contact_id}"`,'small'):''}${admin&&f.status==='pending'?btn(f.action?'Review action':'Acknowledge','review-finding',`data-id="${f.id}" data-decision="approve"`,'primary small')+btn('Dismiss','review-finding',`data-id="${f.id}" data-decision="dismiss"`,'small'):''}</div></article>`).join('')||empty('No findings in this view',agents.length?'Run a configured agent or choose another filter.':'Create an agent from the AI catalog to begin.')}<p class="hint">Proposals expire after 24 hours and cannot be applied if the target conversation changed. Applied actions are recorded in the workspace audit log. Existing queued campaigns are managed separately.</p>`;
}
document.addEventListener('change',async e=>{if(!e.target.dataset.dealStage)return;try{await act('deal.save',{id:e.target.dataset.dealStage,stage:e.target.value});await refresh()}catch(err){toast(err.message);render()}});

function aiConnectionCard(){
  const a=S.data.ai||{},prefix='TW_AI_'+S.data.context.tenant_id.toUpperCase()+'_';
  return `<section class="card"><div class="cardhead"><h2>AI provider connection</h2>${badge(aiRuntimeLabel(),a.enabled&&a.configured?'':'gray')}</div><div class="cardbody"><p><strong>Provider:</strong> ${esc(a.provider||'Not selected')} · <strong>Model:</strong> ${esc(a.model||'Not configured')}</p><p class="hint">Manage credentials in the private server environment. Keys never appear here.</p><details><summary>Connection configuration</summary><div class="code">TW_AI_PROVIDER=openai
TW_AI_MODEL=gpt-6-luna
TW_AI_ENABLED=false
${esc(prefix)}OPENAI_API_KEY=ENTER_ON_SERVER
${esc(prefix)}ALLOW_PAID=false</div><p class="hint">OpenAI needs explicit paid-call approval. Keep activation off until approved. Local inference requires a separately installed Ollama model.</p></details></div></section>`;
}

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
