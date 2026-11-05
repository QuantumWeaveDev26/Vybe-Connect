const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const handlers={},state={html:'',renders:0,login:null,refreshes:0};
 const FB={init(){},login(callback){state.login=callback}};
 const context=vm.createContext({JSON,String,Boolean,Object,Array,Promise,FB,clearTimeout(){},setTimeout(){return 1},
  settingsPage(){return ''},aiConnectionCard(){return ''},pagehead(){return ''},badge(v){return v},date(v){return String(v)},esc(v){return String(v).replaceAll('<','&lt;')},
  S:{workspace:'workspace',route:'settings',data:{context:{role:'admin',user:{id:'owner'}},meta:{},whatsapp_connection:{status:'not_connected',signup_available:true}}},
  document:{addEventListener(name,fn){handlers[name]=fn},querySelector(){return null}},window:{FB,addEventListener(name,fn){handlers['window:'+name]=fn}},
  act(){return Promise.resolve({state:'nonce',app_id:'123',config_id:'456',version:'v25.0'})},
  refresh(){state.refreshes++;return Promise.resolve()},render(){state.renders++;state.html=vm.runInContext('settingsPage()',context)},toast(){}});
 vm.runInContext(fs.readFileSync('static/whatsapp-connect.js','utf8'),context);
 function click(){const button={disabled:false,hasAttribute(name){return name==='data-wa-connect'}};return handlers.click({target:{closest(){return button}}})}
 await click();
 assert.match(state.html,/Continue with Meta/);assert.match(state.html,/data-wa-connect >Continue/);
 assert.equal(state.refreshes,0,'UI preparation must not depend on a changed server snapshot');
 await click();assert.equal(typeof state.login,'function');assert.match(state.html,/data-wa-connect disabled/);
 state.login({status:'unknown'});
 assert.match(state.html,/Meta returned no authorization code/);assert.match(state.html,/data-wa-connect >Connect WhatsApp/);
 assert.doesNotMatch(state.html,/Ready\. Click Continue/,'cancelled login must not leave a stale Ready label');
 await click();await click();
 handlers['window:message']({origin:'https://www.facebook.com',data:JSON.stringify({type:'WA_EMBEDDED_SIGNUP',event:'CANCEL'})});
 assert.match(state.html,/cancelled or rejected/);assert.match(state.html,/data-wa-connect >Connect WhatsApp/);
 console.log('WhatsApp signup retry: immediate Ready rendering, no-code and cancellation recovery work without server-state changes.');
})().catch(error=>{console.error(error);process.exitCode=1});
