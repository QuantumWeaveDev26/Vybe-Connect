const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const elements=new Map();
function element(){
 return {
  children:[],style:{},value:'',textContent:'',
  appendChild(child){this.children.push(child)},
  replaceChildren(){this.children=[]},
  addEventListener(){},remove(){},setAttribute(){},focus(){}
 };
}
const document={
 currentScript:{src:'https://example.test/widget.js',dataset:{workspace:'1234567890abcdef',title:'<b>Support</b>',color:'red;display:none'}},
 head:element(),body:element(),createElement:element,
 getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)}
};
const window={};
let response;
let requests=0;
const context={document,window,URL,URLSearchParams,localStorage:{getItem(){throw Error('Unavailable')},setItem(){throw Error('Unavailable')},removeItem(){}},fetch:async()=>{requests++;return response}};
vm.runInNewContext(fs.readFileSync('static/widget.js','utf8'),context);

(async()=>{
 const input=document.getElementById('vw-text');
 const log=document.getElementById('vybe-messages');
 const status=document.getElementById('vybe-widget-status');
 assert.equal(document.getElementById('vybe-widget-title').textContent,'<b>Support</b>');
 assert.doesNotMatch(document.body.children[0].innerHTML,/<b>Support/);
 assert.doesNotMatch(document.head.children[0].textContent,/red;display:none/);
 input.value='My draft';
 response={ok:false};
 await window.VybeWidget.send();
 assert.equal(input.value,'My draft');
 assert.equal(log.children.length,0,'A failed send must not appear in the transcript');
 assert.match(status.textContent,/Could not confirm/);
 response={ok:true,json:async()=>({contact_id:'contact',visitor_token:'token',messages:[{id:'m1',direction:'in',body:'My draft'}]})};
 await window.VybeWidget.send();
 assert.equal(input.value,'');
 assert.equal(log.children[0].textContent,'My draft');
 assert.equal(status.textContent,'Sent to the team');
 assert.equal(requests,2);
 console.log('Widget retains failed drafts and renders confirmed messages even when browser storage is blocked.');
})().catch(err=>{console.error(err);process.exitCode=1});
