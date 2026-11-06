const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({Date,JSON,Object,Array,String,Number,Math,document:{addEventListener(){}},S:{data:{context:{role:'admin'},ai:{platform_managed:true,enabled:true,allowance:{active:true,remaining:3,limit:5}},services:{platform_ai_mode:true,platform_admin:false,subscription_active:true,plans:[],connections:{billing:{ready:false}}}}},badge:x=>x,esc:x=>String(x??'').replace(/</g,'&lt;'),pagehead:(a,b)=>`<h1>${a}</h1><p>${b}</p>`,btn:(a,b,d)=>`<button data-do="${b}" ${d||''}>${a}</button>`});
vm.runInContext(fs.readFileSync('static/business.js','utf8'),c);vm.runInContext(fs.readFileSync('static/services.js','utf8'),c);
let card=vm.runInContext('aiConnectionCard()',c);assert.match(card,/No API key needed/);assert.doesNotMatch(card,/data-ai-connection|type="password"|Connect OpenAI/);
let page=vm.runInContext('servicesPage()',c);assert.match(page,/Your subscription/);assert.doesNotMatch(page,/KEY SECRET|WEBHOOK|Server configuration|Check openai|Client onboarding|TW_BILLING/);
vm.runInContext('S.data.ai.enabled=false;S.data.ai.allowance={active:false};S.data.services.subscription_active=false',c);card=vm.runInContext('aiConnectionCard()',c);assert.match(card,/Choose your subscription/);
console.log('Customers see subscription and included AI, without platform credential controls.');
