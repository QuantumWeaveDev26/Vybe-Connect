'use strict';
(()=>{
 let prompt=null;
 const standalone=()=>window.matchMedia?.('(display-mode: standalone)')?.matches||(typeof navigator!=='undefined'&&navigator.standalone===true);
 window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();prompt=event});
 window.addEventListener('appinstalled',()=>{prompt=null;document.querySelectorAll('[data-pwa-install]').forEach(button=>button.hidden=true)});
 document.addEventListener('click',async event=>{
  const button=event.target.closest?.('[data-pwa-install]');if(!button)return;
  if(standalone()){if(typeof toast==='function')toast('VYBE Connect is already open as an app.');return}
  if(prompt){const pending=prompt;prompt=null;try{await pending.prompt();await pending.userChoice}catch{showInstructions()}return}
  showInstructions();
 });
 function showInstructions(){
  if(typeof showModal!=='function')return;
  showModal('Install VYBE Connect','<p><strong>Android · Chrome:</strong> open the browser menu, then choose <strong>Install app</strong> or <strong>Add to Home screen</strong>.</p><p><strong>iPhone · Safari:</strong> tap <strong>Share → Add to Home Screen</strong>.</p><p><strong>Computer · Chrome or Edge:</strong> use the install icon in the address bar or the browser’s app menu.</p><p class="hint">Internet is required for CRM, messaging and AI. Installing does not connect WhatsApp or enable charges.</p>',async()=>document.querySelector('#modal').close(),'Done');
 }
 if(typeof navigator!=='undefined'&&'serviceWorker' in navigator&&window.isSecureContext)window.addEventListener('load',()=>{
  navigator.serviceWorker.register('/service-worker.js',{scope:'/',updateViaCache:'none'}).catch(()=>{});
 });
})();
