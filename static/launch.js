
(function(){
 const splash=document.getElementById('vybe-launch');if(!splash)return;
 const started=performance.now(),reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;let done=false;
 const observer=new MutationObserver(check);
 function dismiss(){if(done)return;done=true;observer.disconnect();clearTimeout(deadline);setTimeout(()=>{splash.classList.add('launch-finished');setTimeout(()=>splash.remove(),reduced?0:320)},Math.max(0,(reduced?0:1050)-(performance.now()-started)))}
 function check(){const app=document.getElementById('app');if(app&&!app.querySelector('.loading')&&app.children.length)dismiss()}
 observer.observe(document.getElementById('app'),{childList:true,subtree:true});const deadline=setTimeout(dismiss,8000);check();
})();
