const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const start=source.indexOf('async function api('),end=source.indexOf('\n',start);assert.ok(start>=0);
const c=vm.createContext({S:{workspace:'workspace',review:false},fetch:async()=>({ok:false,status:503,json:async()=>{throw new SyntaxError('Unexpected token')}})});
vm.runInContext(source.slice(start,end),c);
(async()=>{await assert.rejects(vm.runInContext('api("/api/state")',c),e=>e.status===503&&e.message==='The service is restarting. Try again in a moment.');
c.fetch=async()=>({ok:false,status:401,json:async()=>({error:'Sign in required'})});await assert.rejects(vm.runInContext('api("/api/state")',c),e=>e.status===401&&e.message==='Sign in required');console.log('API failures retain status and show actionable text instead of JSON parsing errors.');})().catch(e=>{console.error(e);process.exitCode=1});
