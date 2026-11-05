const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const callbacks=[];
const c=vm.createContext({document:{addEventListener(){}},setInterval(fn){callbacks.push(fn)},structuredClone,esc:String,btn:(label,action,extra='')=>`<button data-do="${action}" ${extra}>${label}</button>`,location:{hash:''}});
vm.runInContext(fs.readFileSync('static/assistant.js','utf8'),c);
(async()=>{
 for(const callback of callbacks)await callback(); // Deliberately before app.js defines S and $.
 c.S={route:'templates',review:false,data:{meta:{configured:true},context:{workspace:{name:'Test'}}}};
 vm.runInContext(fs.readFileSync('static/template-editor.js','utf8'),c);c.render=()=>{};
 vm.runInContext('startTemplateEditor()',c);
 let html=vm.runInContext('templateEditorPage()',c);assert.doesNotMatch(html,/<option[^>]*>AUTHENTICATION/);assert.match(html,/<option[^>]*>UTILITY/);
 vm.runInContext('startTemplateEditor({category:"AUTHENTICATION",body:"A synced OTP template",id:"existing"})',c);
 html=vm.runInContext('templateEditorPage()',c);assert.match(html,/Authentication templates are read-only/);assert.match(html,/<fieldset[^>]*disabled/);assert.match(html,/data-do="template-submit" disabled/);
 console.log('Slow-start polling is safe before app initialization; unsupported OTP editing cannot be submitted.');
})().catch(e=>{console.error(e);process.exitCode=1});
