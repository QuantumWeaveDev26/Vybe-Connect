const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function check(search){
 const button=()=>({addEventListener(_,fn){this.click=fn}});
 const nodes={'#open-widget-preview':button(),'#copy-widget-link':button(),'#widget-preview-notice':{},'#widget-chat-link':{focus(){},select(){this.selected=true}},'#widget-back':{},'#widget-page-title':{}};
 let opened=0;
 const window={VybeWidget:{open(){opened++}}};
 const clipboard={writeText:async value=>{clipboard.value=value}};
 vm.runInNewContext(fs.readFileSync('static/widget-preview.js','utf8'),{URLSearchParams,location:{search,origin:'https://example.test'},navigator:{clipboard},window,document:{querySelector:id=>nodes[id]}});
 return {open:nodes['#open-widget-preview'],copy:nodes['#copy-widget-link'],field:nodes['#widget-chat-link'],window,clipboard,opened:()=>opened};
}
(async()=>{
 let page=check('?workspace=1234567890abcdef');
 assert.equal(page.window.VYBE_WORKSPACE,'1234567890abcdef');
 page.open.click();assert.equal(page.opened(),1);
 await page.copy.click();assert.equal(page.clipboard.value,'https://example.test/widget-preview?workspace=1234567890abcdef&chat=1');
 page.clipboard.writeText=async()=>{throw Error('Clipboard blocked')};
 await page.copy.click();assert.equal(page.field.selected,true);
 assert.equal(check('?workspace=1234567890abcdef&chat=1').copy.hidden,true);
 for(const search of ['','?workspace=bad','?workspace=%22%3E%3Cscript%3E']){
  page=check(search);assert.equal(page.window.VYBE_WORKSPACE,'');assert.equal(page.open.disabled,true);
 }
 assert.doesNotMatch(fs.readFileSync('static/widget-preview.html','utf8'),/onclick=|widget-embed-code/);
 console.log('Website chat, share link, clipboard fallback and invalid workspace gates passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
