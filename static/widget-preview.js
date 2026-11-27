'use strict';
// This page configures a website channel, never a WhatsApp identity or consent.
const previewWorkspace=new URLSearchParams(location.search).get('workspace')||'';
const validWorkspace=/^[a-f0-9]{16}$/.test(previewWorkspace);
window.VYBE_WORKSPACE=validWorkspace?previewWorkspace:'';
const previewButton=document.querySelector('#open-widget-preview');
const embedCode=document.querySelector('#widget-embed-code');
const widgetNotice=document.querySelector('#widget-preview-notice');
const copyButton=document.querySelector('#copy-widget-code');
if(validWorkspace){
 embedCode.textContent=`<script src="${location.origin}/widget.js" data-workspace="${previewWorkspace}" data-title="Support chat" defer></script>`;
 widgetNotice.textContent='Website messages go to Team Inbox.';
}else{
 previewButton.disabled=true;
 if(copyButton)copyButton.disabled=true;
 widgetNotice.textContent='Open this page from your VYBE workspace.';
}
previewButton.addEventListener('click',()=>window.VybeWidget?.open());

copyButton?.addEventListener('click',async()=>{
 if(!validWorkspace)return;
 try{
   await navigator.clipboard.writeText(embedCode.textContent);
   widgetNotice.textContent='Install code copied.';
 }catch{
   const details=document.querySelector('#widget-install-details');
   if(details)details.open=true;
   widgetNotice.textContent='Copy the install code below.';
 }
});
