const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
(async()=>{
 const handlers={};let calls=0,offline=false;
 const c=vm.createContext({URL,Response,fetch:async()=>{calls++;if(offline)throw Error('offline');return new Response('current network build')},self:{location:{origin:'https://app.example.test'},addEventListener(k,v){handlers[k]=v},skipWaiting:async()=>{},clients:{claim:async()=>{}}}});
 vm.runInContext(fs.readFileSync('static/service-worker.js','utf8'),c);
 for(const req of [{method:'POST',mode:'navigate',url:'https://app.example.test/api/action'},{method:'GET',mode:'cors',url:'https://app.example.test/api/state'},{method:'GET',mode:'navigate',url:'https://other.example.test/'}])handlers.fetch({request:req,respondWith(){throw Error('Private/API/non-navigation requests must not be intercepted')}});
 assert.equal(calls,0);
 async function navigate(){let result;handlers.fetch({request:{method:'GET',mode:'navigate',url:'https://app.example.test/'},respondWith(p){result=p}});return result}
 assert.equal(await (await navigate()).text(),'current network build');offline=true;
 const failure=await navigate();assert.equal(failure.status,503);assert.match(await failure.text(),/Messages, changes and AI requests are not sent while offline/);assert.equal(failure.headers.get('Cache-Control'),'no-store');
 const source=fs.readFileSync('static/service-worker.js','utf8');assert.doesNotMatch(source,/caches\.|indexedDB|localStorage/);
 const m=JSON.parse(fs.readFileSync('static/manifest.webmanifest'));assert.equal(m.display,'standalone');assert.equal(m.scope,'/');assert.deepEqual(m.icons.map(i=>i.sizes),['192x192','512x512']);
 console.log('Install manifest and network-only worker: API traffic untouched, current builds fetched, truthful offline fallback, no private caches.');
})().catch(e=>{console.error(e);process.exitCode=1});
