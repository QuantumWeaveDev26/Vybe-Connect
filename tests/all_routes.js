// Render every main destination using a real, isolated Store state. No browser or providers.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const fixture=JSON.parse(execFileSync('python',['-c',[
 'import json,tempfile',
 'from pathlib import Path',
 'from store import Store',
 'with tempfile.TemporaryDirectory() as folder:',
 ' s=Store(Path(folder)/"routes.db")',
 ' token=s.setup("Route Owner","route-owner@example.test","isolated-test-password","Route Test Business")["token"]',
 ' ctx=s.auth(token)',
 ' s.action(ctx,"contact.save",{"name":"A long customer name for renderer checks","phone":"919000000001"})',
 ' print(json.dumps(s.state(ctx)))'
].join('\n')],{cwd:root,encoding:'utf8',env:{...process.env,TW_SANDBOX:'false'}}));
const node={addEventListener(){},remove(){},innerHTML:'',open:false};
const context=vm.createContext({console,Intl,Date,JSON,Number,String,Math,Map,Set,Array,Object,Promise,URL,URLSearchParams,
 document:{querySelector(){return node},querySelectorAll(){return []},addEventListener(){}},window:{addEventListener(){}},location:{hash:''},
 localStorage:{getItem(){return ''},removeItem(){}},setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},fetch(){return new Promise(()=>{})}});
const index=fs.readFileSync(path.join(root,'static/index.html'),'utf8');
for(const [,url] of index.matchAll(/<script src="\/([^"/]+)" defer><\/script>/g)){
 if(url.startsWith('launch'))continue;
 vm.runInContext(fs.readFileSync(path.join(root,'static',url.split('?')[0]),'utf8'),context,{filename:url});
}
context.fixture=fixture;
vm.runInContext('S.data=fixture;S.workspace=fixture.context.tenant_id',context);
const routes=vm.runInContext('Object.keys(names)',context);
for(const route of routes){
 context.route=route;
 const html=vm.runInContext('S.route=route;page()',context);
 assert.equal(typeof html,'string',route);assert.ok(html.length>30,route);
 assert.doesNotMatch(html,/>undefined</,`undefined label on ${route}`);
}
context.invalid={APP_SECRET:'Copy the App Secret from Meta App settings > Basic.'};
const settings=vm.runInContext('S.data.meta.invalid=invalid;S.route="settings";page()',context);
assert.match(settings,/Invalid format/);assert.match(settings,/Correct these settings/);
console.log(`All ${routes.length} main routes rendered from an isolated Store state; invalid configuration is actionable.`);
// Provider results remain visible and never treat stale checks as current proof.
vm.runInContext('S.servicesTab="connections";S.data.provider_checks=[{provider:"openai",outcome:"passed",current:true},{provider:"meta",outcome:"failed_or_unconfirmed",current:true}]',context);
let diagnostic=vm.runInContext('servicesPage()',context);
assert.match(diagnostic,/Metadata verified/);assert.match(diagnostic,/Access not verified/);
vm.runInContext('S.data.provider_checks.forEach(check=>check.current=false)',context);diagnostic=vm.runInContext('servicesPage()',context);
assert.match(diagnostic,/Recheck needed/);assert.doesNotMatch(diagnostic,/Metadata verified/);
console.log('Provider diagnostics persist results and reject stale verification states.');

vm.runInContext('S.data.contacts=[];S.data.meta.configured=true;S.chat=null',context);
let inboxEmpty=vm.runInContext('inboxPage()',context);assert.match(inboxEmpty,/Check your webhook subscription/);assert.doesNotMatch(inboxEmpty,/Connect Meta for real incoming/);
vm.runInContext('S.data.meta.configured=false',context);inboxEmpty=vm.runInContext('inboxPage()',context);assert.match(inboxEmpty,/Connect your WhatsApp account/);
console.log('Inbox setup guidance reflects the actual connection configuration.');
