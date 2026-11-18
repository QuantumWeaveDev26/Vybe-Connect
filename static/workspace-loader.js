'use strict';
// Keep dependency order and recover a failed download before running application code.
(function(){
 if(typeof document.getElementById!=='function')return;
 const manifest=document.getElementById('workspace-scripts');if(!manifest)return;
 let stopped=false;
 function failed(){
  stopped=true;const app=document.getElementById('app');if(!app)return;
  document.getElementById('vybe-launch')?.remove();app.inert=false;
  app.innerHTML='<div class="empty" role="alert"><h3>Could not open VYBE Connect</h3><p>A workspace file could not be downloaded. Reload to try again.</p><button type="button" class="primary" id="workspace-reload">Reload workspace</button></div>';
  document.getElementById('workspace-reload')?.addEventListener('click',()=>location.reload());
 }
 async function load(path){
  if(typeof path!=='string'||!/^\/[a-z0-9-]+\.js\?v=[a-f0-9]+$/.test(path))throw Error('Invalid workspace asset');
  for(let attempt=0;attempt<3;attempt++){
   const outcome=await new Promise(resolve=>{
    const script=document.createElement('script');script.async=false;
    script.src=path+(attempt?'&retry='+attempt:'');
    let settled=false;
    const finish=result=>{if(settled)return;settled=true;clearTimeout(deadline);if(result!=='loaded')script.remove();resolve(result)};
    const deadline=setTimeout(()=>finish('timeout'),12000);
    script.onload=()=>finish('loaded');script.onerror=()=>finish('error');document.head.appendChild(script);
   });
   if(outcome==='loaded')return;
   // A timed-out script may still execute later. Never run a duplicate copy.
   if(outcome==='timeout')throw Error('Workspace download timed out');
  }
  throw Error('Workspace download failed');
 }
 (async()=>{try{const paths=JSON.parse(manifest.textContent);if(!Array.isArray(paths)||!paths.length||paths.length>60)throw Error('Invalid workspace manifest');for(const path of paths){if(stopped)return;await load(path)}if(typeof boot!=='function')throw Error('Workspace initialization unavailable');void boot()}catch{failed()}})();
})();
