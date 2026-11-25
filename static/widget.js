/**
 * VYBE Connect — Standalone Embeddable Website Live Chat Widget
 * Integrates directly with the VYBE Connect Team Inbox & AI Agents.
 */
(function() {
  'use strict';
  if (window.VybeWidgetLoaded) return;

  const script = document.currentScript || document.querySelector('script[data-workspace]');
  const workspace = script?.dataset?.workspace || window.VYBE_WORKSPACE || '';
  const brandTitle = script?.dataset?.title || window.VYBE_WIDGET_TITLE || 'VYBE Connect';
  if (!/^[a-f0-9]{16}$/.test(workspace)) return;
  window.VybeWidgetLoaded = true;
  const requestedColor = script?.dataset?.color || window.VYBE_WIDGET_COLOR;
  const brandColor = /^#[a-f0-9]{6}$/i.test(requestedColor || '') ? requestedColor : '#6037d6';
  const apiUrl = script?.src ? new URL(script.src).origin : window.location.origin;
  const storageKey = key => 'vybe_widget_' + key + '_' + workspace;
  function read(key) {
    try { return localStorage.getItem(storageKey(key)) || ''; } catch (_) { return ''; }
  }
  function save(key, value) {
    try {
      if (value) localStorage.setItem(storageKey(key), value);
      else localStorage.removeItem(storageKey(key));
    } catch (_) {}
  }

  let visitorToken = read('session');
  let contactId = read('contact');
  let visitorName = read('name');
  const visitorPhone = read('phone');
  let historySignature = '';
  let isOpen = false;
  let isSending = false;
  let historyTimer=null;
  let historyLoading=false;

  // Inject Styles
  const style = document.createElement('style');
  style.textContent = `
    #vybe-widget-root { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 14px; color: #292735; z-index: 999999; }
    #vybe-widget-btn { position: fixed; bottom: 24px; right: 24px; width: 60px; height: 60px; border-radius: 50%; background: ${brandColor}; color: #fff; border: none; cursor: pointer; box-shadow: 0 4px 20px #2f214a30; display: flex; align-items: center; justify-content: center; transition: transform 0.25s, box-shadow 0.25s; z-index: 999999; }
    #vybe-widget-btn:hover { transform: scale(1.06); box-shadow: 0 6px 26px #2f214a40; }
    #vybe-widget-btn svg { width: 28px; height: 28px; fill: currentColor; }
    #vybe-widget-window { position: fixed; bottom: 96px; right: 24px; width: 360px; height: 530px; max-height: calc(100dvh - 120px); max-width: calc(100vw - 48px); background: #ffffff; border-radius: 18px; box-shadow: 0 12px 40px rgba(0,0,0,0.18); display: none; flex-direction: column; overflow: hidden; border: 1px solid #e8e6ee; z-index: 999999; animation: vybeSlideUp 0.28s ease; }
    @keyframes vybeSlideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
    .vw-head { background: #fff; border-bottom: 1px solid #eeedf2; color: #292735; padding: 14px; display: flex; align-items: center; justify-content: space-between; }
    .vw-head-info { display: flex; align-items: center; gap: 10px; }
    .vw-avatar { width: 36px; height: 36px; border-radius: 50%; background: #f1ebfb; color: #5534a6; flex: none; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; }
    .vw-head h4 { margin: 0; font-size: 15px; font-weight: 600; }
    .vw-head p { margin: 2px 0 0; font-size: 11px; opacity: 0.88; display: flex; align-items: center; gap: 5px; }

    .vw-close { background: none; border: none; color: #41364d; font-size: 22px; min-width: 44px; min-height: 44px; cursor: pointer; padding: 4px; line-height: 1; opacity: 0.85; }
    .vw-close:hover { opacity: 1; }
    .vw-messages { flex: 1; min-height: 0; padding: 16px; overflow-y: auto; overscroll-behavior: contain; display: flex; flex-direction: column; gap: 10px; background: #f7f6fa; }
    .vw-msg { max-width: 80%; padding: 10px 14px; border-radius: 14px; line-height: 1.45; font-size: 13.5px; overflow-wrap: anywhere; white-space: pre-wrap; }
    .vw-msg.in { align-self: flex-start; background: #ffffff; border: 1px solid #e8e6ee; color: #292735; border-bottom-left-radius: 3px; }
    .vw-msg.out { align-self: flex-end; background: ${brandColor}; color: #ffffff; border-bottom-right-radius: 3px; }
    .vw-msg-time { font-size: 10px; opacity: 0.65; margin-top: 4px; text-align: right; }
    .vw-buttons { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .vw-btn-chip { background: #f3effb; color: ${brandColor}; border: 1px solid #ded3f4; border-radius: 12px; padding: 4px 10px; font-size: 12px; cursor: pointer; transition: all 0.15s; }
    .vw-btn-chip:hover { background: ${brandColor}; color: #fff; }
    .vw-form { padding: 12px; border-top: 1px solid #eeedf2; background: #fff; display: flex; flex-direction: column; gap: 8px; }
    .vw-input-row { display: flex; gap: 8px; }
    .vw-input { flex: 1; min-width: 0; box-sizing: border-box; border: 1px solid #ddd7e7; border-radius: 10px; padding: 9px 12px; font-size: 13px;  transition: border-color 0.15s; }
    .vw-input:focus { border-color: ${brandColor}; }
    .vw-send-btn { background: ${brandColor}; color: #fff; border: none; border-radius: 10px; padding: 0 13px; min-height: 44px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
    .vw-send-btn:disabled { opacity: 0.5; cursor: default; }
    .vw-empty { margin: auto 0; background: #fff; border: 1px solid #e8e6ee; padding: 16px; border-radius: 12px; }
    .vw-empty strong { font-size: 16px; }
    .vw-empty p { font-size: 13px; line-height: 1.5; margin: 8px 0 0; color: #62596d; }
    .vw-status { margin: 0; font-size: 12px; color: #62596d; }
    .vw-status:empty { display: none; }
    #vybe-widget-root :focus-visible { outline: 2px solid #6037d6; outline-offset: 2px; }
    @media (max-width: 480px), (max-height: 480px) {
      #vybe-widget-btn { right: 14px; bottom: max(14px, env(safe-area-inset-bottom)); width: 50px; height: 50px; }
      #vybe-widget-window {
        right: 14px;
        bottom: max(72px, calc(58px + env(safe-area-inset-bottom)));
        width: 320px;
        max-width: calc(100vw - 28px);
        height: 350px;
        max-height: min(65dvh, calc(100dvh - max(84px, calc(70px + env(safe-area-inset-bottom)))));
        border-radius: 14px;
      }
      .vw-head, .vw-messages, .vw-form { padding: 10px 12px; }
      .vw-input { font-size: 16px; }
    }
    @media (max-height: 480px) {
      #vybe-widget-window { bottom: max(14px, env(safe-area-inset-bottom)); }
      .vw-head, .vw-form { padding-block: 6px; }
      .vw-close { min-height: 38px; }
    }
    @media(prefers-reduced-motion: reduce) {
      #vybe-widget-window { animation: none; }
      #vybe-widget-btn { transition: none; }
    }
  `;
  document.head.appendChild(style);

  // Inject HTML Elements
  const root = document.createElement('div');
  root.id = 'vybe-widget-root';
  root.innerHTML = `
    <button id="vybe-widget-btn" aria-label="Open chat" aria-expanded="false" aria-controls="vybe-widget-window" type="button">
      <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>
    </button>
    <div id="vybe-widget-window" role="dialog" aria-labelledby="vybe-widget-title">
      <div class="vw-head">
        <div class="vw-head-info">
          <div class="vw-avatar">V</div>
          <div>
            <h4 id="vybe-widget-title"></h4>
            <p>Website chat</p>
          </div>
        </div>
        <button class="vw-close" id="vybe-widget-close" aria-label="Close chat" type="button">&times;</button>
      </div>
      <div class="vw-messages" id="vybe-messages" role="log" aria-label="Conversation">
        <div class="vw-empty"><strong>How can we help?</strong><p>Send a message to our team. Return to this chat to check for replies.</p></div>
      </div>
      <form class="vw-form" id="vybe-widget-form">
        ${!contactId ? `
          <div class="vw-input-row" id="vw-visitor-fields">
            <input class="vw-input" id="vw-name" placeholder="Name (optional)" aria-label="Your name" autocomplete="name" maxlength="120" />
          </div>
        ` : ''}
        <p class="vw-status" id="vybe-widget-status" role="status"></p>
        <div class="vw-input-row">
          <input class="vw-input" id="vw-text" placeholder="Write a message…" aria-label="Message" autocomplete="off" maxlength="4000" />
          <button class="vw-send-btn" id="vw-send" type="submit">Send</button>
        </div>
      </form>
    </div>
  `;
  document.body.appendChild(root);

  const btn = document.getElementById('vybe-widget-btn');
  const win = document.getElementById('vybe-widget-window');
  const closeBtn = document.getElementById('vybe-widget-close');
  const msgContainer = document.getElementById('vybe-messages');
  const input = document.getElementById('vw-text');
  const sendBtn = document.getElementById('vw-send');
  const status = document.getElementById('vybe-widget-status');
  document.getElementById('vybe-widget-title').textContent = String(brandTitle).slice(0,120);
  const nameField = document.getElementById('vw-name');
  if (nameField) nameField.value = visitorName;

  function toggle() {
    isOpen = !isOpen;
    win.style.display = isOpen ? 'flex' : 'none';
    btn.setAttribute('aria-expanded', String(isOpen));
    btn.hidden = isOpen;
    btn.style.display = isOpen ? 'none' : '';
    clearInterval(historyTimer);
    if(isOpen) historyTimer=setInterval(()=>{if(!isSending && contactId && visitorToken)loadHistory()},5000);
    if (isOpen) {
      const focusTarget = window.matchMedia?.('(max-width: 480px), (max-height: 480px)').matches ? closeBtn : input;
      focusTarget.focus();
      if (contactId && visitorToken) loadHistory();
    } else {
      btn.focus();
    }
  }

  btn.onclick = toggle;
  closeBtn.onclick = toggle;
  win.addEventListener('keydown', event => { if (event.key === 'Escape' && isOpen) toggle(); });

  function renderMessage(text, direction) {
    const div = document.createElement('div');
    div.className = 'vw-msg ' + (direction === 'in' ? 'out' : 'in'); // from visitor perspective: visitor msg is 'out', agent/inbox reply is 'in'

    // Check for interactive button pills
    const parts = direction === 'out' ? String(text || '').split('\n\n🔘 ') : [String(text || '')];
    const mainText = parts[0];
    div.textContent = mainText;

    if (parts[1]) {
      const btnBar = document.createElement('div');
      btnBar.className = 'vw-buttons';
      parts[1].split(' · ').forEach(btnTitle => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'vw-btn-chip';
        chip.textContent = btnTitle.trim();
        chip.onclick = () => sendMessage(btnTitle.trim());
        btnBar.appendChild(chip);
      });
      div.appendChild(btnBar);
    }

    msgContainer.appendChild(div);
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }

  function showHistory(messages) {
    if (!Array.isArray(messages) || !messages.length) return;
    const signature = JSON.stringify(messages.map(m => [m.id, m.body, m.direction]));
    if (signature === historySignature) return;
    historySignature = signature;
    msgContainer.replaceChildren();
    messages.forEach(m => renderMessage(m.body, m.direction));
  }

  async function loadHistory() {
    if (!contactId || !visitorToken || historyLoading || isSending) return;
    const token = visitorToken;
    const contact = contactId;
    historyLoading = true;
    try {
      const query = new URLSearchParams({workspace, contact_id: contact});
      const res = await fetch(`${apiUrl}/api/widget/history?${query}`, {headers: {'X-Visitor-Token': token}});
      if (isSending || visitorToken !== token || contactId !== contact) return;
      if (res.status === 401) {
        visitorToken = '';
        contactId = '';
        historySignature = '';
        save('session', '');
        save('contact', '');
        msgContainer.replaceChildren();
        status.textContent = 'This chat session ended. Send a message to start a new one.';
        return;
      }
      if (!res.ok) return;
      const data = await res.json();
      if (!isSending && visitorToken === token && contactId === contact) showHistory(data.messages);
    } catch (_) {
      // Keep the last confirmed conversation visible while polling retries.
    } finally {
      historyLoading = false;
    }
  }

  async function sendMessage(text) {
    const msg = (typeof text === 'string' ? text : input.value).trim();
    if (!msg || isSending) return;
    if (msg.length > 4000) {
      status.textContent = 'Use 4,000 characters or fewer.';
      return;
    }
    const nameInput = document.getElementById('vw-name');
    const name = nameInput?.value.trim() || visitorName;
    const draft = input.value;
    isSending = true;
    sendBtn.disabled = true;
    status.textContent = 'Sending…';
    try {
      const res = await fetch(`${apiUrl}/api/widget/message`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({workspace, visitor_token: visitorToken, name: name || 'Website Visitor', phone: visitorPhone, message: msg})
      });
      if (!res.ok) throw new Error('Message could not be confirmed.');
      const data = await res.json();
      visitorToken = data.visitor_token || visitorToken;
      contactId = data.contact_id || contactId;
      visitorName = name;
      save('session', visitorToken);
      save('contact', contactId);
      save('name', visitorName);
      if (contactId) document.getElementById('vw-visitor-fields')?.remove();
      showHistory(data.messages);
      if (typeof text !== 'string' && input.value === draft) input.value = '';
      status.textContent = 'Message sent';
    } catch (_) {
      status.textContent = 'Could not confirm your message. Check the conversation before retrying.';
    } finally {
      isSending = false;
      sendBtn.disabled = false;
    }
  }

  document.getElementById('vybe-widget-form').addEventListener('submit', event => {
    event.preventDefault();
    void sendMessage();
  });

  // Expose API
  window.VybeWidget = {
    open: () => { if (!isOpen) toggle(); },
    close: () => { if (isOpen) toggle(); },
    send: sendMessage
  };
})();
