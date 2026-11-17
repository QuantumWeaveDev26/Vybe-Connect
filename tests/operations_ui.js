const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const c=vm.createContext({document:{addEventListener(){}},S:{workspace:'qa',data:{context:{role:'admin',user:{id:'owner'}},members:[{id:'owner',name:'Owner'}],calling:{ready:false,calls:[{id:'call',status:'ended',owner:'owner',direction:'inbound',notes:[{body:'<script>private</script>',author:'owner',created:100}],connected_at:100,ended:130}],requests:[]},contacts:[]}},esc:v=>String(v).replaceAll('<','&lt;'),badge:String,btn:(label,action,attrs)=>`<button data-do="${action}" ${attrs||''}>${label}</button>`,refresh:async()=>{},render:()=>{},field:()=>'',showModal:(title,html,submit)=>{c.submit=submit},$:()=>({close(){c.closed=true}})});
 vm.runInContext(fs.readFileSync('static/services.js','utf8'),c);
 let html=vm.runInContext('voiceCallsPanel()',c);assert.match(html,/30s connected/);assert.doesNotMatch(html,/<script>/);assert.match(html,/&lt;script>/);
 c.act=async()=>({calls:[],next_before:null});await vm.runInContext("voiceAction('voice-history',{dataset:{}})",c);
 assert.match(vm.runInContext('voiceCallsPanel()',c),/disabled>History loaded/);
 c.S.workspace='other';vm.runInContext('checkVoiceScope()',c);assert.equal(c.S.callHistory,null);
 c.S.data.calling.access=false;assert.doesNotMatch(vm.runInContext('voiceCallsPanel()',c),/private/);
 let resolve;c.S.workspace='qa';c.S.data.calling.access=true;c.act=()=>new Promise(r=>resolve=r);
 vm.runInContext("voiceLocalAction('voice-note',{dataset:{id:'call'}})",c);
 const pending=c.submit({body:'Internal note'});c.S.workspace='changed';resolve({});await pending;assert.notEqual(c.closed,true);
 console.log('Call history completion, note escaping, permission hiding and stale-workspace handling passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
