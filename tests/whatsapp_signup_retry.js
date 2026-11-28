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
 vm.runInContext(fs.readFileSync('static/manual-whatsapp.js','utf8'),context);
vm.runInContext(fs.readFileSync('static/whatsapp-connect.js','utf8'),context);
 function click(){const button={disabled:false,hasAttribute(name){return name==='data-wa-connect'}};return handlers.click({target:{closest(){return button}}})}
 const settle=()=>new Promise(resolve=>setImmediate(resolve));
 vm.runInContext('render()',context);
 assert.match(state.html,/Preparing WhatsApp/);
 await settle();
 assert.match(state.html,/data-wa-connect >Connect WhatsApp/);
 assert.doesNotMatch(state.html,/Continue with Meta/);
 assert.equal(state.refreshes,0);
 await click();
 assert.equal(typeof state.login,'function');
 assert.match(state.html,/data-wa-connect disabled/);
 state.login({status:'unknown'});
 assert.match(state.html,/Meta sign-in did not finish/);
 await settle();
 assert.match(state.html,/data-wa-connect >Try again/);
 const previous=state.login;await click();assert.notEqual(state.login,previous);
 handlers['window:message']({origin:'https://www.facebook.com',data:JSON.stringify({type:'WA_EMBEDDED_SIGNUP',event:'CANCEL'})});
 assert.match(state.html,/cancelled or rejected/);
 console.log('WhatsApp signup opens from the first click after preload and handles cancelled login.');
})().catch(error=>{console.error(error);process.exitCode=1});
