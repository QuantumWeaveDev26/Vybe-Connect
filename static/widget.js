/**
 * VYBE Connect — Standalone Embeddable Website Live Chat Widget
 * Integrates directly with the VYBE Connect Team Inbox & AI Agents.
 */
(function() {
  'use strict';
  if (window.VybeWidgetLoaded) return;
  window.VybeWidgetLoaded = true;

  const script = document.currentScript || document.querySelector('script[data-workspace]');
  const workspace = script?.dataset?.workspace || window.VYBE_WORKSPACE || '';
  const brandTitle = script?.dataset?.title || window.VYBE_WIDGET_TITLE || 'VYBE Connect';
  const brandColor = script?.dataset?.color || window.VYBE_WIDGET_COLOR || '#108449';
  const apiUrl = (script?.src ? new URL(script.src).origin : window.location.origin);

  let visitorToken = localStorage.getItem('vybe_widget_session_' + workspace) || '';
  let contactId = localStorage.getItem('vybe_widget_contact_' + workspace) || '';
  let visitorName = localStorage.getItem('vybe_widget_name_' + workspace) || '';
  let visitorPhone = localStorage.getItem('vybe_widget_phone_' + workspace) || '';
  let isOpen = false;
  let isSending = false;
  let historyTimer=null;
  let historyLoading=false;

  // Inject Styles
  const style = document.createElement('style');
  style.textContent = `
    #vybe-widget-root { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 14px; color: #28352f; z-index: 999999; }
    #vybe-widget-btn { position: fixed; bottom: 24px; right: 24px; width: 60px; height: 60px; border-radius: 50%; background: ${brandColor}; color: #fff; border: none; cursor: pointer; box-shadow: 0 4px 20px rgba(16,132,73,0.35); display: flex; align-items: center; justify-content: center; transition: transform 0.25s, box-shadow 0.25s; z-index: 999999; }
    #vybe-widget-btn:hover { transform: scale(1.06); box-shadow: 0 6px 26px rgba(16,132,73,0.45); }
    #vybe-widget-btn svg { width: 28px; height: 28px; fill: currentColor; }
    #vybe-widget-window { position: fixed; bottom: 96px; right: 24px; width: 360px; height: 530px; max-height: calc(100vh - 120px); max-width: calc(100vw - 48px); background: #ffffff; border-radius: 18px; box-shadow: 0 12px 40px rgba(0,0,0,0.18); display: none; flex-direction: column; overflow: hidden; border: 1px solid #dff0e6; z-index: 999999; animation: vybeSlideUp 0.28s ease; }
    @keyframes vybeSlideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
    .vw-head { background: ${brandColor}; color: #fff; padding: 16px; display: flex; align-items: center; justify-content: space-between; }
    .vw-head-info { display: flex; align-items: center; gap: 10px; }
    .vw-avatar { width: 36px; height: 36px; border-radius: 50%; background: #ffffff25; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; }
    .vw-head h4 { margin: 0; font-size: 15px; font-weight: 600; }
    .vw-head p { margin: 2px 0 0; font-size: 11px; opacity: 0.88; display: flex; align-items: center; gap: 5px; }
    .vw-dot { width: 7px; height: 7px; background: #5bf79b; border-radius: 50%; display: inline-block; }
    .vw-close { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; padding: 4px; line-height: 1; opacity: 0.85; }
    .vw-close:hover { opacity: 1; }
    .vw-messages { flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; background: #f8fbf9; }
    .vw-msg { max-width: 80%; padding: 10px 14px; border-radius: 14px; line-height: 1.45; font-size: 13.5px; word-break: break-word; }
    .vw-msg.in { align-self: flex-start; background: #ffffff; border: 1px solid #e1ebe4; color: #203328; border-bottom-left-radius: 3px; }
    .vw-msg.out { align-self: flex-end; background: ${brandColor}; color: #ffffff; border-bottom-right-radius: 3px; }
    .vw-msg-time { font-size: 10px; opacity: 0.65; margin-top: 4px; text-align: right; }
    .vw-buttons { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .vw-btn-chip { background: #eaf6ef; color: ${brandColor}; border: 1px solid #bde3cc; border-radius: 12px; padding: 4px 10px; font-size: 12px; cursor: pointer; transition: all 0.15s; }
    .vw-btn-chip:hover { background: ${brandColor}; color: #fff; }
    .vw-form { padding: 12px; border-top: 1px solid #eef4f0; background: #fff; display: flex; flex-direction: column; gap: 8px; }
    .vw-input-row { display: flex; gap: 8px; }
    .vw-input { flex: 1; border: 1px solid #d4e2d9; border-radius: 10px; padding: 9px 12px; font-size: 13px; outline: none; transition: border-color 0.15s; }
    .vw-input:focus { border-color: ${brandColor}; }
    .vw-send-btn { background: ${brandColor}; color: #fff; border: none; border-radius: 10px; padding: 0 16px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
    .vw-send-btn:disabled { opacity: 0.5; cursor: default; }
    .vw-footer { text-align: center; font-size: 10px; color: #8ea196; padding: 4px; background: #fff; }
  `;
  document.head.appendChild(style);

  // Inject HTML Elements
  const root = document.createElement('div');
  root.id = 'vybe-widget-root';
  root.innerHTML = `
    <button id="vybe-widget-btn" aria-label="Open chat" type="button">
      <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>
    </button>
    <div id="vybe-widget-window" role="dialog" aria-label="${brandTitle}">
      <div class="vw-head">
        <div class="vw-head-info">
          <div class="vw-avatar">V</div>
          <div>
            <h4>${brandTitle}</h4>
            <p><span class="vw-dot"></span> Online · Replies in minutes</p>
          </div>
        </div>
        <button class="vw-close" id="vybe-widget-close" aria-label="Close chat">&times;</button>
      </div>
      <div class="vw-messages" id="vybe-messages">
        <div class="vw-msg in">
          Hello! How can we help you today? Leave us a message and our team will get right back to you.
        </div>
      </div>
      <div class="vw-form">
        ${!visitorName ? `
          <div class="vw-input-row" id="vw-visitor-fields">
            <input class="vw-input" id="vw-name" placeholder="Your name" value="${visitorName}" />
            <input class="vw-input" id="vw-phone" placeholder="Phone or Email" value="${visitorPhone}" />
          </div>
        ` : ''}
        <div class="vw-input-row">
          <input class="vw-input" id="vw-text" placeholder="Type your message…" autocomplete="off" />
          <button class="vw-send-btn" id="vw-send" type="button">Send</button>
        </div>
      </div>
      <div class="vw-footer">Powered by VYBE Connect AI</div>
    </div>
  `;
  document.body.appendChild(root);

  const btn = document.getElementById('vybe-widget-btn');
  const win = document.getElementById('vybe-widget-window');
  const closeBtn = document.getElementById('vybe-widget-close');
  const msgContainer = document.getElementById('vybe-messages');
  const input = document.getElementById('vw-text');
  const sendBtn = document.getElementById('vw-send');

  function toggle() {
    isOpen = !isOpen;
    win.style.display = isOpen ? 'flex' : 'none';
    clearInterval(historyTimer);
    if(isOpen) historyTimer=setInterval(()=>{if(!isSending && contactId && visitorToken)loadHistory()},5000);
    if (isOpen) {
      input.focus();
      if (contactId && visitorToken) loadHistory();
    }
  }

  btn.onclick = toggle;
  closeBtn.onclick = toggle;

  function renderMessage(text, direction) {
    const div = document.createElement('div');
    div.className = 'vw-msg ' + (direction === 'in' ? 'out' : 'in'); // from visitor perspective: visitor msg is 'out', agent/inbox reply is 'in'
    
    // Check for interactive button pills
    const parts = text.split('\n\n🔘 ');
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

  async function loadHistory() {
    if (!contactId || !workspace || historyLoading) return;
    historyLoading=true;
    try {
      const res = await fetch(`${apiUrl}/api/widget/history?workspace=${encodeURIComponent(workspace)}&contact_id=${encodeURIComponent(contactId)}`, {headers: {'X-Visitor-Token': visitorToken}});
      if (res.status === 401) { visitorToken=''; contactId=''; localStorage.removeItem('vybe_widget_session_' + workspace); localStorage.removeItem('vybe_widget_contact_' + workspace); return; }
      if (!res.ok) return;
      const data = await res.json();
      if (data.messages && data.messages.length) {
        msgContainer.innerHTML = '';
        data.messages.forEach(m => renderMessage(m.body, m.direction));
      }
    } catch (_) {} finally {historyLoading=false;}
  }

  async function sendMessage(text) {
    const msg = (text || input.value || '').trim();
    if (!msg || isSending) return;

    const nameInput = document.getElementById('vw-name');
    const phoneInput = document.getElementById('vw-phone');
    if (nameInput?.value) {
      visitorName = nameInput.value.trim();
      localStorage.setItem('vybe_widget_name_' + workspace, visitorName);
    }
    if (phoneInput?.value) {
      visitorPhone = phoneInput.value.trim();
      localStorage.setItem('vybe_widget_phone_' + workspace, visitorPhone);
    }

    renderMessage(msg, 'in'); // visitor message
    input.value = '';
    isSending = true;
    sendBtn.disabled = true;

    try {
      const res = await fetch(`${apiUrl}/api/widget/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace,
          visitor_token: visitorToken,
          name: visitorName || 'Website Visitor',
          phone: visitorPhone,
          message: msg
        })
      });
      if (!res.ok) throw new Error("Message was not delivered. Please try again.");
      if (res.ok) {
        const data = await res.json();
        visitorToken = data.visitor_token || visitorToken;
        localStorage.setItem('vybe_widget_session_' + workspace, visitorToken);
        if (data.contact_id) {
          contactId = data.contact_id;
          localStorage.setItem('vybe_widget_contact_' + workspace, contactId);
          document.getElementById('vw-visitor-fields')?.remove();
        }
        if (data.messages && data.messages.length) {
          // Re-render recent messages including any auto-reply
          msgContainer.innerHTML = '';
          data.messages.forEach(m => renderMessage(m.body, m.direction));
        }
      }
    } catch (_) {
      renderMessage("Message was not delivered. Please try again.", "out");
    } finally {
      isSending = false;
      sendBtn.disabled = false;
    }
  }

  sendBtn.onclick = () => sendMessage();
  input.onkeydown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  };

  // Expose API
  window.VybeWidget = {
    open: () => { if (!isOpen) toggle(); },
    close: () => { if (isOpen) toggle(); },
    send: sendMessage
  };
})();
