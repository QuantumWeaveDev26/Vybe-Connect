const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('static/app.js', 'utf8');
const refresh = source.slice(source.indexOf('async function refresh('), source.indexOf('async function act('));
const startup = source.slice(source.indexOf('async function retryStartupRequest('), source.indexOf('\nboot();'));

function harness(stateResponse) {
  const app = {innerHTML: 'Loading'};
  const state = {data: null, workspace: ''};
  let stateCalls = 0;
  let retry;
  const context = vm.createContext({
    S: state,
    AbortSignal,
    location: {hash: '', pathname: '/'},
    localStorage: {setItem() {}, removeItem() {}},
    hasPasswordResetHash: () => false,
    hasInvitationHash: () => false,
    empty: (title, body, button) => title + body + button,
    $: selector => selector === '#app' ? app : {addEventListener: (_, handler) => { retry = handler; }},
    render: () => { app.innerHTML = 'Workspace dashboard'; },
    renderAuth: () => { app.innerHTML = 'Sign in'; },
    setTimeout: callback => callback(),
    api: async (path, {signal}) => {
      assert.equal(signal.aborted, false);
      if (path === '/api/bootstrap') return {initialized: true, deployment: 'hosted'};
      return stateResponse(++stateCalls);
    },
  });
  vm.runInContext(refresh + startup, context);
  return {app, state, boot: () => vm.runInContext('boot()', context), calls: () => stateCalls, retry: () => retry()};
}

const workspace = {context: {tenant_id: 'workspace'}};
const unavailable = () => Object.assign(new Error('Temporary failure'), {status: 503});

(async () => {
  const transient = harness(call => {
    if (call === 1) throw unavailable();
    return workspace;
  });
  await transient.boot();
  assert.equal(transient.calls(), 2);
  assert.equal(transient.app.innerHTML, 'Workspace dashboard');

  const timeout = harness(call => {
    if (call <= 3) throw new DOMException('Timed out', 'TimeoutError');
    return workspace;
  });
  await timeout.boot();
  assert.equal(timeout.calls(), 3);
  assert.match(timeout.app.innerHTML, /Could not open VYBE Connect.*Try again/);
  assert.equal(timeout.state.data, null);
  timeout.retry();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(timeout.calls(), 4);
  assert.equal(timeout.app.innerHTML, 'Workspace dashboard');

  const signedOut = harness(() => { throw Object.assign(new Error('Sign in required'), {status: 401}); });
  await signedOut.boot();
  assert.equal(signedOut.calls(), 1);
  assert.equal(signedOut.app.innerHTML, 'Sign in');
  console.log('Startup recovers after a temporary failure, offers a retry after timeouts, and preserves sign-in.');
})().catch(error => { console.error(error); process.exitCode = 1; });
