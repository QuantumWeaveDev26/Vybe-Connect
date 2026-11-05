const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const listeners={},input={value:'private-input',type:'password'},modal={dataset:{},open:true,innerHTML:'form',close(){this.open=false}};
 const effects={calls:[],form:null};
 const ctx=vm.createContext({JSON,String,Number,Boolean,Object,Array,Math,Date,Set,Promise,
 S:{workspace:'one',data:{context:{tenant_id:'one',role:'admin',user:{id:'owner'}},ai:{provider:'OpenAI',model:'model-id',configured:false,requested_enabled:true}}},
 document:{addEventListener(name,fn){(listeners[name]??=[]).push(fn)}},
 $:selector=>selector==='#modal'?modal:selector==='#ai-connection-key'?input:null,
 esc:value=>String(value).replaceAll('<','&lt;'),badge:value=>value,aiRuntimeLabel:()=> 'AI requests paused',formSubmit:null,
 showModal(title,html,handler){effects.form={title,html,handler}},act(operation,data){effects.calls.push({operation,data:JSON.parse(JSON.stringify(data))});return Promise.resolve({})},refresh(){return Promise.resolve()},toast(){},confirm(){return true}});
 vm.runInContext(fs.readFileSync('static/business.js','utf8'),ctx);
 const html=vm.runInContext('aiConnectionCard()',ctx);assert.match(html,/Connect OpenAI/);assert.match(html,/Saving a key does not run a test/);assert.doesNotMatch(html,/TW_AI_|private-input/);
 const el={disabled:false,dataset:{aiConnection:'save'}};
 for(const fn of listeners.click)await fn({target:{closest(selector){return selector==='[data-ai-connection]'?el:null}}});
 assert.match(effects.form.html,/type="password"/);assert.match(effects.form.html,/name="enabled"/);assert.doesNotMatch(effects.form.html,/<input[^>]*name="enabled"[^>]*\schecked(?:[\s=>])/,'spending must not be pre-enabled');
 const data={key:'sk-'+'x'.repeat(40),model:'model-id',enabled:false};await effects.form.handler(data);
 assert.equal(effects.calls[0].operation,'ai.connection.save');assert.equal(effects.calls[0].data.enabled,false);assert.equal(data.key,'');assert.equal(input.value,'');
 vm.runInContext('S.data.context.role="agent"',ctx);assert.doesNotMatch(vm.runInContext('aiConnectionCard()',ctx),/data-ai-connection/);
 vm.runInContext('S.data.context.role="admin";S.workspace="other";clearAIConnectionDialog()',ctx);assert.equal(modal.innerHTML,'');assert.equal(modal.open,false);
 console.log('AI connection UI: admin-only controls, spending off by default, masked key input and workspace-change cleanup passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
