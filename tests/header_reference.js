const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c=vm.createContext({document:{addEventListener(){}},esc:v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),initials:()=> 'AB',S:{data:{mention_notifications:[{read:false},{read:true}],context:{user:{name:'A <Owner>',email:'owner@example.test'}}}}});
vm.runInContext(fs.readFileSync('static/shell.js','utf8'),c);
assert.equal(vm.runInContext('typeof headerAccountMarkup',c),'function');
const html=vm.runInContext('headerAccountMarkup()',c);assert.match(html,/data-do="team-mentions"/);assert.match(html,/header-profile-toggle/);assert.match(html,/A &lt;Owner>/);assert.match(html,/data-do="account-profile"/);assert.match(html,/data-do="logout"/);assert.doesNotMatch(html,/<Owner>/);
assert.match(html,/1 unread notification/);assert.match(html,/id="header-profile-menu"[^>]*hidden/);
console.log('Header uses real notifications, escaped current-user data, existing actions and a closed-by-default profile menu.');
