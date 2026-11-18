const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/workspace-loader.js','utf8');
async function scenario(fails){
 const executed=[],requests=[],timers=new Map();let next=0,booted=0;
 const app={innerHTML:'Loading',inert:true};
 const doc={getElementById:id=>id==='workspace-scripts'?{textContent:JSON.stringify(['/account.js?v=abc','/app.js?v=def'])}:id==='app'?app:id==='vybe-launch'?{remove(){}}:null,createElement:()=>({remove(){}}),head:{appendChild(script){requests.push(script.src);queueMicrotask(()=>{if(fails(script.src))script.onerror();else{executed.push(script.src.split('?')[0]);script.onload()}})}}};
 const c=vm.createContext({boot:()=>{booted++},document:doc,JSON,Promise,Error,URL,location:{origin:'https://example.test'},setTimeout:fn=>{timers.set(++next,fn);return next},clearTimeout:id=>timers.delete(id)});
 vm.runInContext(source,c);for(let i=0;i<20;i++)await new Promise(r=>setImmediate(r));return {executed,requests,app,booted};
}
(async()=>{
 let r=await scenario(url=>url.startsWith('/account')&&!url.includes('retry='));assert.deepEqual(r.executed,['/account.js','/app.js']);assert.equal(r.requests.length,3);assert.equal(r.booted,1);
 r=await scenario(url=>url.startsWith('/account'));assert.deepEqual(r.executed,[]);assert.equal(r.booted,0);assert.equal(r.requests.length,3);assert.match(r.app.innerHTML,/Reload workspace/);assert.ok(!r.requests.some(x=>x.startsWith('/app')));
 console.log('Workspace loader retries failed downloads before app startup and stops after bounded failure.');
})().catch(e=>{console.error(e);process.exitCode=1});
