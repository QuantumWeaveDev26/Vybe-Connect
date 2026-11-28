'use strict';
const params=new URLSearchParams(location.search);
const workspace=params.get('workspace')||'';
const validWorkspace=/^[a-f0-9]{16}$/.test(workspace);
window.VYBE_WORKSPACE=validWorkspace?workspace:'';
const open=document.querySelector('#open-widget-preview');
const copy=document.querySelector('#copy-widget-link');
const notice=document.querySelector('#widget-preview-notice');
const field=document.querySelector('#widget-chat-link');
const customerView=params.get('chat')==='1';
const link=location.origin+'/widget-preview?workspace='+encodeURIComponent(workspace)+'&chat=1';
open.disabled=!validWorkspace;
copy.hidden=customerView||!validWorkspace;
notice.textContent=!validWorkspace?'This chat link is unavailable.':customerView?'Send us a message.':'Open chat or share its link with customers.';
if(customerView){
 document.querySelector('#widget-back').hidden=true;
 document.querySelector('#widget-page-title').textContent='Support chat';
}
open.addEventListener('click',()=>{if(validWorkspace)window.VybeWidget?.open()});
copy.addEventListener('click',async()=>{
 if(!validWorkspace||customerView)return;
 try{
   await navigator.clipboard.writeText(link);
   notice.textContent='Chat link copied.';
 }catch{
   field.value=link;field.hidden=false;field.focus();field.select();
   notice.textContent='Copy the selected link.';
 }
});
