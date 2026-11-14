const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const c=vm.createContext({document:{addEventListener(){}},S:{workspace:'customer',data:{context:{role:'admin',user:{id:'owner'}},ai:{},services:{plans:[],connections:{billing:{ready:false}}}}},esc:String,ownedCommerceMoney:()=> 'INR 499',pagehead:()=>'',badge:String,btn:(label,action,attrs)=>`<button ${attrs}>${label}</button>`});
 vm.runInContext(fs.readFileSync('static/services.js','utf8'),c);
 const render=()=>vm.runInContext('customerSubscriptionPage(S.data.services)',c);
 assert.match(render(),/Subscriptions are being prepared/);
 assert.doesNotMatch(render(),/data-plan=/);
 await assert.rejects(()=>vm.runInContext("serviceAction('service-subscribe',{dataset:{plan:'missing'}})",c),/not available/);
 c.S.data.services.plans=[{key:'starter',name:'Starter',amount_minor:49900,currency:'INR',interval:'monthly'}];
 c.S.data.services.subscription_active=true;c.S.data.services.connections.billing.ready=true;
 assert.match(render(),/data-plan="starter" disabled/);
 await assert.rejects(()=>vm.runInContext("serviceAction('service-subscribe',{dataset:{plan:'starter'}})",c),/already active/);
 c.job={kind:'billing.subscription',status:'created',result:{url:'https://rzp.io/checkout',provider_status:'created'}};
 assert.match(vm.runInContext('serviceJobActions(job)',c),/Open provider checkout/);
 for(const status of ['active','authenticated','cancelled','completed','expired']){
  c.job.result.provider_status=status;
  assert.doesNotMatch(vm.runInContext('serviceJobActions(job)',c),/Open provider checkout/);
 }
 console.log('Subscription UI: unavailable checkout, active-plan guard and stale checkout links passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
