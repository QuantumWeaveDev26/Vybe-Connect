const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../static/interactions.js'),'utf8');
function setup(reduced=false){
 const card={events:{},classes:new Set(),classList:{add(n){card.classes.add(n)},remove(n){card.classes.delete(n)}},addEventListener(n,fn){this.events[n]=fn}};
 const media={matches:reduced,addEventListener(n,fn){this.change=fn}};let io,mo,frames=[];
 const c=vm.createContext({document:{documentElement:{},querySelectorAll(s){return s==='.vybe-enter'?[card].filter(n=>n.classes.has('vybe-enter')):[card]}},matchMedia:()=>media,WeakSet,
 IntersectionObserver:class{constructor(fn){this.fn=fn;this.nodes=[];io=this}observe(n){this.nodes.push(n)}unobserve(n){this.nodes=this.nodes.filter(x=>x!==n)}disconnect(){this.nodes=[]}},
 MutationObserver:class{constructor(fn){this.fn=fn;mo=this}observe(){}disconnect(){}},requestAnimationFrame:fn=>(frames.push(fn),frames.length),cancelAnimationFrame(){}});
 vm.runInContext(source,c);return {card,media,get io(){return io},get mo(){return mo},frames};
}
let x=setup();assert.equal(x.io.nodes.length,1);assert.equal(x.card.classes.size,0,'Below-fold controls must stay visible without hidden styles');
x.io.fn([{target:x.card,isIntersecting:false}]);assert.equal(x.card.classes.size,0);
x.io.fn([{target:x.card,isIntersecting:true}]);assert.equal(x.card.classes.has('vybe-enter'),true);assert.equal(x.io.nodes.length,0);x.card.events.animationend();assert.equal(x.card.classes.size,0);
x.mo.fn([{addedNodes:[{}]}]);x.frames[0]();assert.equal(x.io.nodes.length,0,'Same card should not repeatedly animate');
x=setup(true);assert.equal(x.io,undefined,'Reduced motion must not install reveal observers');
x=setup();x.io.fn([{target:x.card,isIntersecting:true}]);x.media.matches=true;x.media.change();assert.equal(x.card.classes.size,0);assert.equal(x.io.nodes.length,0);
console.log('Scroll entry: content visible, once-only animation, cleanup and reduced-motion preference passed.');
