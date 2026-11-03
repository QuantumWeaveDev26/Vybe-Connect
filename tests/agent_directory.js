const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context=vm.createContext({document:{addEventListener(){}},agentActionLabels:{tag:'Tag',note:'Note'},esc:x=>String(x).replaceAll('<','&lt;')});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../static/agent-directory.js'),'utf8'),context);
assert.equal(vm.runInContext('agentDirectoryMatches("Sales Agent","setup"," sales ","all")',context),true);
assert.equal(vm.runInContext('agentDirectoryMatches("Sales Agent","setup","sales","configured")',context),false);
assert.equal(vm.runInContext('agentDirectoryMatches("Sales Agent","setup","support","all")',context),false);
context.original={id:'original',name:'Triage',instructions:'Review facts',allowed_actions:['note'],schedule_enabled:true,interval:3600,archived:true};
const draft=vm.runInContext('agentCopyDraft(original)',context);
assert.deepEqual(JSON.parse(JSON.stringify(draft)),{name:'Triage (copy)',instructions:'Review facts',allowed_actions:['note']});
draft.allowed_actions.push('tag');assert.deepEqual(context.original.allowed_actions,['note']);
for(const [enabled,configured,gate,status] of [[false,true,true,'disabled'],[true,true,false,'setup'],[true,false,true,'setup'],[true,true,true,'configured']]){
 context.connection={enabled,connection:{configured,enabled:gate}};assert.equal(vm.runInContext('agentConnectionState(connection)',context),status);
}
console.log('Agent search, status gates and safe duplicate configuration passed.');

// Verify live DOM filtering updates cards, count and empty-state together.
const cards=[{dataset:{agentName:'Sales',agentStatus:'disabled'},hidden:false},{dataset:{agentName:'Support',agentStatus:'configured'},hidden:false}];
const search={value:''},filter={value:'configured'},count={},empty={};
context.document={querySelector(selector){return selector.includes('data-agent-search')?search:selector.includes('data-agent-filter')?filter:selector.includes('data-agent-count')?count:empty},querySelectorAll(){return cards}};
vm.runInContext('filterAgentDirectory("external")',context);
assert.deepEqual(cards.map(c=>c.hidden),[true,false]);assert.equal(count.textContent,'1 of 2 agents');assert.equal(empty.hidden,true);
search.value='missing';vm.runInContext('filterAgentDirectory("external")',context);assert.equal(count.textContent,'0 of 2 agents');assert.equal(empty.hidden,false);
console.log('Rendered directory card visibility, result count and no-match state passed.');
