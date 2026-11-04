'use strict';
// Content is always visible. Animate once on entry; never delay controls or data.
(function(){
 if(typeof IntersectionObserver==='undefined'||typeof MutationObserver==='undefined'||!document.documentElement)return;
 const reduce=matchMedia('(prefers-reduced-motion: reduce)'),seen=new WeakSet();
 const selector='.content .card,.content .stat,.content .owned-product,.content .deal-card,.content .finding-card,.ai-body .agent-preset-card,.ai-body .saved-agent-card';
 let visibility=null,changes=null,frame=0;
 function scan(){frame=0;if(reduce.matches)return;document.querySelectorAll(selector).forEach(node=>{if(!seen.has(node)){seen.add(node);visibility.observe(node)}})}
 function schedule(){if(!frame)frame=requestAnimationFrame(scan)}
 function start(){
  if(reduce.matches)return;
  visibility=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){visibility.unobserve(entry.target);entry.target.classList.add('vybe-enter');entry.target.addEventListener('animationend',()=>entry.target.classList.remove('vybe-enter'),{once:true})}})},{threshold:.08});
  changes=new MutationObserver(records=>{if(records.some(r=>r.addedNodes.length))schedule()});
  changes.observe(document.documentElement,{childList:true,subtree:true});scan();
 }
 function stop(){visibility?.disconnect();changes?.disconnect();cancelAnimationFrame(frame);frame=0;document.querySelectorAll('.vybe-enter').forEach(node=>node.classList.remove('vybe-enter'))}
 reduce.addEventListener?.('change',()=>{stop();start()});start();
})();
