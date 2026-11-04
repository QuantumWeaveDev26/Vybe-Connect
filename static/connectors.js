'use strict';
const CONNECTOR_MENU={trigger:null,timer:0,pinned:false};
function connectorMenuMarkup(){return '<nav id="connector-popover" class="connector-popover" aria-label="Connectors"><p>CONNECTORS</p><a href="#developers">API <span>Setup and event contract</span></a><a href="#commerce">Integrations <span>Commerce and connected services</span></a><a href="#webhooks">Webhooks <span>Callback setup and delivery logs</span></a></nav>'}
function connectorPosition(rect,width,height,menuHeight){
 const menuWidth=Math.min(260,width-16),left=Math.max(8,Math.min(rect.right+10,width-menuWidth-8));
 return {left,top:Math.max(8,Math.min(rect.top,height-menuHeight-8)),width:menuWidth};
}
function closeConnectorMenu(restoreFocus=false){
 clearTimeout(CONNECTOR_MENU.timer);document.querySelector('#connector-popover')?.remove();
 const trigger=CONNECTOR_MENU.trigger;trigger?.setAttribute('aria-expanded','false');CONNECTOR_MENU.trigger=null;CONNECTOR_MENU.pinned=false;
 if(restoreFocus&&trigger?.isConnected)trigger.focus();
}
function openConnectorMenu(trigger,focus=false){
 if(!S.data)return;clearTimeout(CONNECTOR_MENU.timer);
 let menu=document.querySelector('#connector-popover');
 if(!menu){closeConnectorMenu();document.body.insertAdjacentHTML('beforeend',connectorMenuMarkup());menu=document.querySelector('#connector-popover')}
 CONNECTOR_MENU.trigger=trigger;trigger.setAttribute('aria-expanded','true');
 if(typeof hideNavigationHint==='function')hideNavigationHint();
 const position=connectorPosition(trigger.getBoundingClientRect(),innerWidth,innerHeight,menu.offsetHeight);
 Object.assign(menu.style,{left:position.left+'px',top:position.top+'px',width:position.width+'px'});
 if(focus)menu.querySelector('a')?.focus();
}
document.addEventListener('click',event=>{
 const trigger=event.target.closest?.('[data-connectors-trigger]');
 if(trigger){event.preventDefault();event.stopImmediatePropagation();if(document.querySelector('#connector-popover')&&CONNECTOR_MENU.pinned)closeConnectorMenu();else{openConnectorMenu(trigger,event.detail===0);CONNECTOR_MENU.pinned=true}return}
 if(!event.target.closest?.('#connector-popover'))closeConnectorMenu();
},true);
document.addEventListener('pointerover',event=>{
 if(event.target.closest?.('#connector-popover')){clearTimeout(CONNECTOR_MENU.timer);return}
 const trigger=event.target.closest?.('[data-connectors-trigger]');
 if(trigger&&typeof matchMedia==='function'&&matchMedia('(hover:hover) and (pointer:fine)').matches)openConnectorMenu(trigger);
});
document.addEventListener('pointerout',event=>{
 if(!event.target.closest?.('[data-connectors-trigger],#connector-popover'))return;
 if(event.relatedTarget?.closest?.('[data-connectors-trigger],#connector-popover'))return;
 if(CONNECTOR_MENU.pinned)return;
 CONNECTOR_MENU.timer=setTimeout(()=>closeConnectorMenu(),160);
});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'&&document.querySelector('#connector-popover')){event.preventDefault();closeConnectorMenu(true)}
 if(event.key==='ArrowDown'&&event.target.closest?.('[data-connectors-trigger]')){event.preventDefault();openConnectorMenu(event.target.closest('[data-connectors-trigger]'),true);CONNECTOR_MENU.pinned=true}
});
document.addEventListener('focusin',event=>{if(CONNECTOR_MENU.trigger&&!event.target.closest?.('[data-connectors-trigger],#connector-popover'))closeConnectorMenu()});
document.addEventListener('scroll',()=>closeConnectorMenu(),true);
window.addEventListener('hashchange',()=>closeConnectorMenu());window.addEventListener('resize',()=>closeConnectorMenu());
function developerPage(){
 const meta=S.data.meta,agents=S.data.external_agents||[],events=S.data.webhook_events||[];
 const connected=agents.filter(a=>a.enabled&&a.connection?.configured).length;
 const steps=[
  ['1','Connect your WhatsApp channel',meta.configured?'Required settings are present and have valid formats. Live delivery still needs verification.':'Add your Meta settings to connect your business number.',meta.configured?'Settings complete':'Setup needed','#settings','Open connection settings'],
  ['2','Connect your agent',connected?`${connected} enabled connection${connected===1?'':'s'} with dispatch settings configured.`:'Connect your own HTTPS agent endpoint and signing secret.',connected?'Configured':'Setup needed','#external-agents','Manage agents'],
  ['3','Review webhook delivery',events.length?`${events.length} recent event${events.length===1?'':'s'} available for review.`:'Review callback setup, signed events and delivery history.',events.length?'Activity available':'No events yet','#webhooks','Open webhooks']
 ];
 return pagehead('Developer console','Connect your channel, configure agents and review real event delivery.')+`<div class="developer-steps">${steps.map(([n,title,description,status,href,label])=>`<section class="developer-step"><span class="developer-step-number">${n}</span><div><div class="developer-step-heading"><h2>${title}</h2><span class="badge">${status}</span></div><p>${esc(description)}</p><a href="${href}" class="developer-step-link">${label} →</a></div></section>`).join('')}</div><details class="developer-contract"><summary>API event contract and agent callbacks</summary>${developerContractPage()}</details>`;
}
function webhooksPage(){
 const m=S.data.meta,origin=location.origin||'',callback=origin+'/webhook/'+S.workspace;
 return pagehead('Webhooks','Configure your Meta callback and inspect signed agent event delivery.')+`<section class="card"><div class="cardhead"><h2>WhatsApp callback</h2><span class="badge">${m.present?.VERIFY_TOKEN?'Verify token set':'Verify token missing'}</span></div><div class="cardbody"><p>Use this callback URL in your Meta app’s WhatsApp configuration.</p><div class="code">${esc(callback)}</div><p class="hint">The verify token must match the private server setting exactly. A configured token does not confirm Meta verification or event delivery. Keep your App Secret and access token private.</p><a href="#settings" class="developer-step-link">Review connection settings →</a></div></section>`+webhookHistory();
}
