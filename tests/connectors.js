const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const ctx=vm.createContext({console,document:{addEventListener(){}},window:{addEventListener(){}},S:{workspace:'workspace',data:{meta:{configured:false,present:{VERIFY_TOKEN:true}},external_agents:[],webhook_events:[]}},
 esc:v=>String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;'),pagehead:(a,b)=>`<h1>${a}</h1><p>${b}</p>`,webhookHistory:()=>'<div>Delivery history</div>',developerContractPage:()=>'<div>Signed event contract</div>',location:{origin:'https://chat.example.test'}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/connectors.js'),'utf8'),ctx);
let html=vm.runInContext('connectorMenuMarkup()',ctx);
for(const route of ['developers','commerce','webhooks'])assert.match(html,new RegExp('href="#'+route+'"'));
assert.match(html,/aria-label="Connectors"/);
for(const [width,height] of [[320,568],[1366,768],[844,390]]){
 ctx.width=width;ctx.height=height;
 const p=vm.runInContext('connectorPosition({right:width-5,left:width-40,top:height-20},width,height,200)',ctx);
 assert.ok(p.left>=8&&p.left+p.width<=width-8);assert.ok(p.top>=8&&p.top+200<=height-8);
}
html=vm.runInContext('developerPage()',ctx);assert.match(html,/Setup needed/);assert.doesNotMatch(html,/Generate key|Connected successfully/);
html=vm.runInContext('webhooksPage()',ctx);assert.match(html,/https:\/\/chat.example.test\/webhook\/workspace/);assert.match(html,/Verify token set/);assert.match(html,/Delivery history/);
console.log('Connector destinations, viewport containment and real setup states passed.');
