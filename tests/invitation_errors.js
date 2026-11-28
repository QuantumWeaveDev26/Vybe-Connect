'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

async function run() {
  let submit;
  let request;
  let calls = 0;
  const shown = [];
  const context = vm.createContext({
    S: {data: {context: {tenant_id: 'team', user: {id: 'owner'}, role: 'admin', workspace: {name: 'Team'}}}},
    field: () => '',
    showModal: (_title, _markup, callback) => { submit = callback; },
    act: () => { calls++; return request; },
    refresh: async () => {},
    toast: () => {}
  });
  const source = fs.readFileSync(path.join(__dirname, '../static/team-invitations.js'), 'utf8');
  vm.runInContext(source, context);
  context.captureInvite = invite => shown.push(invite);
  vm.runInContext('showShareableInvitation = captureInvite', context);
  await vm.runInContext("invitationAction('invite-create', {})", context);

  const data = {email: 'teammate@example.test', role: 'agent', hours: 24};
  let reject;
  request = new Promise((_resolve, fail) => { reject = fail; });
  const first = submit(data);
  await submit(data);
  assert.equal(calls, 1, 'duplicate clicks must not repeat an in-flight request');
  reject(Object.assign(new Error('The server returned an unreadable response. Refresh and try again.'), {status: 200}));
  await assert.rejects(first, /Invite unconfirmed.*pending invite/);
  assert.deepEqual(shown, []);

  request = Promise.reject(Object.assign(new Error('Please sign in.'), {status: 401}));
  await assert.rejects(submit(data), /Session expired.*Sign in again/);

  request = Promise.resolve({token: 'test-only'});
  await submit(data);
  assert.equal(calls, 3);
  assert.deepEqual(shown, [{token: 'test-only'}]);
  console.log('Interrupted invite, duplicate prevention, expired session and success passed.');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
