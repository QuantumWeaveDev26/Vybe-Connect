const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/app.js','utf8');
const fn=source.slice(source.indexOf('async function sendConversationMessage('),source.indexOf('function inboxPage('));
function harness(){const calls=[];const c=vm.createContext({S:{data:{context:{tenant_id:'team'}},chat:'contact',draft:'Hello'},document:{querySelectorAll:()=>[]},$:()=>({open:false,close(){}}),render(){},refresh:async()=>{},act:async(action,data)=>{calls.push({action,data});return {}},Error});vm.runInContext(fn,c);return {c,calls,send:()=>vm.runInContext("sendConversationMessage({contactId:'contact',scope:'team',mode:'note',body:'Hello',resolve:true})",c)}}
(async()=>{
 let h=harness();await h.send();assert.deepEqual(h.calls.slice(0,2).map(x=>x.action),['message.send','chat.update']);assert.equal(h.calls[0].data.note,true);assert.equal(h.calls[1].data.status,'solved');assert.equal(h.c.S.draft,'');
 h=harness();h.c.act=async()=>{throw Error('Send rejected')};await assert.rejects(h.send,/Send rejected/);assert.equal(h.c.S.draft,'Hello');assert.equal(h.c.S.messageSending,false);
 h=harness();h.c.act=async action=>{if(action==='chat.update')throw Error('Status rejected');return {}};await assert.rejects(h.send,/Do not resend/);assert.equal(h.c.S.draft,'','A successful send must not remain as a resendable draft after resolve fails');
 h=harness();let finish;h.c.act=()=>new Promise(r=>finish=r);const pending=h.send();await h.send();h.c.S.data.context.tenant_id='other';h.c.S.draft='New workspace draft';finish({});await pending;assert.equal(h.c.S.draft,'New workspace draft');
 console.log('Send and resolve preserves order, rejected drafts, successful-send safety and workspace boundaries.');
})().catch(e=>{console.error(e);process.exitCode=1});
