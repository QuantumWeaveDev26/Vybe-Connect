'use strict';
function manualWhatsAppURL(phone){
 const number=String(phone||'').replace(/^\+/,'');
 return /^[1-9]\d{6,14}$/.test(number)?'https://wa.me/'+number:'';
}
function manualWhatsAppAction(contact){
 if(!contact||contact.channel==='website')return '';
 const url=manualWhatsAppURL(contact.phone);
 if(!url)return '';
 return `<a class="button small manual-whatsapp-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer" title="Opens WhatsApp. Messages are not synced to VYBE.">Open in WhatsApp <span aria-hidden="true">&#8599;</span></a>`;
}
function manualWhatsAppBanner(contact){
 const action=manualWhatsAppAction(contact);
 if(!action)return '';
 return `<div class="manual-whatsapp-banner"><div><strong>Reply in WhatsApp</strong><span>Replies stay in WhatsApp. Use Notes to leave an update for your team.</span></div>${action}</div>`;
}
function manualWhatsAppSettings(){
 return '<section class="card"><div class="cardhead"><h2>Use the CRM with your existing number</h2></div><div class="cardbody"><p>Open a contact and select <strong>Open in WhatsApp</strong>. Send from WhatsApp, then track notes and follow-ups in VYBE.</p><p class="hint">Messages sent this way stay in WhatsApp.</p><a class="button primary manual-contacts-action" href="#contacts">Open contacts</a></div></section>';
}
