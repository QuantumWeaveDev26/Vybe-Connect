
'use strict';
// Natural Earth public-domain land dots. Pointer effects stay on this device.
(function(){
 const first=document.getElementById('vybe-launch');if(!first)return;
 const template=first.outerHTML,reduce=matchMedia('(prefers-reduced-motion: reduce)');let land=[],active=null;
 fetch('/world-dots.json').then(r=>r.ok?r.json():[]).then(points=>{if(Array.isArray(points)&&points.length<20000&&points.every(n=>typeof n==='number'&&n>=0&&n<=1)){land=points;active?.resize()}}).catch(()=>{});
 function open(splash,preview=false){
  if(active)active.close(true);
  let frame=0,finished=false,ready=preview,deadline=0,auto=0,lastPointer=0,particles=[],width=0,height=0;
  const began=performance.now(),canvas=splash.querySelector('canvas'),ctx=canvas.getContext('2d'),button=splash.querySelector('[data-launch-enter]'),mark=splash.querySelector('.launch-mark');
  const appRoot=document.getElementById('app'),wasInert=appRoot.inert;appRoot.inert=true;
  const pointer={x:-9999,y:-9999},previous=document.activeElement,observer=new MutationObserver(check);
  const cities=[[-122.42,37.77],[-74.01,40.71],[-.13,51.51],[77.21,28.61],[103.82,1.35],[151.21,-33.87]];
  function make(x,y,logo,seed){return {x,y,ox:0,oy:0,vx:0,vy:0,logo,seed}}
  function resize(){
   if(finished||!ctx)return;width=innerWidth;height=innerHeight;const dpr=Math.min(devicePixelRatio||1,1.75);canvas.width=width*dpr;canvas.height=height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
   const bounds=mark.getBoundingClientRect(),mapW=Math.min(1650,Math.max(width*1.04,680)),mapH=mapW/2,mapX=(width-mapW)/2,mapY=(height-mapH)/2-25;
   particles=[];for(let i=0;i<land.length;i+=2)particles.push(make(mapX+land[i]*mapW,mapY+land[i+1]*mapH,false,i));
   const mask=document.createElement('canvas');mask.width=140;mask.height=140;const mc=mask.getContext('2d');mc.fillStyle='#000';mc.fill(new Path2D('M18 24h29l23 66 23-66h29L83 118H57Z'));const pixels=mc.getImageData(0,0,140,140).data;
   for(let y=0;y<140;y+=3)for(let x=0;x<140;x+=3)if(pixels[(y*140+x)*4+3]>128)particles.push(make(bounds.x+x*bounds.width/140,bounds.y+y*bounds.height/140,true,x+y));
   splash.dataset.particles=String(particles.length);if(reduce.matches)draw(performance.now());
  }
  function draw(now){
   if(finished||!ctx)return;ctx.clearRect(0,0,width,height);const age=now-began,reveal=reduce.matches?1:Math.min(1,Math.max(0,(age-350)/950));
   for(const p of particles){
    const dx=p.x-pointer.x,dy=p.y-pointer.y,distance=Math.hypot(dx,dy),near=distance<125&&distance>0,force=near?(1-distance/125):0;
    if(!reduce.matches){p.vx=(p.vx+(near?dx/distance*force*3:0)-p.ox*.055)*.83;p.vy=(p.vy+(near?dy/distance*force*3:0)-p.oy*.055)*.83;p.ox+=p.vx;p.oy+=p.vy}
    const purple=p.logo&&(Math.sin(age/640+p.x/80+p.y/90)>.6||near);
    ctx.globalAlpha=p.logo?Math.min(1,age/350):reveal*(.32+force*.55);ctx.fillStyle=p.logo?(purple?'#8854d9':'#27342f'):(near?'#8962c1':'#aaa0c3');
    const intro=p.logo||reduce.matches?0:(1-reveal)*8*Math.sin(p.seed);ctx.beginPath();ctx.arc(p.x+p.ox,p.y+p.oy+intro,p.logo?1.15:1+force*1.3,0,Math.PI*2);ctx.fill();
   }
   const mapW=Math.min(1650,Math.max(width*1.04,680)),mapH=mapW/2;ctx.globalAlpha=reveal*.58;ctx.font='9px "Segoe UI",sans-serif';ctx.fillStyle='#9179b5';
   for(const [lon,lat] of cities){const x=(width-mapW)/2+(lon+180)/360*mapW,y=(height-mapH)/2-25+(90-lat)/180*mapH;ctx.fillText('+ '+Math.abs(lat).toFixed(2)+'° '+(lat>0?'N':'S')+'  '+Math.abs(lon).toFixed(2)+'° '+(lon>0?'E':'W'),x+8,y);ctx.beginPath();ctx.arc(x,y,2,0,Math.PI*2);ctx.fill()}
   ctx.globalAlpha=1;if(!reduce.matches)frame=requestAnimationFrame(draw);
  }
  function move(event){if(reduce.matches)return;pointer.x=event.clientX;pointer.y=event.clientY;lastPointer=performance.now()}
  function leave(){pointer.x=pointer.y=-9999}
  function check(){const app=document.getElementById('app');if(preview||(app&&!app.querySelector('.loading')&&app.children.length)){ready=true;splash.dataset.ready='true';button.disabled=false;button.textContent='Open workspace';observer.disconnect();if(!auto)auto=setTimeout(tick,reduce.matches?0:4200)}}
  function tick(){if(finished)return;if(!preview&&performance.now()-began<12000&&performance.now()-lastPointer<1000){auto=setTimeout(tick,1000);return}close()}
  function key(event){if(event.key==='Tab'){event.preventDefault();if(ready)button.focus();return}if(event.key==='Escape'&&ready){event.preventDefault();close()}}
  function close(immediate=false){if(finished)return;finished=true;cancelAnimationFrame(frame);clearTimeout(deadline);clearTimeout(auto);observer.disconnect();window.removeEventListener('resize',resize);splash.removeEventListener('pointermove',move);splash.removeEventListener('pointerleave',leave);document.removeEventListener('keydown',key);appRoot.inert=wasInert;splash.classList.add('launch-finished');if(splash.contains(document.activeElement)&&previous?.isConnected)previous.focus();if(immediate||reduce.matches)splash.remove();else setTimeout(()=>splash.remove(),460);if(active?.element===splash)active=null}
  button.addEventListener('click',()=>{if(ready)close()});splash.addEventListener('pointermove',move);splash.addEventListener('pointerleave',leave);document.addEventListener('keydown',key);window.addEventListener('resize',resize);
  observer.observe(document.getElementById('app'),{childList:true,subtree:true});deadline=setTimeout(()=>close(),12000);active={element:splash,resize,close};
  resize();if(ctx){splash.classList.add('launch-interactive');if(!reduce.matches)frame=requestAnimationFrame(draw)}check();if(preview){button.focus();clearTimeout(auto);auto=setTimeout(tick,12000)}
 }
 document.addEventListener('click',event=>{if(event.target.closest('[data-do="launch-preview"]')){event.preventDefault();event.stopImmediatePropagation();if(active)return;document.body.insertAdjacentHTML('beforeend',template);open(document.getElementById('vybe-launch'),true)}},true);
 open(first);
})();
