'use strict';
function manualWhatsAppURL(phone,body=''){
 const number=String(phone||'').replace(/^\+/,'');
 if(!/^[1-9]\d{6,14}$/.test(number))return '';
 const text=typeof body==='string'?body.slice(0,4000):'';
 try{return 'https://wa.me/'+number+(text?'?text='+encodeURIComponent(text):'')}catch{return ''}
}
function manualWhatsAppAction(contact,body='',draft=false){
 if(!contact||contact.channel==='website')return '';
 const url=manualWhatsAppURL(contact.phone,body);if(!url)return '';
 return `<a class="button small manual-whatsapp-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer" ${draft?`data-manual-draft data-phone="${esc(contact.phone)}"`:''} title="Opens WhatsApp. You send there; messages and delivery status are not synced to VYBE.">Open in WhatsApp</a>`;
}
function manualWhatsAppSettings(){
 return '<section class="card"><div class="cardhead"><h2>WhatsApp on your phone</h2><span class="badge gray">Opens WhatsApp</span></div><div class="cardbody"><p>Manage contacts, notes and follow-ups in VYBE. Use Open in WhatsApp on a contact to send from your phone account.</p><p class="hint">Phone chats stay in WhatsApp. Connect the WhatsApp Business API for synced conversations and automated sending.</p><a class="primary manual-contacts-action" href="#contacts">Open contacts</a></div></section>';
}
document.addEventListener('input',event=>{
 if(event.target.id!=='compose')return;
 const link=document.querySelector('[data-manual-draft]');if(!link)return;
 const url=manualWhatsAppURL(link.dataset.phone,event.target.value);if(url)link.href=url;
});
