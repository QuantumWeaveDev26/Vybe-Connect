'use strict';
// Original vector characters; no external image requests or copied character assets.
// Presets have intentional identities; custom names use a stable full-string hash.
const CHARACTER_NAMES=['Daily Digest','Inbox Triage','Re-engagement Scout','Urgency Watcher','Top Topics','Spam Watcher','Ready-to-Buy','Automation Health Check','Campaign Readiness Checker','Segment & Contact Checker','Campaign Idea Finder','Account Health Checker','Admissions inquiry & Counseling','Course discovery','Student support & FAQ','Appointment booking & reschedules','Customer concierge','Property inquiries','Shopping assistant','Order support'];
function characterAvatar(seed='Agent'){
 const name=String(seed),known=CHARACTER_NAMES.indexOf(name);
 const conceptPortraits={'Inbox Triage':0,'Daily Digest':1,'Re-engagement Scout':2,'Urgency Watcher':3,'Top Topics':4,'Spam Watcher':5};
 if(Object.prototype.hasOwnProperty.call(conceptPortraits,name))return `<span class="character-avatar concept-portrait portrait-${conceptPortraits[name]}" aria-hidden="true"></span>`;
 let hash=2166136261;for(const c of name)hash=Math.imul(hash^c.codePointAt(0),16777619)>>>0;
 const identity=known<0?hash:known;
 const skin=['#f0c4a4','#b77b55','#d99f78','#8f5b42','#e5b28b'][identity%5];
 const hair=['#493127','#242d34','#a96037','#302823','#68534b'][Math.floor(identity/2)%5];
 const shirt=['#23775d','#347e9b','#a75c43','#625d92','#b58126','#41766d'][identity%6];
 const bg=['#e5f4ed','#e7f2fa','#fff0e5','#eeebf8','#fff5d9','#e8f3f1'][identity%6];
 const style=identity%6;
 const hairBack=style===1?'<path d="M12 27C8 3 53 1 53 29v29H12Z" fill="'+hair+'"/>':style===3?'<circle cx="33" cy="10" r="10" fill="'+hair+'"/>':'';
 const hairFront=[
  'M13 27C8 6 25 0 39 7c14-2 17 16 10 22l-4-14C34 25 23 14 13 27',
  'M13 28C9 8 23 3 34 5c20-2 22 18 15 24l-7-17c-5 12-22 4-29 16',
  'M12 28C6 16 13 4 24 7c4-10 17-6 19 0 13-2 17 17 6 22l-5-12c-12 6-20-3-26 7Z',
  'M13 26C9 7 25 2 35 5c17 0 22 13 14 24l-4-12c-7 4-22 4-29 2Z',
  'M13 25C8 9 24 1 36 6c17-4 20 18 13 23l-5-14-10 2-9-5-7 15Z',
  'M13 27C9 8 22 1 35 5c17-1 23 18 14 24l-5-11c-12 12-19-5-31 9'
 ][style];
 const glasses=identity%4===1?'<g fill="none" stroke="#263e48" stroke-width="2"><rect x="15" y="28" width="16" height="12" rx="5"/><rect x="34" y="28" width="16" height="12" rx="5"/><path d="M31 32h3"/></g>':'';
 const accessory=identity%4===2?'<g fill="none" stroke="#234f49" stroke-width="2.5"><path d="M11 30c-3-28 45-28 43 0M51 42l-8 5"/><rect x="9" y="29" width="5" height="13" rx="2"/><rect x="50" y="29" width="5" height="13" rx="2"/></g>':identity%4===3?'<path d="M21 42q11 22 22 0l-4 11H26Z" fill="'+hair+'" opacity=".8"/>':'';
 return `<span class="character-avatar" aria-hidden="true" style="background:${bg}"><svg viewBox="0 0 64 72">${hairBack}<path d="M4 74c1-18 13-23 28-23s27 5 28 23" fill="${shirt}"/><path d="M25 46h14v12c-4 6-10 6-14 0" fill="${skin}"/><ellipse cx="32" cy="31" rx="18" ry="23" fill="${skin}"/><path d="${hairFront}" fill="${hair}"/><path d="M19 28q5-4 10 0M36 28q5-4 10 0" stroke="${hair}" stroke-width="2" fill="none"/><ellipse cx="24" cy="34" rx="2" ry="2.4" fill="#302a29"/><ellipse cx="40" cy="34" rx="2" ry="2.4" fill="#302a29"/><path d="M31 35l-2 7h5" fill="none" stroke="#965e47" stroke-width="1.3"/>${accessory}<path d="M25 46q7 8 14 0" fill="#fff" stroke="#9c5c48" stroke-width="1.1"/>${glasses}<path d="M21 59l11 9 11-9" fill="#fff" opacity=".85"/></svg></span>`;
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

// Original activity scenes for campaign metrics, separate from the AI team portraits.
function metricIllustration(label){
 const scenes={
 'Total contacts':`<circle cx="84" cy="70" r="53" fill="#e2f5ec"/><rect x="20" y="24" width="36" height="49" rx="9" fill="#fff" stroke="#b8dfcf"/><circle cx="38" cy="40" r="7" fill="#9acdb8"/><path d="M27 61q11-21 22 0" fill="#c5e7d8"/><path d="M81 32c-17-8-33 8-28 30l-5 30h54l-5-37Z" fill="#33473e"/><path d="M42 128q0-42 35-42t36 42" fill="#e8b774"/><path d="M52 112q5-17 16-20l11 27 12-26 15 24v11H51" fill="#f5ca8d"/><path d="M69 76h17v19q-9 12-17-1" fill="#bd7e5a"/><ellipse cx="77" cy="56" rx="20" ry="26" fill="#ce956e"/><path d="M56 52q-6-33 21-32 26 1 22 32L87 36q-9 13-31 16" fill="#33473e"/><path d="M63 52q4-3 8 0m13 0q4-3 8 0" fill="none" stroke="#544032" stroke-width="2"/><circle cx="68" cy="58" r="1.8" fill="#2b342d"/><circle cx="86" cy="58" r="1.8" fill="#2b342d"/><path d="M71 70q7 6 13-1" fill="#fff"/><rect x="91" y="75" width="41" height="51" rx="7" fill="#008e65"/><rect x="96" y="80" width="31" height="42" rx="4" fill="#c4ead6"/><circle cx="112" cy="94" r="6" fill="#78b499"/><path d="M103 111q9-17 18 0" fill="#78b499"/><path d="M89 103q9-8 14-1v11q-5 6-12 3" fill="#ce956e"/>`,
 'Campaigns':`<circle cx="81" cy="71" r="53" fill="#fff1da"/><path d="M34 128q0-43 37-43t35 43" fill="#0d7864"/><path d="M59 76h17v19q-8 10-17 0" fill="#9c6747"/><ellipse cx="68" cy="55" rx="21" ry="27" fill="#b37b55"/><path d="M46 49q-6-25 10-27 1-15 18-7 24-3 15 35l-8-15q-20 9-35 14" fill="#263d35"/><path d="M50 49q4-3 9 0m13 0q5-3 10 0" stroke="#46372c" stroke-width="2" fill="none"/><circle cx="56" cy="56" r="2" fill="#29342c"/><circle cx="77" cy="56" r="2" fill="#29342c"/><path d="M59 69q8 9 15-1" fill="#fff"/><path d="M88 104l15-30 10 8-8 38" fill="#b37b55"/><path d="M100 72l8-15q7-3 11 4l-6 22Z" fill="#c68f68"/><path d="M100 55l35-15v42l-35-13Z" fill="#efac52"/><path d="M135 40q15 20 0 42Z" fill="#ffe7b4" stroke="#e6ac60"/><rect x="90" y="55" width="18" height="15" rx="4" fill="#fff8e8"/><path d="M105 70l5 15h9l-6-15" fill="#d28a3e"/><g stroke="#dda24b" stroke-width="2.5" stroke-linecap="round"><path d="M144 30l5-7M150 51h7M145 91l6 6"/></g><path d="M21 43l6 4 6-4-6-4Z" fill="#eed89c"/>`,
 'Queued messages':`<circle cx="80" cy="70" r="53" fill="#e8f0fb"/><path d="M28 128q1-41 38-41t39 41" fill="#637fa4"/><path d="M56 76h17v18q-8 13-17 0" fill="#e3b28a"/><path d="M45 48q-7-24 18-28 27 0 24 27v25H44" fill="#82523c"/><ellipse cx="65" cy="56" rx="21" ry="27" fill="#efc7a5"/><path d="M43 49q-3-28 24-30 29 4 21 31L72 32q-10 15-29 17" fill="#82523c"/><circle cx="55" cy="56" r="1.8" fill="#33403b"/><circle cx="75" cy="56" r="1.8" fill="#33403b"/><path d="M58 70q8 7 14-1" fill="#fff"/><path d="M40 53q-1-36 26-35 29 0 26 38M88 66l-11 6" stroke="#2e5267" stroke-width="4" fill="none"/><rect x="38" y="49" width="6" height="17" rx="3" fill="#45748b"/><rect x="87" y="49" width="6" height="17" rx="3" fill="#45748b"/><rect x="76" y="96" width="67" height="30" rx="5" fill="#a6c2d8"/><path d="M78 100h61l-10 26H69Z" fill="#cbdde9"/><circle cx="108" cy="114" r="3" fill="#fff"/><path d="M52 112l26 5M124 91l8 7" stroke="#efc7a5" stroke-width="9" stroke-linecap="round"/><rect x="103" y="19" width="39" height="28" rx="8" fill="#fff" stroke="#bed6e8"/><path d="M111 29h22m-22 8h14" stroke="#88aac2" stroke-width="2" stroke-linecap="round"/><path d="M111 46l-5 8v-9" fill="#fff"/>`,
 'Opted-in audience':`<circle cx="81" cy="72" r="53" fill="#e8f4e3"/><path d="M30 129q0-41 37-41t37 41" fill="#718a66"/><path d="M58 77h17v18q-8 11-17-1" fill="#dca77c"/><ellipse cx="67" cy="56" rx="21" ry="27" fill="#ebbd91"/><path d="M45 47q-5-28 22-29 26 0 24 27l-12-14q-17 8-34 16" fill="#c6c9bc"/><path d="M47 61q2 27 19 28 21-3 23-30l-11 9-12 10-13-11Z" fill="#d6d8ca"/><path d="M59 72q7 6 13-1" fill="#fff"/><circle cx="56" cy="54" r="8" stroke="#45614c" stroke-width="2" fill="none"/><circle cx="78" cy="54" r="8" stroke="#45614c" stroke-width="2" fill="none"/><path d="M64 53h6" stroke="#45614c" stroke-width="2"/><circle cx="56" cy="54" r="1.5" fill="#344733"/><circle cx="78" cy="54" r="1.5" fill="#344733"/><path d="M99 63l29-9 27 10v28q-2 25-28 38-26-14-28-39Z" fill="#159269"/><path d="M105 68l23-7 20 7v22q-2 20-21 31-20-12-22-31Z" fill="#bce8ca"/><path d="M114 89l9 10 15-21" stroke="#12835e" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M91 106q6-10 14-2l2 12q-10 6-17-1" fill="#ebbd91"/><path d="M26 32l4 6 7 1-5 5 1 7-7-3-6 3 1-7-5-5 7-1Z" fill="#c6dfb3"/>`
 };
 const scene=scenes[label];return scene?`<span class="metric-illustration" aria-hidden="true"><svg viewBox="0 0 160 140" focusable="false" aria-hidden="true">${scene}</svg></span>`:'';
}
