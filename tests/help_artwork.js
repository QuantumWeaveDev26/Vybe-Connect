const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({S:{data:{context:{user:{name:'Alex'},role:'admin'}}},document:{addEventListener(){}},esc:String,btn:(text,action,extra='',cls='')=>`<button data-do="${action}">${text}</button>`,icon:()=>''});
vm.runInContext(fs.readFileSync('static/visuals.js','utf8'),c);vm.runInContext(fs.readFileSync('static/help-widget.js','utf8'),c);
const html=vm.runInContext('helpPanel()',c);assert.equal((html.match(/support-portrait /g)||[]).length,4);assert.doesNotMatch(html,/character-avatar/);
assert.equal(vm.runInContext('HELP_STEPS.find(s=>s.title==="AI agents").route',c),'ai-agents');
assert.doesNotMatch(fs.readFileSync('static/concept-theme.css','utf8'),/metric-characters-v2\.png/);
console.log('Help uses four clean 3D portraits, live AI route and no mockup artwork source.');
