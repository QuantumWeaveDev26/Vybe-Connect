'use strict';
// Original 3D artwork served locally; no third-party avatar requests.
// Presets have intentional identities; custom names use a stable full-string hash.
const CHARACTER_NAMES=['Daily Digest','Inbox Triage','Re-engagement Scout','Urgency Watcher','Top Topics','Spam Watcher','Ready-to-Buy','Automation Health Check','Campaign Readiness Checker','Segment & Contact Checker','Campaign Idea Finder','Account Health Checker','Admissions inquiry & Counseling','Course discovery','Student support & FAQ','Appointment booking & reschedules','Customer concierge','Property inquiries','Shopping assistant','Order support'];
function characterAvatar(seed='Agent'){
 const name=String(seed),known=CHARACTER_NAMES.indexOf(name);let hash=2166136261;
 for(const c of name)hash=Math.imul(hash^c.codePointAt(0),16777619)>>>0;
 // Twelve distinct preset identities; the last six have role-specific original artwork.
 const faces=[1,0,2,3,4,5,10,11,12,13,14,15,16,17,18,19,20,21,22,23];
 const face=known<0?hash%6:faces[known];
 if(face>=16)return `<span class="character-avatar template-portrait template-portrait-${face-16}" aria-hidden="true"></span>`;
 if(face>=10)return `<span class="character-avatar role-portrait role-portrait-${face-10}" aria-hidden="true"></span>`;
 return face<6?`<span class="character-avatar concept-portrait portrait-${face}" aria-hidden="true"></span>`:`<span class="character-avatar character-clean portrait-clean-${face-6}" aria-hidden="true"></span>`;
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

// The four approved 3D characters are displayed smaller than the design preview.
function metricIllustration(label){
 const variants={'Total contacts':'contacts','Campaigns':'campaigns','Queued messages':'messages','Opted-in audience':'consent'};
 const kind=variants[label];return kind?`<span class="metric-illustration metric-character-v2 metric-character-clean metric-${kind}" aria-hidden="true"></span>`:'';
}

function supportPortrait(variant){
 const kind=['contacts','campaigns','messages','consent'].includes(variant)?variant:'messages';
 return `<span class="support-portrait support-${kind}" aria-hidden="true"></span>`;
}
