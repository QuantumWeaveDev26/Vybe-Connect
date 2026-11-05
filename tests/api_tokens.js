const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const modal={dataset:{},open:true,innerHTML:'original form',close(){this.open=false},addEventListener(){},querySelector(){return null}};
const form={};let submit,post;
const c=vm.createContext({Date,Array,Number,document:{addEventListener(){},querySelector(s){return s==='#modal'?modal:s==='#dialog-form'?form:null},querySelectorAll(){return [{value:'contacts:read'}]}},window:{addEventListener(){}},S:{workspace:'one',review:false,data:{context:{role:'admin',user:{id:'owner'}},api_tokens:[{id:'id',name:'<img onerror=bad>',scopes:['contacts:read'],expires:9999999999,revoked:0,last_used:0}]}},location:{origin:'https://example.test'},esc:v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),date:String,btn:(label,action,extra)=>`<button data-do="${action}" ${extra||''}>${label}</button>`,showModal(title,html,callback){submit=callback;return html},api:async(path,options)=>{post={path,body:JSON.parse(options.body)};return {token:'synthetic-once-only-token'}},refresh:async()=>true,toast(){}});
vm.runInContext(fs.readFileSync('static/api-tokens.js','utf8'),c);
const html=vm.runInContext('apiTokenManagerMarkup()',c);
assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img/);assert.match(html,/Read-only/);assert.match(html,/api-token-revoke/);
vm.runInContext('S.data.context.role="agent"',c);assert.equal(vm.runInContext('apiTokenManagerMarkup()',c),'');vm.runInContext('S.data.context.role="admin"',c);
(async()=>{
 await vm.runInContext('apiTokenAction("api-token-create",{})',c);await submit({name:'CRM',days:'30'});
 assert.equal(post.path,'/api/developer/tokens');assert.deepEqual(post.body,{name:'CRM',days:30,scopes:['contacts:read']});assert.match(modal.innerHTML,/synthetic-once-only-token/);
 vm.runInContext('clearApiTokenSecret()',c);assert.equal(modal.innerHTML,'');assert.equal(modal.dataset.apiTokenSecret,undefined);
 modal.open=true;modal.innerHTML='new form';c.refresh=async()=>{vm.runInContext('S.workspace="two"',c)};
 await vm.runInContext('apiTokenAction("api-token-create",{})',c);await submit({name:'CRM',days:'7'});
 assert.doesNotMatch(modal.innerHTML,/synthetic-once-only-token/,'Do not reveal token after workspace changes');
 console.log('API token permissions, escaped metadata, show-once cleanup and stale-workspace secret fencing passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
