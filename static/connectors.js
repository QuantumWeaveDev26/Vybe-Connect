'use strict';
const CONNECTOR_MENU={trigger:null,timer:0,pinned:false};
function connectorMenuMarkup(){return '<nav id="connector-popover" class="connector-popover" aria-label="Connectors"><p>CONNECTORS</p><a href="#developers">API tokens <span>Access keys and developer setup</span></a><a href="#commerce">Integrations <span>Commerce and connected services</span></a><a href="#recipes">Integration recipes <span>Map incoming business events</span></a><a href="#webhooks">Webhooks <span>Callback setup and delivery logs</span></a></nav>'}
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
 const sendingReady=meta.configured&&meta.live;
 const channelStatus=!meta.configured?'Not connected':sendingReady?'Sending enabled':'Sending paused';
 const channelDetail=!meta.configured?'Connect a WhatsApp Business number to send messages.':sendingReady?'The number is configured and sending is enabled. Check webhooks for delivery activity.':'The number is configured. Enable sending in WhatsApp settings when ready.';
 return pagehead('API & integrations','Connect your tools or open VYBE’s built-in agents.')+
 `<section class="card"><div class="cardbody setup-connections developer-connections"><div class="developer-channel"><h2>WhatsApp channel</h2>${badge(channelStatus,sendingReady?'green':'gray')}<p>${channelDetail}</p><a class="developer-step-link" href="#settings">${meta.configured?'Manage WhatsApp':'Connect WhatsApp'} →</a></div><div><h2>Built-in AI agents</h2><p>Choose an agent, add your business knowledge and review its findings.</p><a class="developer-step-link" href="#ai-agents">Open AI agents →</a></div></div></section>`+
 `<details class="developer-contract"><summary>Advanced · API tokens</summary>${apiTokenManagerMarkup()}</details>`+`<details class="developer-contract"><summary>Optional integrations</summary><div class="setup-connections"><section><h2>External agent endpoint</h2>${badge(connected?'Configured':'Optional',connected?'':'gray')}<p>${connected?`${connected} enabled external connection${connected===1?'':'s'}.`:'Connect your own agent only if you use a separate service.'}</p><a href="#external-agents" class="developer-step-link">Manage external agents →</a></section><section><h2>Webhook delivery</h2>${badge(events.length?'Activity available':'No events yet','gray')}<p>Receive events in your own tools and review delivery logs.</p><a href="#webhooks" class="developer-step-link">Open webhooks →</a></section></div></details><details class="developer-contract"><summary>Webhook and API reference</summary>${developerContractPage()}</details>`;
}
function webhooksPage(){
 const m=S.data.meta,origin=location.origin||'',callback=origin+'/webhook/'+S.workspace;
 return pagehead('Webhooks','Configure your Meta callback and inspect signed agent event delivery.')+`<section class="card"><div class="cardhead"><h2>WhatsApp callback</h2><span class="badge">${m.present?.VERIFY_TOKEN?'Verify token set':'Verify token missing'}</span></div><div class="cardbody"><p>Use this callback URL in your Meta app’s WhatsApp configuration.</p><div class="code">${esc(callback)}</div><p class="hint">The verify token must match the private server setting exactly. A configured token does not confirm Meta verification or event delivery. Keep your App Secret and access token private.</p><a href="#settings" class="developer-step-link">Review connection settings →</a></div></section>`+webhookHistory();
}
