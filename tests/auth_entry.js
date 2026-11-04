const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const nodes={};
for(const name of ['#app','#authform','#password','#auth-password-toggle','#auth-caps','#autherror','#auth-mfa','#f-code'])nodes[name]={innerHTML:'',textContent:'',hidden:true,open:false,type:'password',isConnected:true,focus(){this.focused=true},setAttribute(k,v){this[k]=v}};
const submit={textContent:'Sign in',disabled:false};nodes['#authform'].querySelector=()=>submit;
let refreshed=0;
const ctx=vm.createContext({console,S:{initialized:true,setupTokenRequired:false,deployment:'hosted',workspace:'old'},
 $:s=>nodes[s],esc:v=>String(v),btn:(t,a)=>`<button type="button" data-do="${a}">${t}</button>`,
 mfaCodeField:()=>'<input id="f-code" name="code" autocomplete="one-time-code">',
 FormData:class extends Map{constructor(){super([['email','owner@example.test'],['password','private-test-password'],['code','']])}},
 api:async()=>{throw Object.assign(new Error('Invalid authenticator or recovery code.'),{status:401})},refresh:async()=>{refreshed++}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/auth-entry.js'),'utf8'),ctx);
const html=vm.runInContext('accountEntryMarkup(false)',ctx);
assert.match(html,/autocomplete="username"/);assert.match(html,/autocomplete="current-password"/);
assert.match(html,/<details id="auth-mfa">/);assert.doesNotMatch(html,/<details id="auth-mfa" open/);
assert.match(html,/id="auth-password-toggle"/);assert.doesNotMatch(html,/Client billing requires/);
vm.runInContext('renderAccountEntry(false)',ctx);
nodes['#auth-password-toggle'].onclick();assert.equal(nodes['#password'].type,'text');assert.equal(nodes['#auth-password-toggle']['aria-pressed'],'true');
nodes['#auth-password-toggle'].onclick();assert.equal(nodes['#password'].type,'password');
nodes['#password'].onkeyup({getModifierState:()=>true});assert.equal(nodes['#auth-caps'].hidden,false);
nodes['#password'].onblur();assert.equal(nodes['#auth-caps'].hidden,true);
(async()=>{
 await nodes['#authform'].onsubmit({preventDefault(){},target:nodes['#authform']});
 assert.equal(nodes['#auth-mfa'].open,true);assert.equal(nodes['#f-code'].focused,true);assert.equal(submit.disabled,false);assert.equal(refreshed,0);
 let resolve;ctx.api=()=>new Promise(r=>resolve=r);
 const pending=nodes['#authform'].onsubmit({preventDefault(){},target:nodes['#authform']});
 nodes['#authform'].isConnected=false;resolve({});await pending;
 assert.equal(refreshed,0,'A completed login must not rerender a replaced form.');
 assert.equal(vm.runInContext('S.workspace',ctx),'old','A stale login response must not overwrite the current workspace selection.');
 console.log('Sign-in autofill, password visibility, Caps Lock, MFA and stale-form checks passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
