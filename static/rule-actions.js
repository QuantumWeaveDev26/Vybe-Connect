'use strict';
const ruleTriggerNames={incoming_message:'Incoming message',contact_created:'Contact created',contact_updated:'Contact updated',attribute_added:'Custom attribute added',attribute_changed:'Custom attribute changed',conversation_opened:'Conversation opened',conversation_resolved:'Conversation resolved',customer_no_response:'Customer has not replied'};
function ruleTriggerSummary(rule){const event=rule.event||'incoming_message';return esc((ruleTriggerNames[event]||event)+(event==='incoming_message'?' · '+rule.keyword:event==='customer_no_response'?' · '+rule.wait_seconds+' seconds':rule.trigger_attribute?' · '+rule.trigger_attribute:''))}
const ruleActionOrder=['attribute','untag','tag','assign','status','draft','task','handoff'];
const ruleActionNames={attribute:'Set attribute',untag:'Remove tag',tag:'Add tag',assign:'Assign teammate',status:'Change status',draft:'Create draft',task:'Create task',handoff:'Human handoff'};
function ruleActionSummary(rule){return esc((rule.actions||[{type:'draft'}]).map(a=>ruleActionNames[a.type]||a.type).join(' → '))}
function canEditRuleActions(actions){
  return actions.every((a,i)=>ruleActionOrder.includes(a.type)&&(!i||ruleActionOrder.indexOf(a.type)>ruleActionOrder.indexOf(actions[i-1].type)));
}
function richRuleForm(rule={}){
  if(S.data.context.role!=='admin')throw new Error('Administrator access required.');
  const tenant=S.data.context.tenant_id,user=S.data.context.user.id;
  const same=()=>S.data?.context.tenant_id===tenant&&S.data?.context.user.id===user;
  const actions=rule.actions||[{type:'draft',value:rule.reply||''}],editable=canEditRuleActions(actions),byType=Object.fromEntries(actions.map(a=>[a.type,a]));
  const segments=[['','All contacts'],...(S.data.segments||[]).map(s=>[s.id,s.name])];
  if(rule.segment_id&&!segments.some(s=>s[0]===rule.segment_id))segments.push([rule.segment_id,'Missing saved segment · choose a replacement']);
  const members=[['','Keep current assignment'],...S.data.members.map(m=>[m.id,m.name])];
  if(byType.assign&&!members.some(m=>m[0]===byType.assign.value))members.push([byType.assign.value,'Unavailable member · choose a replacement']);
  let fields=field('name','Rule name',rule.name||'')+field('event','Trigger',rule.event||'incoming_message','select',Object.entries(ruleTriggerNames))+field('trigger_attribute','Trigger attribute name · optional for attribute events',rule.trigger_attribute||'')+field('keyword','Incoming message contains',rule.keyword||'')+field('priority','Priority · lower numbers run first',rule.priority??100,'number')+field('segment_id','Also require saved contact segment',rule.segment_id||'','select',segments);
  fields+=field('wait_seconds','No-response wait · seconds (1–604800)',rule.wait_seconds??3600,'number')+'<p class="hint">No-response rules begin after a newly accepted real outbound reply. Saving starts fresh; older replies are excluded. A real customer reply, STOP or human handoff cancels the watch.</p>';
  if(editable)fields+='<p class="hint">Leave unused actions blank. Actions run in the order below, once for each matching event. Nothing is sent externally.</p>'+field('attribute_field','Custom attribute name (optional)',byType.attribute?.field||'')+field('attribute_value','Custom attribute value',byType.attribute?.value||'')+field('untag','Remove tag',byType.untag?.value||'')+field('tag','Add tag',byType.tag?.value||'')+field('assign','Assign teammate',byType.assign?.value||'','select',members)+field('status','Set conversation status',byType.status?.value||'','select',[['','Keep current status'],['open','Open'],['pending','Pending'],['solved','Solved']])+field('draft','Create unsent reply draft · supports {{name}}',byType.draft?.value||'','textarea')+field('task','Internal follow-up task title',byType.task?.value||'')+field('handoff','Finally hand off to a human and pause automation',!!byType.handoff,'checkbox');
  else fields+='<p class="hint">This rule has repeated or custom-ordered actions. Its action sequence is retained when editing these settings.</p><p>'+ruleActionSummary(rule)+'</p>';
  fields+=field('enabled','Enable this rule',rule.enabled??true,'checkbox');
  showModal(rule.id?'Edit automation rule':'Create automation rule',fields,async data=>{
    if(!same())throw new Error('Workspace changed. Reopen the rule.');
    let updated=actions;
    if(editable){
      updated=[];
      if(data.attribute_field||data.attribute_value){if(!data.attribute_field||!data.attribute_value)throw new Error('Provide both an attribute name and value.');updated.push({type:'attribute',field:data.attribute_field,value:data.attribute_value})}
      for(const type of ['untag','tag','assign','status','draft','task'])if(data[type]?.trim())updated.push({type,value:data[type].trim()});
      if(data.handoff)updated.push({type:'handoff'});
    }
    await act('rule.save',{id:rule.id,name:data.name,keyword:data.keyword||'',event:data.event,wait_seconds:data.event==='customer_no_response'?Number(data.wait_seconds):undefined,trigger_attribute:['attribute_added','attribute_changed'].includes(data.event)?data.trigger_attribute||'':'',priority:Number(data.priority),segment_id:data.segment_id,actions:updated,reply:updated.find(a=>a.type==='draft')?.value||'',enabled:data.enabled});
    if(!same())return;$('#modal').close();await refresh();toast('Local rule saved.');
  },'Save rule');
  const triggerControls=()=>{const event=$('#f-event').value;$('#f-keyword').required=event==='incoming_message';$('#f-keyword').disabled=event!=='incoming_message';$('#f-trigger_attribute').disabled=!['attribute_added','attribute_changed'].includes(event);$('#f-wait_seconds').disabled=event!=='customer_no_response';$('#f-wait_seconds').required=event==='customer_no_response'};
  $('#f-trigger_attribute').required=false;$('#f-event').onchange=triggerControls;triggerControls();
  $('#f-priority').min='0';$('#f-priority').max='1000';
  $('#f-wait_seconds').min='1';$('#f-wait_seconds').max='604800';$('#f-wait_seconds').step='1';
  if(editable)for(const name of ['attribute_field','attribute_value','untag','tag','draft','task'])$('#f-'+name).required=false;
}

