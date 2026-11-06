const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({S:{data:{context:{tenant_id:'scope',role:'admin',user:{id:'owner'}},contacts:[],members:[],growth:{}},chat:''},location:{origin:'https://example.test'},pagehead:(t,d,a='')=>`<h1>${t}</h1><p>${d}</p>${a}`,esc:v=>String(v??'').replace(/[<>&"']/g,'_'),btn:(t,a,e='')=>`<button data-do="${a}" ${e}>${t}</button>`,field:()=>'',document:{addEventListener(){}},Date});
vm.runInContext(fs.readFileSync('static/growth.js','utf8'),c);
for(const name of ['recipesPage','supportToolsPage','branchesPage','attributionPage','helpCentrePage','whatsappFormsPage']){
 const result=vm.runInContext(`${name}()`,c);assert.match(result,/<h1>/);assert.doesNotMatch(result,/undefined|NaN/);
}
vm.runInContext(`S.data.growth={recipes:[{id:'recipe',name:'<unsafe>',mode:'draft',enabled:true}],branch_report:[{id:'branch',name:'Branch',contacts:2,open:1,deals:1,won:0}],attribution_report:[{source_id:'ad',kind:'meta_ad',leads:2,deals:1,won:0}],whatsappforms:[{id:'form',title:'Form',meta_id:'123',status:'PUBLISHED',fields:[{}]}]}`,c);
assert.doesNotMatch(vm.runInContext('recipesPage()',c),/<unsafe>/);
assert.match(vm.runInContext('whatsappFormsPage()',c),/growth-form-send/);
assert.match(vm.runInContext('branchesPage()',c),/do not restrict teammate visibility/);
const callbacks=[];c.showModal=(title,body,submit)=>callbacks.push(submit);c.calls=0;c.act=async()=>{c.calls++;return {}};c.$=()=>({close(){}});c.refresh=async()=>{};
vm.runInContext(`growthDialog('Scope check','',()=>act('unexpected',{}));S.data.context.tenant_id='another-workspace'`,c);
(async()=>{await assert.rejects(()=>callbacks[0]({}),/Workspace changed/);assert.equal(c.calls,0);console.log('Growth page empty/filled states, escaping, scope guards and truthful controls passed.')})().catch(e=>{console.error(e);process.exitCode=1});
