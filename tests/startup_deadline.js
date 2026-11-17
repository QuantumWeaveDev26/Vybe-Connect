const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/app.js','utf8');
const retry=source.slice(source.indexOf('async function retryStartupRequest('),source.indexOf('function showStartupError('));
(async()=>{
 for(const support of [false,true]){
  let calls=0;
  const context=vm.createContext({AbortSignal:{},...(support?{AbortController}:{}),Promise,Error,
   setTimeout:(callback,delay)=>setTimeout(callback,delay===4000?5:0),clearTimeout});
  vm.runInContext(retry,context);context.request=()=>{calls++;return new Promise(()=>{})};
  let watchdog;
  try{
   await assert.rejects(Promise.race([vm.runInContext('retryStartupRequest(request)',context),new Promise((_,reject)=>{watchdog=setTimeout(()=>reject(new Error('Startup deadline never completed')),150)})]),error=>error.name==='TimeoutError');
  }finally{clearTimeout(watchdog)}
  assert.equal(calls,3);
 }
 const refresh=source.slice(source.indexOf('async function refresh('),source.indexOf('async function act('));
 let resolve;const controller=new AbortController(),state={data:null,workspace:''};
 const context=vm.createContext({S:state,api:()=>new Promise(done=>{resolve=done}),localStorage:{setItem(){}},render(){throw new Error('Late request rendered a stale workspace')},toast(){}});
 vm.runInContext(refresh,context);context.signal=controller.signal;
 const pending=vm.runInContext('refresh({starting:true,signal})',context);
 controller.abort(new Error('Expired startup request'));resolve({context:{tenant_id:'stale'}});
 await assert.rejects(pending,/Expired startup request/);assert.equal(state.data,null);
 for(const loading of [true,false]){
  let deadline,reload,removed=false;
  const app={innerHTML:'Existing content',inert:true,querySelector:()=>loading?{}:null};
  const ctx=vm.createContext({setTimeout:fn=>{deadline=fn},document:{getElementById:id=>id==='app'?app:id==='vybe-launch'?{remove(){removed=true}}:{addEventListener:(_,fn)=>{reload=fn}}},location:{reload(){removed='reloaded'}}});
  vm.runInContext(fs.readFileSync('static/startup-guard.js','utf8'),ctx);deadline();
  if(loading){assert.match(app.innerHTML,/Reload workspace/);assert.equal(app.inert,false);assert.equal(removed,true);reload();assert.equal(removed,'reloaded')}
  else assert.equal(app.innerHTML,'Existing content');
 }
 console.log('Startup has a hard deadline even without AbortSignal.timeout or abort support.');
})().catch(error=>{console.error(error);process.exitCode=1});
