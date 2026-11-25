const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({esc:s=>String(s).replaceAll('"','&quot;')});
vm.runInContext(fs.readFileSync('static/manual-whatsapp.js','utf8'),c);
assert.equal(vm.runInContext("manualWhatsAppURL('+919876543210')",c),'https://wa.me/919876543210');
for(const value of ['javascript:alert(1)','https://evil.test','123','+0','919876543210?secret=1']){c.phone=value;assert.equal(vm.runInContext('manualWhatsAppURL(phone)',c),'')}
let html=vm.runInContext("manualWhatsAppBanner({phone:'+919876543210'})",c);
assert.match(html,/Reply in WhatsApp/);
assert.match(html,/noopener noreferrer/);
assert.match(html,/not synced/);
assert.doesNotMatch(html,/data-do="message.send"|[?]text=|data-manual-draft/);
assert.equal(vm.runInContext("manualWhatsAppAction({phone:'+919876543210',channel:'website'})",c),'');
assert.equal(vm.runInContext("manualWhatsAppURL('+919876543210','private draft')",c),'https://wa.me/919876543210');
console.log('Manual WhatsApp links validate numbers, keep private drafts out of links and explicitly avoid fake message/delivery sync.');
