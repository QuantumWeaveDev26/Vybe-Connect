const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const c=vm.createContext({S:{data:{services:{connections:{payments:{configured:true,ready:false},shipping:{configured:false,ready:false}}}}},badge:s=>s,document:{addEventListener(){}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/services.js'),'utf8'),c);
let html=vm.runInContext('fulfillmentConnections()',c);assert.match(html,/Activation needed/);assert.match(html,/Setup needed/);assert.doesNotMatch(html,/>Enabled/);
vm.runInContext('S.data.services.connections.payments.ready=true',c);html=vm.runInContext('fulfillmentConnections()',c);assert.match(html,/Enabled/);assert.match(html,/#services/);
console.log('Payment and shipping setup states reflect real configured and activation gates.');
