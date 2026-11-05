const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const listeners={},calls=[];
const context=vm.createContext({console,JSON,String,Boolean,Object,Array,Promise,clearTimeout(){},setTimeout(){return 1},
 settingsPage(){return ''},aiConnectionCard(){return ''},pagehead(){return ''},badge(v){return v},date(v){return String(v)},esc(v){return String(v).replaceAll('<','&lt;')},
 S:{workspace:'workspace',data:{context:{role:'admin',user:{id:'owner'}},meta:{},whatsapp_connection:{status:'not_connected',signup_available:true}}},
 document:{addEventListener(){},querySelector(){return null}},window:{addEventListener(name,fn){listeners[name]=fn}},
 act(operation,data){calls.push({operation,data});return Promise.resolve({})},refresh(){return Promise.resolve()},toast(){}});
vm.runInContext(fs.readFileSync('static/whatsapp-connect.js','utf8'),context);
let html=vm.runInContext('settingsPage()',context);assert.match(html,/data-wa-connect >Connect WhatsApp/);
vm.runInContext('S.data.context.role="agent"',context);html=vm.runInContext('settingsPage()',context);assert.match(html,/data-wa-connect disabled/);
vm.runInContext('S.data.context.role="admin";WA_SIGNUP={scope:whatsappScope(),opened:true,config:{state:"state"},code:"code"}',context);
const message={type:'WA_EMBEDDED_SIGNUP',event:'FINISH',data:{waba_id:'123',phone_number_id:'456'}};
listeners.message({origin:'https://www.facebook.com.evil.test',data:JSON.stringify(message)});assert.equal(calls.length,0);
listeners.message({origin:'https://www.facebook.com',data:JSON.stringify(message)});assert.equal(calls.length,1);assert.equal(calls[0].operation,'whatsapp.finish');
listeners.message({origin:'https://www.facebook.com',data:JSON.stringify(message)});assert.equal(calls.length,1,'repeated completion cannot dispatch twice');
vm.runInContext('WA_SIGNUP={scope:"another:workspace",opened:true,config:{state:"state"},code:"code"}',context);
listeners.message({origin:'https://www.facebook.com',data:JSON.stringify(message)});assert.equal(calls.length,1,'stale workspace cannot complete');
console.log('WhatsApp signup: administrator controls, trusted origins, single completion and stale workspace isolation passed.');
