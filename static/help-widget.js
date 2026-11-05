'use strict';
const HELP={scope:null,open:false,tab:'help',rating:0,draft:'',category:'feedback',tour:null,surveyDismissed:false};
const HELP_STEPS=[
 {selector:'.sidebar nav a[href="#inbox"]',title:'Your team inbox',text:'Read customer conversations, assign teammates, add private notes and review drafts.',route:'inbox'},
 {selector:'.sidebar nav a[href="#campaigns"]',title:'Campaigns and templates',text:'Create templates and plan campaigns. Provider approval and sending settings are checked separately.',route:'campaigns'},
 {selector:'.sidebar nav a[href="#external-agents"]',title:'Astra / Custom AI',text:'Connect your own signed webhook agent and review its event delivery and reply drafts.',route:'external-agents'},
 {selector:'.sidebar nav a[href="#ai-agents"]',title:'AI agents',text:'Manage your agents, business knowledge and findings.',route:'ai-agents'},
 {selector:'.sidebar nav a[href="#rules"]',title:'Automations',text:'Find rules, visual chatbots, sequences and AI customer replies in the automation menu.',route:'rules'},
 {selector:'.help-launcher',title:'Help and feedback',text:'Return here for walkthroughs, your AI assistant and the feedback inbox. Feedback is saved to this workspace.'}
];
function clearHelpWidget(){HELP.scope=null;HELP.open=false;HELP.tab='help';HELP.rating=0;HELP.draft='';HELP.category='feedback';HELP.tour=null;HELP.surveyDismissed=false;document.querySelector('#help-widget')?.remove();document.querySelector('#guided-tour')?.remove()}
function helpScope(){return S.data?S.data.context.tenant_id+':'+S.data.context.user.id:null}
function helpStars(){return `<div class="help-stars" role="group" aria-label="Rate your experience from one to five">${[1,2,3,4,5].map(r=>`<button type="button" data-do="help-rate" data-rating="${r}" aria-label="${r} out of 5 stars" aria-pressed="${HELP.rating===r}">${HELP.rating>=r?'★':'☆'}</button>`).join('')}</div>`}
function helpReports(){
 const reports=S.data.product_feedback||[],admin=S.data.context.role==='admin';
 return '<p class="hint">'+(admin?'Workspace feedback inbox.':'Your submitted feedback.')+' Reports stay in this application; no email or external support request is sent.</p>'+reports.map(r=>`<article class="help-report"><div><strong>${esc(r.category)}</strong> ${badge(r.status,'gray')} ${r.rating?`<span>${r.rating}/5</span>`:''}</div><p>${esc(r.body||'Rating submitted')}</p><small>${esc(r.page)} · ${esc(new Date(r.created*1000).toLocaleString())}</small>${admin?`<div class="buttons">${['open','reviewing','resolved'].filter(v=>v!==r.status).map(status=>btn(status,'help-status',`data-id="${esc(r.id)}" data-version="${r.version}" data-status="${status}"`,'small')).join('')}</div>`:''}</article>`).join('')+(reports.length?'':'<p class="hint">No feedback reports yet.</p>');
}
function helpPanel(){
 let body='';
 if(HELP.tab==='feedback')body=`<h3>How can we improve?</h3>${helpStars()}<div class="help-rating-labels"><span>Unsatisfied</span><span>Satisfied</span></div><form id="help-feedback-form"><div class="field"><label for="help-feedback-category">Feedback type</label><select id="help-feedback-category" name="category">${[['feedback','General feedback'],['bug','Report an issue'],['idea','Suggest a feature']].map(([id,label])=>`<option value="${id}" ${HELP.category===id?'selected':''}>${label}</option>`).join('')}</select></div><div class="field"><label for="help-feedback-body">Your feedback</label><textarea id="help-feedback-body" name="body" maxlength="4000" placeholder="Describe the issue or idea. Keep passwords and API keys out of feedback.">${esc(HELP.draft)}</textarea></div><p id="help-feedback-error" class="error"></p><button class="primary" type="submit">Send feedback</button><p class="hint">Saved to your workspace feedback inbox. No customer messages or screenshots are attached automatically.</p></form>`;
 else if(HELP.tab==='reports')body=helpReports();
 else body=`<div class="help-greeting"><div class="help-characters">${supportPortrait('contacts')}${supportPortrait('messages')}${supportPortrait('consent')}</div><p>Hi ${esc(S.data.context.user.name.split(' ')[0])} <span aria-hidden="true">&#128075;</span></p><h3>How can we help?</h3></div><div class="help-home-cards"><button type="button" class="help-home-card help-chat-card" data-do="help-ai"><strong>Ask VYBE AI</strong><span>Explore your workspace with your assistant</span><b aria-hidden="true">&#10148;</b></button><section class="help-home-card"><strong>Your VYBE guide is here</strong><div class="help-illustration">${supportPortrait('messages')}<span>Conversations.<br>Agents. Automations.</span></div>${btn('Take a guided tour &#8594;','help-tour','','help-card-link')}</section><button type="button" class="help-home-card" data-do="help-astra"><strong>Meet your custom agents</strong><span>Explore Astra and customer assistant templates &#8594;</span></button></div>`;
 return `<section class="help-panel ${HELP.tab==='help'?'help-home':''}" role="dialog" aria-label="VYBE Connect help"><header><div><strong>VYBE Connect</strong><span>Help for your workspace</span></div>${btn('×','help-close','aria-label="Close help"','ghost')}</header><div class="help-panel-body">${body}</div><nav class="help-tabs" aria-label="Help sections">${[['help','Home','inbox'],['feedback','Feedback','replies'],['reports','Inbox','templates']].map(([id,label,glyph])=>btn(icon(glyph)+'<span>'+label+'</span>','help-tab',`data-tab="${id}" aria-pressed="${HELP.tab===id}"`,HELP.tab===id?'selected':'')).join('')}</nav></section>`;
}
function renderHelpWidget(){
 if(!S.data)return clearHelpWidget();const scope=helpScope();
 if(HELP.scope!==scope){clearHelpWidget();HELP.scope=scope;HELP.surveyDismissed=localStorage.getItem('vybe-survey:'+scope)==='dismissed'}
 let root=document.querySelector('#help-widget');if(!root){root=document.createElement('div');root.id='help-widget';document.body.append(root)}
 const survey=false; // Feedback opens on demand, without covering the agent directory.
 root.innerHTML=(survey?`<section class="help-survey" aria-label="Product feedback"><button type="button" class="help-survey-close" data-do="help-dismiss-survey" aria-label="Dismiss feedback prompt">×</button><h3>How satisfied are you with Astra / Custom AI?</h3><p>Your feedback helps improve this workspace.</p>${helpStars()}<div class="help-rating-labels"><span>Unsatisfied</span><span>Satisfied</span></div>${btn('Share feedback','help-feedback','','small')}</section>`:'')+(HELP.open?helpPanel():'')+`<button type="button" class="help-launcher" data-do="help-toggle" aria-expanded="${HELP.open}" aria-label="Open VYBE Connect help and feedback"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-6l-5 4v-4H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 8h10M7 12h7"/></svg></button>`;
 const form=document.querySelector('#help-feedback-form');if(form)form.onsubmit=submitHelpFeedback;
 if(HELP.tour!==null)renderGuidedTour();
}
async function submitHelpFeedback(event){
 event.preventDefault();const scope=helpScope(),rating=HELP.rating,values=Object.fromEntries(new FormData(event.target));
 if(!rating&&!values.body.trim()){document.querySelector('#help-feedback-error').textContent='Choose a rating or write your feedback.';return}
 const submit=event.target.querySelector('[type="submit"]');submit.disabled=true;
 try{
  const report=await act('feedback.save',{rating,body:values.body,category:values.category,page:S.route});if(scope!==helpScope())return;
  HELP.draft='';HELP.rating=0;HELP.tab='reports';HELP.surveyDismissed=true;localStorage.setItem('vybe-survey:'+scope,'dismissed');await refresh();if(scope!==helpScope())return;renderHelpWidget();toast('Feedback saved. Reference '+report.id+'.');
 }catch(error){if(scope===helpScope()){const box=document.querySelector('#help-feedback-error');if(box)box.textContent=error.message;submit.disabled=false}}
}
function renderGuidedTour(){
 document.querySelector('#guided-tour')?.remove();const step=HELP_STEPS[HELP.tour];if(!step)return;
 const target=document.querySelector(step.selector);target?.scrollIntoView({block:'nearest',behavior:'auto'});
 const rect=target?.getBoundingClientRect(),width=Math.min(360,window.innerWidth-32),left=rect?Math.min(window.innerWidth-width-16,Math.max(16,rect.right+18)):16,top=rect?Math.min(window.innerHeight-250,Math.max(16,rect.top)):80;
 const root=document.createElement('div');root.id='guided-tour';root.className='tour-layer';
 root.innerHTML=(rect?`<div class="tour-highlight" style="left:${rect.left-4}px;top:${rect.top-4}px;width:${rect.width+8}px;height:${rect.height+8}px"></div>`:'')+`<section class="tour-card" role="dialog" aria-modal="true" aria-label="Guided product tour" style="left:${left}px;top:${Math.max(16,top)}px;width:${width}px"><div class="buttons"><span>${HELP.tour+1} / ${HELP_STEPS.length}</span>${btn('×','help-end-tour','aria-label="Close tour"','ghost')}</div><h3>${esc(step.title)}</h3><p>${esc(step.text)}</p><div class="buttons">${btn('Back','help-tour-back',HELP.tour===0?'disabled':'','small')}${step.route||step.ai?btn('Open this area','help-tour-open','','small'):''}${btn(HELP.tour===HELP_STEPS.length-1?'Finish':'Next','help-tour-next','','primary small')}</div></section>`;
 document.body.append(root);root.querySelector('[data-do="help-tour-next"]').focus();
}
async function helpAction(action,el){
 if(!S.data)return;const scope=helpScope();
 if(action==='help-toggle'){HELP.open=!HELP.open;HELP.tour=null;document.querySelector('#guided-tour')?.remove()}
 if(action==='help-close')HELP.open=false;
 if(action==='help-tab'){if(!['help','feedback','reports'].includes(el.dataset.tab))return;HELP.tab=el.dataset.tab}
 if(action==='help-feedback'){HELP.open=true;HELP.tab='feedback'}
 if(action==='help-reports'){HELP.open=true;HELP.tab='reports'}
 if(action==='help-rate'){HELP.rating=Number(el.dataset.rating);if(!HELP.open){HELP.open=true;HELP.tab='feedback'}}
 if(action==='help-dismiss-survey'){HELP.surveyDismissed=true;localStorage.setItem('vybe-survey:'+scope,'dismissed')}
 if(action==='help-astra'){HELP.open=false;location.hash='external-agents'}
 if(action==='help-ai'){HELP.open=false;showAI('ask')}
 if(action==='help-tour'){HELP.open=false;HELP.tour=0}
 if(action==='help-tour-back')HELP.tour=Math.max(0,HELP.tour-1);
 if(action==='help-tour-next'){HELP.tour++;if(HELP.tour>=HELP_STEPS.length)HELP.tour=null}
 if(action==='help-end-tour')HELP.tour=null;
 if(action==='help-tour-open'){const step=HELP_STEPS[HELP.tour];HELP.tour=null;if(step.route)location.hash=step.route;else if(step.ai)showAI(step.ai)}
 if(action==='help-status'){await act('feedback.status',{id:el.dataset.id,version:Number(el.dataset.version),status:el.dataset.status});if(scope!==helpScope())return;await refresh()}
 if(HELP.tour===null)document.querySelector('#guided-tour')?.remove();renderHelpWidget();
}
document.addEventListener('input',event=>{if(event.target.id==='help-feedback-body')HELP.draft=event.target.value});
document.addEventListener('change',event=>{if(event.target.id==='help-feedback-category'&&event.target.closest('#help-feedback-form'))HELP.category=event.target.value});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'&&(HELP.open||HELP.tour!==null)){HELP.open=false;HELP.tour=null;document.querySelector('#guided-tour')?.remove();renderHelpWidget();document.querySelector('.help-launcher')?.focus()}
 if(event.key==='Tab'&&HELP.tour!==null){const buttons=[...document.querySelectorAll('#guided-tour button:not(:disabled)')];if(!buttons.length)return;const first=buttons[0],last=buttons.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}
});
