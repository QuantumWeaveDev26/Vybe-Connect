const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const handlers={},timers=new Map();let menu=null,nextTimer=0;
const link={focus(){this.focused=true}};
const trigger={isConnected:true,attributes:{},closest(selector){return selector.includes('data-connectors-trigger')?this:null},getBoundingClientRect(){return {left:5,right:50,top:250}},setAttribute(k,v){this.attributes[k]=v},focus(){this.focused=true}};
const doc={addEventListener(name,handler){handlers[name]=handler},querySelector(selector){return selector==='#connector-popover'?menu:null},body:{insertAdjacentHTML(){menu={offsetHeight:220,style:{},remove(){menu=null},querySelector(){return link}}}}};
const context=vm.createContext({document:doc,window:{addEventListener(){}},S:{data:{}},innerWidth:390,innerHeight:844,matchMedia:()=>({matches:true}),
 setTimeout(fn){timers.set(++nextTimer,fn);return nextTimer},clearTimeout(id){timers.delete(id)}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/connectors.js'),'utf8'),context);
const event=target=>({target,detail:1,preventDefault(){},stopImmediatePropagation(){}});
handlers.pointerover(event(trigger));assert.ok(menu,'Hover opens the connector choices.');
handlers.click(event(trigger));assert.ok(menu,'The first click must keep a hover-opened menu visible.');
handlers.pointerout({...event(trigger),relatedTarget:null});for(const fn of [...timers.values()])fn();timers.clear();
assert.ok(menu,'A click-pinned menu stays open after pointer exit.');
handlers.click(event(trigger));assert.equal(menu,null,'A second click closes the pinned menu.');
handlers.click({...event(trigger),detail:0});assert.ok(menu);assert.equal(link.focused,true,'Keyboard activation focuses the first destination.');
handlers.keydown({...event(trigger),key:'Escape'});assert.equal(menu,null);assert.equal(trigger.focused,true);
handlers.keydown({...event(trigger),key:'ArrowDown'});assert.ok(menu);
handlers.click(event({closest(){return null}}));assert.equal(menu,null,'Clicking outside closes the popover.');
console.log('Connector hover, click pinning, keyboard activation and dismissal passed.');
