const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({document:{addEventListener(){}},S:{data:{context:{role:'admin'},services:{internal_use:true,platform_ai_mode:true,platform_admin:false,plans:[],connections:{}},ai:{platform_managed:true,allowance:{active:false,internal_use:true},enabled:false}}},badge:x=>x,esc:String,pagehead:(a,b)=>`<h1>${a}</h1><p>${b}</p>`,btn:()=>''});
vm.runInContext(fs.readFileSync('static/services.js','utf8'),c);vm.runInContext(fs.readFileSync('static/business.js','utf8'),c);
let html=vm.runInContext('servicesPage()',c);assert.match(html,/Internal team/);assert.match(html,/No subscription/);assert.doesNotMatch(html,/Subscribe|Choose your plan|Checkout coming soon/);
html=vm.runInContext('aiConnectionCard()',c);assert.match(html,/AI usage is paused/);assert.doesNotMatch(html,/Choose your subscription|Subscription needed/);
c.S.data.ai.allowance={active:true,internal_use:true,budget_paise:29900,budget_remaining_paise:28000,remaining:900,limit:1000};
html=vm.runInContext('servicesPage()',c);assert.match(html,/299\.00 monthly spending cap/);assert.match(html,/280\.00/);assert.doesNotMatch(html,/NaN|Subscription needed/);
c.S.data.ai.enabled=true;assert.equal(vm.runInContext('aiConnectionCard()',c),'');
console.log('Internal billing is distinct from paid subscriptions and does not promise free provider usage.');
