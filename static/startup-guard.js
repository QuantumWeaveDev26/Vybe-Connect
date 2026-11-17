'use strict';
// Independent of application initialization: a failed script must not leave a permanent spinner.
(function(){
 if(typeof document.getElementById!=='function')return;
 setTimeout(()=>{
  const app=document.getElementById('app');
  if(!app?.querySelector('.loading'))return;
  document.getElementById('vybe-launch')?.remove();app.inert=false;
  app.innerHTML='<div class="empty" role="alert"><h3>Could not open VYBE Connect</h3><p>The workspace took too long to load. Reload to try again.</p><button type="button" class="primary" id="startup-reload">Reload workspace</button></div>';
  document.getElementById('startup-reload')?.addEventListener('click',()=>location.reload());
 },30000);
})();
