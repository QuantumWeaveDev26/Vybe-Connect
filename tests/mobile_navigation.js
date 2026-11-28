const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const handlers={};let focused='',open=false;
const controls=[{setAttribute(k,v){this[k]=v}},{setAttribute(k,v){this[k]=v}}];
const first={focus(){focused='first'},hidden:false,getClientRects:()=>[1]};
const sidebar={setAttribute(){},removeAttribute(){},querySelector:()=>first,querySelectorAll:()=>[first],contains:x=>x===first};
const main={inert:false};const shell={classList:{toggle(_,value){open=value}}};
const doc={body:{classList:{toggle(){}}},activeElement:null,addEventListener(n,fn){(handlers[n]??=[]).push(fn)},querySelector(q){if(q==='.shell')return shell;if(q==='.sidebar')return sidebar;if(q==='.content')return main;if(q.includes('header-mobile-menu'))return {focus(){focused='toggle'}};return null},querySelectorAll(q){return q==='[data-do="nav-toggle"]'?controls:[]}};
const c=vm.createContext({document:doc,window:{addEventListener(){}},innerWidth:390,workspaceStorage:{getItem:()=>null},S:{data:{}},btn:()=>'',icon:()=>''});vm.runInContext(fs.readFileSync('static/shell.js','utf8'),c);
vm.runInContext('toggleNavigation()',c);assert.equal(open,true);assert.equal(main.inert,true);assert.equal(focused,'first');for(const control of controls)assert.equal(control['aria-expanded'],'true');
for(const handler of handlers.keydown)handler({key:'Escape'});
assert.equal(open,false);assert.equal(main.inert,false);assert.equal(focused,'toggle');for(const control of controls)assert.equal(control['aria-expanded'],'false');
console.log('Mobile drawer synchronizes toggles, focuses navigation, protects background and restores focus.');

for(const width of [320,390,658,800,1050]){
 c.innerWidth=width;vm.runInContext('toggleNavigation()',c);assert.equal(open,true,'Drawer must open at '+width);assert.equal(main.inert,true);
 vm.runInContext('closeMobileNavigation(true)',c);assert.equal(open,false,'Drawer must close at '+width);assert.equal(main.inert,false);assert.equal(focused,'toggle');
}
console.log('Drawer state and background access passed at 320, 390, 658, 800 and 1050 pixels.');
