'use strict';
let segmentEditorState=null;
const SEGMENT_FIELDS=[['name','Name'],['phone','Phone'],['tags','Tags'],['optin','Marketing consent'],['status','Conversation status'],['assignee','Assigned teammate'],['source','Source'],['last_inbound','Last inbound timestamp'],['custom','Custom attribute']];
const SEGMENT_OPERATORS=[['eq','Equals'],['ne','Does not equal'],['contains','Contains'],['not_contains','Does not contain'],['starts_with','Starts with'],['ends_with','Ends with'],['gt','Greater than'],['gte','At least'],['lt','Less than'],['lte','At most'],['date_before','Before date'],['date_after','After date'],['exists','Exists'],['not_exists','Missing'],['empty','Empty'],['not_empty','Not empty']];
function segmentOperators(field){return SEGMENT_OPERATORS.filter(([op])=>field==='optin'?['eq','ne'].includes(op):field==='tags'?['contains','not_contains','exists','not_exists','empty','not_empty'].includes(op):true)}
function segmentValueControl(field,value){
  const options=field==='assignee'?[['','Unassigned'],...(S.data.members||[]).map(m=>[m.id,m.name])]:field==='optin'?[['true','Opted in'],['false','Not opted in']]:null;
  return options?`<select data-segment-value>${options.map(([v,label])=>`<option value="${esc(v)}" ${String(value)===v?'selected':''}>${esc(label)}</option>`).join('')}</select>`:`<input data-segment-value value="${esc(value??'')}" placeholder="Comparison value">`;
}
function segmentsPage(){
  const admin=S.data.context.role==='admin';return pagehead('Contact segments','Save dynamic audiences using contact fields, tags and custom attributes.',btn('New segment','segment-new',admin?'':'disabled','primary'))+`<section class="card"><div class="tablewrap"><table><thead><tr><th>Segment</th><th>Match rules</th><th>Updated</th><th>Actions</th></tr></thead><tbody>${(S.data.segments||[]).map(s=>`<tr><td><strong>${esc(s.name)}</strong></td><td>${s.criteria.mode==='any'?'Any':'All'} of ${s.criteria.rules?.length||1} conditions</td><td>${esc(new Date(s.updated*1000).toLocaleString())}</td><td>${btn('Preview audience','segment-preview-saved',`data-id="${esc(s.id)}"`,'small')}${btn('Edit','segment-edit',`data-id="${esc(s.id)}" ${admin?'':'disabled'}`,'small')}${btn('Delete','segment-delete',`data-id="${esc(s.id)}" ${admin?'':'disabled'}`,'small ghost')}</td></tr>`).join('')||'<tr><td colspan="4">No saved segments. Add conditions to define an audience.</td></tr>'}</tbody></table></div></section><p class="hint">A segment does not grant consent. Campaigns use the latest matching contacts at launch and recheck consent before every queued send. Date-only comparisons use UTC midnight; date-times need an explicit offset.</p>`;
}
function captureSegmentRules(){return [...document.querySelectorAll('[data-segment-rule]')].map(row=>{
  const selected=row.querySelector('[data-segment-field]').value,field=selected==='custom'?'attributes.'+row.querySelector('[data-segment-key]').value.trim():selected,operator=row.querySelector('[data-segment-operator]').value;
  const rule={field,operator};if(['exists','not_exists','empty','not_empty'].includes(operator))return rule;
  const raw=row.querySelector('[data-segment-value]').value,type=selected==='optin'?'boolean':row.querySelector('[data-segment-type]').value;
  rule.value=type==='number'?Number(raw):type==='boolean'?raw==='true':raw;
  if(type==='number'&&(!raw.trim()||!Number.isFinite(rule.value)))throw new Error('Enter a finite numeric filter value.');
  if(type==='boolean'&&!['true','false'].includes(raw))throw new Error('Boolean values must be true or false.');
  return rule;
})}
function paintSegmentRules(){
  $('#segment-rules').innerHTML=segmentEditorState.rules.map((r,index)=>{const custom=r.field.startsWith('attributes.'),selected=custom?'custom':r.field;return `<section data-segment-rule class="cardbody"><strong>Condition ${index+1}</strong><div class="field"><label>Contact field<select data-segment-field>${SEGMENT_FIELDS.map(([value,label])=>`<option value="${value}" ${value===selected?'selected':''}>${label}</option>`).join('')}</select></label></div><div class="field"><label>Custom attribute key<input data-segment-key value="${esc(custom?r.field.slice(11):'')}" placeholder="Used only for custom attributes"></label></div><div class="field"><label>Comparison<select data-segment-operator>${segmentOperators(selected).map(([value,label])=>`<option value="${value}" ${value===r.operator?'selected':''}>${label}</option>`).join('')}</select></label></div><div class="field"><label>Value type<select data-segment-type><option value="text">Text or ISO date</option><option value="number" ${typeof r.value==='number'?'selected':''}>Number</option><option value="boolean" ${typeof r.value==='boolean'?'selected':''}>True / false</option></select></label></div><div class="field"><label>Value${segmentValueControl(selected,r.value)}</label></div>${btn('Remove condition','segment-remove-rule',`data-index="${index}" ${segmentEditorState.rules.length===1?'disabled':''}`,'small ghost')}</section>`}).join('');
}
function currentSegmentCriteria(){return {mode:$('#f-match_mode').value,rules:captureSegmentRules()}}
function segmentForm(segment={}){
  const rules=segment.criteria?.rules||(segment.criteria?.field?[segment.criteria]:[]);
  if(rules.some(r=>r.rules||!SEGMENT_OPERATORS.some(([op])=>op===r.operator))){toast('This segment uses nested groups or API-only operators. The visual editor cannot preserve those conditions.');return}
  segmentEditorState={tenant:S.data.context.tenant_id,user:S.data.context.user.id,rules:(rules.length?rules:[{field:'tags',operator:'contains',value:''}]).map(r=>({...r}))};
  showModal(segment.id?'Edit segment':'New contact segment',field('name','Segment name',segment.name||'')+field('match_mode','Match conditions',segment.criteria?.mode||'all','select',[['all','All conditions (AND)'],['any','Any condition (OR)']])+'<div id="segment-rules"></div>'+btn('Add condition','segment-add-rule','','small')+btn('Preview matches','segment-preview-editor','','small')+'<div id="segment-preview"></div><p class="hint">Use numeric comparisons with Number values. Consent uses true/false and Equals. Exists/Empty comparisons ignore the value. Up to twenty conditions.</p>',async data=>{if(!segmentScopeCurrent())throw new Error('Workspace changed. Reopen the segment editor.');await act('segment.save',{id:segment.id,name:data.name,criteria:currentSegmentCriteria()});$('#modal').close();await refresh();toast('Dynamic contact segment saved.');},'Save segment');paintSegmentRules();
}
function segmentScopeCurrent(){return S.data?.context.tenant_id===segmentEditorState.tenant&&S.data?.context.user.id===segmentEditorState.user}
document.addEventListener('change',e=>{
  if(!e.target.matches('[data-segment-field],[data-segment-operator]'))return;
  const row=e.target.closest('[data-segment-rule]'),field=row.querySelector('[data-segment-field]').value,operator=row.querySelector('[data-segment-operator]'),type=row.querySelector('[data-segment-type]');let value=row.querySelector('[data-segment-value]');
  if(e.target.matches('[data-segment-field]')){const old=operator.value;operator.innerHTML=segmentOperators(field).map(([op,label])=>`<option value="${op}" ${op===old?'selected':''}>${label}</option>`).join('');row.querySelector('[data-segment-key]').disabled=field!=='custom';value.outerHTML=segmentValueControl(field,value.value);value=row.querySelector('[data-segment-value]');if(field==='assignee')type.value='text'}
  if(field==='optin'){type.value='boolean';if(!['true','false'].includes(value.value))value.value='true'}
  else if(['gt','gte','lt','lte'].includes(operator.value))type.value='number';
  else if(['date_before','date_after'].includes(operator.value))type.value='text';
});
function segmentPreviewHTML(result){return `<p><strong>${result.count} matching contacts</strong> · ${result.opted_in} opted in</p>${result.sample.map(c=>`<div class="summaryrow"><span>${esc(c.name)} · +${esc(c.phone)}</span>${badge(c.optin?'Opted in':'No campaign consent','gray')}</div>`).join('')}<p class="hint">Showing up to 20 matching contacts. A preview does not send or enroll anyone.</p>`}
async function segmentAction(action,el){
  const segment=(S.data.segments||[]).find(s=>s.id===el.dataset.id);
  if(action==='segment-new'||action==='segment-edit')return segmentForm(segment||{});
  if(action==='segment-add-rule'||action==='segment-remove-rule'){if(!segmentScopeCurrent())throw new Error('Workspace changed.');segmentEditorState.rules=captureSegmentRules();if(action==='segment-add-rule'){if(segmentEditorState.rules.length>=20)throw new Error('Use up to twenty conditions.');segmentEditorState.rules.push({field:'name',operator:'contains',value:''})}else segmentEditorState.rules.splice(Number(el.dataset.index),1);return paintSegmentRules()}
  if(action==='segment-preview-editor'){
    const criteria=currentSegmentCriteria(),fingerprint=JSON.stringify(criteria),tenant=S.data.context.tenant_id,user=S.data.context.user.id;const result=await act('segment.preview',{criteria});
    if(S.data?.context.tenant_id!==tenant||S.data?.context.user.id!==user||!$('#modal').open||!$('#segment-preview')||JSON.stringify(currentSegmentCriteria())!==fingerprint)return;
    $('#segment-preview').innerHTML=segmentPreviewHTML(result);return;
  }
  if(action==='segment-preview-saved'){
    const tenant=S.data.context.tenant_id,user=S.data.context.user.id,result=await act('segment.preview',{criteria:segment.criteria});
    if(S.data?.context.tenant_id!==tenant||S.data?.context.user.id!==user)return;
    return showModal(segment.name,segmentPreviewHTML(result),()=>$('#modal').close(),'Close');
  }
  if(action==='segment-delete'){
    const tenant=S.data.context.tenant_id,user=S.data.context.user.id;
    return showModal('Delete saved segment','<p>Draft campaigns using this segment will need a new audience before launch. Already queued campaigns retain their enrolled recipients.</p>',async()=>{if(S.data?.context.tenant_id!==tenant||S.data?.context.user.id!==user)throw new Error('Workspace changed. Reopen this segment.');await act('segment.delete',{id:segment.id});$('#modal').close();await refresh()},'Delete segment');
  }
}
