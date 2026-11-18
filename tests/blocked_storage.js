const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('static/app.js','utf8');
const prelude=source.slice(0,source.indexOf('let formSubmit'));
const context=vm.createContext({Map,location:{hash:''},document:{querySelector(){}}});
vm.runInContext("Object.defineProperty(globalThis,'localStorage',{get(){throw new Error('SecurityError: browser storage blocked')}})",context);
assert.doesNotThrow(()=>vm.runInContext(prelude,context),'Blocked site storage must not prevent workspace startup');
vm.runInContext("workspaceStorage.setItem('tw_workspace','current');if(workspaceStorage.getItem('tw_workspace')!=='current')throw Error('fallback failed');workspaceStorage.removeItem('tw_workspace');if(workspaceStorage.getItem('tw_workspace')!==null)throw Error('remove failed')",context);
console.log('Workspace initializes with browser storage denied; preferences fall back to page memory.');
