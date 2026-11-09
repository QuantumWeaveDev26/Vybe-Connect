const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const script=fs.readFileSync('static/widget-preview.js','utf8');
function check(search){
 const button={disabled:false,addEventListener(type,fn){this.click=fn}},code={},notice={};let opened=0;
 const window={VybeWidget:{open(){opened++}}};
 vm.runInNewContext(script,{URLSearchParams,location:{search,origin:'https://example.test'},window,document:{querySelector(s){return s==='#open-widget-preview'?button:s==='#widget-embed-code'?code:notice}}});
 return {button,code,notice,window,opened:()=>opened};
}
let page=check('?workspace=1234567890abcdef');
assert.equal(page.window.VYBE_WORKSPACE,'1234567890abcdef');
assert.match(page.code.textContent,/data-workspace="1234567890abcdef"/);page.button.click();assert.equal(page.opened(),1);
for(const search of ['','?workspace=bad','?workspace=%22%3E%3Cscript%3E']){page=check(search);assert.equal(page.window.VYBE_WORKSPACE,'');assert.equal(page.button.disabled,true)}
assert.doesNotMatch(fs.readFileSync('static/widget-preview.html','utf8'),/onclick=/);
console.log('Website setup binds only valid workspaces and uses CSP-compatible controls.');