function ruleExecutionPanel(){
  const history=[...(S.data.rule_executions||[])].reverse();
  return `<section class="card"><div class="cardhead"><h2>Recent rule executions</h2>${badge('Latest 100','gray')}</div><div class="tablewrap"><table><thead><tr><th>Rule</th><th>Trigger</th><th>Contact</th><th>Result</th><th>Time</th></tr></thead><tbody>${history.map(run=>`<tr><td>${esc(S.data.rules.find(r=>r.id===run.rule_id)?.name||'Deleted rule')}</td><td>${esc(ruleTriggerNames[run.event]||run.event)}</td><td>${esc(S.data.contacts.find(c=>c.id===run.contact_id)?.name||'Contact')}</td><td>${badge(run.status,run.status==='blocked'?'amber':'gray')}${run.reason?`<p class="sub">${esc(run.reason)}</p>`:''}</td><td>${esc(new Date(run.created*1000).toLocaleString())}</td></tr>`).join('')||'<tr><td colspan="5">No rule executions recorded yet.</td></tr>'}</tbody></table></div></section>`;
}

function noResponseHistoryPanel(){
  const history=[...(S.data.no_response_evaluations||[])].reverse();
  return `<section class="card"><div class="cardhead"><h2>No-response evaluations</h2>${badge('Latest 100','gray')}</div><p class="hint">Each rule evaluates once per accepted reply. Not applied means its current segment or dependencies did not allow the actions.</p><div class="tablewrap"><table><thead><tr><th>Rule</th><th>Contact</th><th>Due</th><th>Evaluated</th><th>Result</th></tr></thead><tbody>${history.map(run=>`<tr><td>${esc(S.data.rules.find(r=>r.id===run.rule_id)?.name||'Deleted rule')}</td><td>${esc(S.data.contacts.find(c=>c.id===run.contact_id)?.name||'Contact')}</td><td>${esc(new Date(run.due*1000).toLocaleString())}</td><td>${esc(new Date(run.processed*1000).toLocaleString())}</td><td>${badge(run.status==='applied'?'Applied':'Not applied',run.status==='applied'?'':'gray')}</td></tr>`).join('')||'<tr><td colspan="5">No no-response evaluations recorded yet.</td></tr>'}</tbody></table></div></section>`;
}
