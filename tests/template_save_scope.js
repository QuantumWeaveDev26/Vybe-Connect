const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 let resolveSave,calls=0,refreshes=0;
 const error={textContent:''},form={reportValidity:()=>true};
 const ctx=vm.createContext({structuredClone,document:{addEventListener(){}},S:{workspace:'first',route:'templates',data:{context:{user:{id:'owner'}}}},location:{},render(){},toast(){},$:(s)=>s==='#template-editor'?form:error,act:()=>{calls++;return new Promise(r=>resolveSave=r)},refresh:async()=>refreshes++,templatePageBase:()=>'<div>New workspace templates</div>'});
 vm.runInContext(fs.readFileSync('static/template-editor.js','utf8'),ctx);
 vm.runInContext("startTemplateEditor({name:'first-draft',body:'Private first workspace text'})",ctx);
 const pending=vm.runInContext("templateAction('template-save',{})",ctx);
 await vm.runInContext("templateAction('template-save',{})",ctx);
 assert.equal(calls,1,'rapid repeated saves must not create duplicate drafts');
 vm.runInContext("S.workspace='second';startTemplateEditor({name:'second-draft',body:'Second workspace draft'})",ctx);
 resolveSave({id:'old-response'});await pending;
 assert.equal(refreshes,0,'late save must not refresh another workspace');
 assert.equal(vm.runInContext('TE.name',ctx),'second-draft');assert.equal(vm.runInContext('TE.id',ctx),null);
 vm.runInContext("S.workspace='third'",ctx);
 assert.equal(vm.runInContext('templateEditorPage()',ctx),'<div>New workspace templates</div>');assert.equal(vm.runInContext('TE',ctx),null);
 console.log('Template save: duplicate-submit lock, delayed workspace isolation and private draft cleanup passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
