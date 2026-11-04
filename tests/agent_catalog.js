const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const c=vm.createContext({console,S:{data:{context:{role:'admin'},ai:{enabled:false,configured:false,provider_id:'openai'},aiagents:[]}},
 esc:v=>String(v).replaceAll('<','&lt;').replaceAll('"','&quot;'),btn:(text,action,extra='',cls='')=>`<button data-do="${action}" class="${cls}" ${extra}>${text}</button>`,
 badge:(text)=>`<span>${text}</span>`,characterAvatar:name=>`<svg data-avatar="${name}"></svg>`,agentDirectoryToolbar:()=>'',agentActionSummary:()=>'',renderAI:()=>{},setInterval(){},document:{addEventListener(){}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/assistant.js'),'utf8'),c);
let html=vm.runInContext('aiAgentsPage()',c);
assert.equal((html.match(/class="agent-preset-card"/g)||[]).length,6);
assert.equal((html.match(/data-avatar=/g)||[]).length,6);
assert.match(html,/Show all 12 agents/);assert.doesNotMatch(html,/Never claim to assign|partial conversation sample/);
vm.runInContext('A.catalogExpanded=true',c);html=vm.runInContext('aiAgentsPage()',c);
assert.equal((html.match(/class="agent-preset-card"/g)||[]).length,12);
vm.runInContext('A.agentCategory="Sales"',c);html=vm.runInContext('aiAgentsPage()',c);
assert.match(html,/Ready-to-Buy/);assert.match(html,/data-preset="6"/);assert.doesNotMatch(html,/data-preset="0"/);
vm.runInContext('S.data.context.role="agent"',c);html=vm.runInContext('aiAgentsPage()',c);assert.doesNotMatch(html,/data-do="ai-preset"/);
vm.runInContext('S.data.context.role="admin";S.data.aiagents=[{id:"x",name:"Daily Digest",instructions:"<script>private instructions</script>",schedule_enabled:false}]',c);
html=vm.runInContext('aiAgentCard(S.data.aiagents[0])',c);assert.match(html,/<details/);assert.match(html,/Manage/);assert.match(html,/&lt;script>/);assert.match(html,/data-do="ai-run-agent"[^>]*disabled/);
console.log('Agent catalog: avatars, concise copy, all 12 presets, stable filtering and roles passed.');
