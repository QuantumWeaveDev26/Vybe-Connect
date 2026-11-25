const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({S:{data:{context:{user:{name:'Alex'},role:'admin'}}},document:{addEventListener(){}},esc:String,btn:(text,action,extra='',cls='')=>`<button data-do="${action}">${text}</button>`,icon:()=>''});
vm.runInContext(fs.readFileSync('static/visuals.js','utf8'),c);vm.runInContext(fs.readFileSync('static/help-widget.js','utf8'),c);
const html=vm.runInContext('helpPanel()',c);assert.doesNotMatch(html,/support-portrait|character-avatar|help-illustration/);for(const action of ['help-ai','help-tour','help-astra'])assert.match(html,new RegExp('data-do="'+action+'"'));assert.doesNotMatch(html,/Your VYBE guide is here/);
assert.equal(vm.runInContext('HELP_STEPS.find(s=>s.title==="AI agents").route',c),'ai-agents');
assert.doesNotMatch(fs.readFileSync('static/concept-theme.css','utf8'),/metric-characters-v2\.png/);
console.log('Compact help exposes real AI, tour and custom agent actions without hidden illustration space.');
