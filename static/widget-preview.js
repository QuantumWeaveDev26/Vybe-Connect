'use strict';
// This page configures a website channel, never a WhatsApp identity or consent.
const previewWorkspace=new URLSearchParams(location.search).get('workspace')||'';
const validWorkspace=/^[a-f0-9]{16}$/.test(previewWorkspace);
window.VYBE_WORKSPACE=validWorkspace?previewWorkspace:'';
const previewButton=document.querySelector('#open-widget-preview');
const embedCode=document.querySelector('#widget-embed-code');
const widgetNotice=document.querySelector('#widget-preview-notice');
if(validWorkspace){
 embedCode.textContent=`<script src="${location.origin}/widget.js" data-workspace="${previewWorkspace}" data-title="Support chat" defer></script>`;
 widgetNotice.textContent='Messages in this website chat appear in your inbox. WhatsApp messaging and marketing consent stay separate.';
}else{
 previewButton.disabled=true;
 widgetNotice.textContent='Open Website chat setup from your workspace’s API tokens page to select the correct inbox.';
}
previewButton.addEventListener('click',()=>window.VybeWidget?.open());
