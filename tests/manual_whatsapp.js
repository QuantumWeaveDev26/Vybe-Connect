const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let input;const draftLink={dataset:{phone:'+919876543210'}};
const c=vm.createContext({esc:s=>String(s).replaceAll('"','&quot;'),document:{addEventListener(name,fn){if(name==='input')input=fn},querySelector:()=>draftLink}});
vm.runInContext(fs.readFileSync('static/manual-whatsapp.js','utf8'),c);
assert.equal(vm.runInContext("manualWhatsAppURL('+919876543210')",c),'https://wa.me/919876543210');
for(const value of ['javascript:alert(1)','https://evil.test','123','+0','919876543210?secret=1']){c.phone=value;assert.equal(vm.runInContext('manualWhatsAppURL(phone)',c),'')}
let html=vm.runInContext("manualWhatsAppAction({phone:'+919876543210'},'A & B',true)",c);assert.match(html,/text=A%20%26%20B/);assert.match(html,/noopener noreferrer/);assert.match(html,/not synced/);assert.doesNotMatch(html,/data-do="message.send"/);
assert.equal(vm.runInContext("manualWhatsAppAction({phone:'+919876543210',channel:'website'})",c),'');
input({target:{id:'compose',value:'Updated unsent draft'}});assert.equal(draftLink.href,'https://wa.me/919876543210?text=Updated%20unsent%20draft');
console.log('Manual WhatsApp links validate numbers, encode unsent drafts and explicitly avoid fake message/delivery sync.');
