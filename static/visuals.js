'use strict';
// Original vector characters; no external image requests or copied character assets.
function characterAvatar(seed='Agent'){
 const hash=[...String(seed)].reduce((n,c)=>n+c.charCodeAt(0),0),variant=hash%4;
 const skin=['#edbd98','#d39b75','#a96d4f','#f0c4a4'][variant],hair=['#78492e','#322d2d','#462a21','#54342a'][variant],shirt=['#a6d7c2','#bcb2e2','#90b6ce','#d6adc5'][variant];
 return `<span class="character-avatar" aria-hidden="true"><svg viewBox="0 0 64 72"><path d="M5 74c1-18 12-23 27-23s26 5 27 23" fill="${shirt}"/><path d="M25 46h14v12c-4 6-10 6-14 0" fill="${skin}"/><path d="M13 29C9 7 23 2 34 5c17-2 24 15 16 34l-5 15H18Z" fill="${hair}"/><ellipse cx="32" cy="31" rx="18" ry="23" fill="${skin}"/><path d="M14 25C8 8 26 0 36 6 56 2 56 24 47 28l-3-12C29 25 21 14 14 25" fill="${hair}"/><path d="M19 29q5-4 10 0M36 29q5-4 10 0" stroke="${hair}" stroke-width="2" fill="none"/><ellipse cx="24" cy="34" rx="2" ry="2.4" fill="#302a29"/><ellipse cx="40" cy="34" rx="2" ry="2.4" fill="#302a29"/><path d="M31 35l-2 7h5" fill="none" stroke="#aa7054" stroke-width="1.3"/><path d="M25 46q7 8 14 0" fill="#fff" stroke="#9c5c48" stroke-width="1.1"/>${variant%2===0?'<g fill="none" stroke="#34343a" stroke-width="1.7"><rect x="16" y="28" width="15" height="12" rx="5"/><rect x="34" y="28" width="15" height="12" rx="5"/><path d="M31 32h3"/></g>':''}${variant===1?'<path d="M15 35v19l8 2-5-27M49 31l-3 24 7-3V32" fill="'+hair+'"/>':''}<path d="M21 60l7 12h8l7-12" fill="#fff" opacity=".7"/></svg></span>`;
}
const CUSTOMER_TEMPLATES=[
 ['admissions','Admissions inquiry & Counseling','Education & EdTech','Lead qualification','lead','Capture prospective student questions, explain admissions using approved knowledge, and prepare a counseling handoff.'],
 ['courses','Course discovery','Education & EdTech','Sales','sales','Suggest courses from approved business knowledge based on student goals. Explain published schedules and pricing; hand enrollment to staff.'],
 ['students','Student support & FAQ','Education & EdTech','Support','support','Answer questions about deadlines, assignments and academic policies from approved sources. Escalate unsupported questions to staff.'],
 ['appointments','Appointment booking & reschedules','Healthcare & Clinics','Bookings','bookings','Collect appointment preferences and prepare a scheduling handoff. Calendar booking requires a separate connected integration.'],
 ['concierge','Customer concierge','General','Support','support','Answer common business questions from approved sources and prepare helpful replies for the team to review.'],
 ['property','Property inquiries','Real Estate','Lead qualification','lead','Collect property preferences and answer published listing questions. Offer a staff handoff for availability and viewings.'],
 ['shopping','Shopping assistant','Retail & E-commerce','Sales','sales','Explain published products and policies from approved knowledge. Hand off stock, checkout and order changes to staff.'],
 ['orders','Order support','Retail & E-commerce','Support','support','Answer shipping and returns policy questions from approved sources. Never invent delivery status or change an order.']
];
let TEMPLATE_PICK={id:'admissions',category:'All',query:'',scope:null};
function templateCards(){
 const list=CUSTOMER_TEMPLATES.filter(t=>(TEMPLATE_PICK.category==='All'||t[2]===TEMPLATE_PICK.category)&&(t[1]+' '+t[5]).toLowerCase().includes(TEMPLATE_PICK.query.toLowerCase()));
 if(!list.some(t=>t[0]===TEMPLATE_PICK.id))TEMPLATE_PICK.id=list[0]?.[0]||null;
 return list.map(t=>`<button type="button" class="agent-template-card" data-template-id="${t[0]}" aria-pressed="${t[0]===TEMPLATE_PICK.id}">${characterAvatar(t[1])}<span class="template-tag ${t[4]}">${t[3]}</span><h3>${t[1]}</h3><p>${t[5]}</p></button>`).join('')||'<p class="template-empty">No templates match. Try another category or search.</p>';
}
function openAgentTemplates(){
 TEMPLATE_PICK={id:'admissions',category:'All',query:'',scope:S.data.context.tenant_id+':'+S.data.context.user.id};
 showModal('Pick a template',`<p class="template-intro">Welcome back, ${esc(S.data.context.user.name)}. Give your customer assistant a starting point.</p><input id="agent-template-search" aria-label="Search agent templates" placeholder="Search templates"><nav class="template-categories" aria-label="Template categories">${['All','General','Education & EdTech','Healthcare & Clinics','Real Estate','Retail & E-commerce'].map(c=>`<button type="button" data-template-category="${esc(c)}" aria-pressed="${c==='All'}">${esc(c)}</button>`).join('')}</nav><div id="template-results" class="agent-template-grid">${templateCards()}</div><p class="template-preview-note">Templates prefill instructions for your customer assistant. Review knowledge and settings before saving. No AI calls or automatic replies are activated.</p>`,async()=>{
  if(TEMPLATE_PICK.scope!==S.data.context.tenant_id+':'+S.data.context.user.id)throw new Error('Workspace changed. Reopen templates.');
  const t=CUSTOMER_TEMPLATES.find(t=>t[0]===TEMPLATE_PICK.id);if(!t)throw new Error('Select an available template.');$('#modal').close();customerAssistantForm({name:t[1],instructions:t[5]+' Use only approved business knowledge. If facts are missing, hand off to a teammate. Do not make bookings, payments or account changes.',mode:'draft',enabled:false});
 },'Use this template');const modal=$('#modal');modal.classList.add('agent-template-modal');const form=modal.querySelector('form'),footer=form.querySelector('.modalfoot');form.after(footer);footer.querySelector('[type="submit"]').setAttribute('form','dialog-form');
}
document.addEventListener('input',event=>{if(event.target.id==='agent-template-search'){TEMPLATE_PICK.query=event.target.value;document.querySelector('#template-results').innerHTML=templateCards()}});
document.addEventListener('click',event=>{
 const card=event.target.closest('[data-template-id]'),category=event.target.closest('[data-template-category]');
 if(card){TEMPLATE_PICK.id=card.dataset.templateId;document.querySelectorAll('[data-template-id]').forEach(n=>n.setAttribute('aria-pressed',String(n.dataset.templateId===TEMPLATE_PICK.id)))}
 if(category){TEMPLATE_PICK.category=category.dataset.templateCategory;document.querySelectorAll('[data-template-category]').forEach(n=>n.setAttribute('aria-pressed',String(n===category)));document.querySelector('#template-results').innerHTML=templateCards()}
});
// A short WATI-style label on hover and keyboard focus, outside the scrollable rail.
function hideNavigationHint(){document.querySelector('#nav-hint')?.remove()}
function showNavigationHint(target){
 const link=target.closest?.('.sidebar .navlink');if(!link||document.querySelector('.shell')?.classList.contains('nav-expanded'))return hideNavigationHint();
 const label=link.dataset.navLabel||link.getAttribute('aria-label')?.split(':')[0];if(!label)return;
 hideNavigationHint();const tip=document.createElement('div');tip.id='nav-hint';tip.setAttribute('role','tooltip');tip.textContent=label;const rect=link.getBoundingClientRect();tip.style.left=(rect.right+10)+'px';tip.style.top=Math.max(8,Math.min(innerHeight-40,rect.top+(rect.height-30)/2))+'px';document.body.append(tip);
}
document.addEventListener('pointerover',event=>showNavigationHint(event.target));
document.addEventListener('pointerout',event=>{if(event.target.closest?.('.sidebar .navlink')&&!event.relatedTarget?.closest?.('.sidebar .navlink'))hideNavigationHint()});
document.addEventListener('focusin',event=>showNavigationHint(event.target));
document.addEventListener('focusout',hideNavigationHint);document.addEventListener('scroll',hideNavigationHint,true);document.addEventListener('click',hideNavigationHint);

document.addEventListener('keydown',event=>{if(event.key==='Escape')hideNavigationHint()});
