/* עוזר AI – כפתור צף וחלון שיחה ללוח המשימות.
 *
 * הוספה ללוח (שורה אחת לפני </body>):
 *   <script src="/assistant/static/assistant-widget.js" defer></script>
 *
 * כדי שהעוזר יידע על איזו משימה עובדים, הלוח יכול להגדיר פונקציה שמחזירה טקסט:
 *   window.assistantContext = () => "לקוח: עמרני אייל\nמשימה: התאמת בנק לאוקטובר\nאחראית: נינה";
 */
(function () {
  'use strict';
  if (window.__assistantWidget) return;
  window.__assistantWidget = true;

  const API = '/api/assistant';
  const STORE = 'office_assistant_history_v1';

  const css = `
  .oa-fab{position:fixed;bottom:20px;left:20px;z-index:2147483000;display:flex;align-items:center;gap:8px;background:#1f6f5c;color:#fff;border:none;border-radius:999px;padding:12px 18px;font:700 14px/1 Assistant,Arial,sans-serif;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.25)}
  .oa-fab:hover{filter:brightness(1.08)}
  .oa-panel{position:fixed;bottom:80px;left:20px;z-index:2147483001;width:400px;max-width:calc(100vw - 32px);height:600px;max-height:calc(100dvh - 110px);background:#fff;color:#1d2422;border:1px solid #d9dfdb;border-radius:14px;box-shadow:0 18px 50px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;direction:rtl;font:14px/1.6 Assistant,Arial,sans-serif}
  .oa-panel.open{display:flex}
  .oa-head{background:#1f6f5c;color:#fff;padding:12px 14px;display:flex;align-items:center;justify-content:space-between;gap:8px}
  .oa-head b{font-size:15px}.oa-head small{display:block;font-size:11.5px;opacity:.85}
  .oa-btns{display:flex;gap:4px}
  .oa-ib{background:rgba(255,255,255,.16);border:none;color:#fff;border-radius:8px;width:30px;height:30px;cursor:pointer;font-size:14px}
  .oa-ib:hover{background:rgba(255,255,255,.3)}
  .oa-body{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;background:#f7f8f6}
  .oa-msg{max-width:90%;padding:10px 12px;border-radius:14px;white-space:pre-wrap;word-wrap:break-word}
  .oa-bot{align-self:flex-start;background:#fff;border:1px solid #d9dfdb;border-top-right-radius:4px}
  .oa-user{align-self:flex-end;background:#1f6f5c;color:#fff;border-top-left-radius:4px}
  .oa-note{display:block;margin-top:6px;font-size:11.5px;color:#5d6763}
  .oa-ctx{font-size:12px;color:#5d6763;background:#e3f0eb;border-radius:8px;padding:6px 10px;align-self:stretch}
  .oa-chips{display:flex;flex-wrap:wrap;gap:6px}
  .oa-chip{background:#fff;border:1px solid #d9dfdb;color:#1d2422;border-radius:999px;padding:6px 10px;font:12.5px Assistant,Arial,sans-serif;cursor:pointer}
  .oa-chip:hover{border-color:#1f6f5c;color:#1f6f5c}
  .oa-foot{border-top:1px solid #d9dfdb;padding:10px;display:flex;gap:8px;background:#fff}
  .oa-foot textarea{flex:1;resize:none;height:44px;padding:10px 12px;border:1px solid #d9dfdb;border-radius:10px;font:14px Assistant,Arial,sans-serif;direction:rtl}
  .oa-foot textarea:focus{outline:2px solid #1f6f5c;outline-offset:1px}
  .oa-send{background:#1f6f5c;color:#fff;border:none;border-radius:10px;padding:0 14px;font:700 14px Assistant,Arial,sans-serif;cursor:pointer}
  .oa-send:disabled{opacity:.5;cursor:default}
  .oa-dots{display:inline-flex;gap:3px}.oa-dots i{width:6px;height:6px;border-radius:50%;background:#5d6763;animation:oaDot 1s infinite}
  .oa-dots i:nth-child(2){animation-delay:.15s}.oa-dots i:nth-child(3){animation-delay:.3s}
  @keyframes oaDot{0%,80%,100%{opacity:.25}40%{opacity:1}}
  @media(max-width:520px){.oa-panel{left:16px;right:16px;width:auto;bottom:76px}.oa-fab{left:16px;bottom:16px}}
  @media print{.oa-fab,.oa-panel{display:none!important}}`;

  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  const fab = document.createElement('button');
  fab.type = 'button';
  fab.className = 'oa-fab';
  fab.innerHTML = '<span>✨</span><span>עוזר AI</span>';

  const panel = document.createElement('div');
  panel.className = 'oa-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'עוזר AI');
  panel.innerHTML = `
    <div class="oa-head">
      <div><b>עוזר AI</b><small>איך עושים? איפה מוצאים? למי מעבירים?</small></div>
      <div class="oa-btns">
        <button class="oa-ib" data-act="clear" title="שיחה חדשה" aria-label="שיחה חדשה">🗑️</button>
        <button class="oa-ib" data-act="close" title="סגירה" aria-label="סגירה">✕</button>
      </div>
    </div>
    <div class="oa-body"></div>
    <div class="oa-foot">
      <textarea placeholder="לדוגמה: איך עושים התאמת בנק?" rows="1"></textarea>
      <button class="oa-send" type="button">שליחה</button>
    </div>`;

  document.body.appendChild(fab);
  document.body.appendChild(panel);

  const body = panel.querySelector('.oa-body');
  const input = panel.querySelector('textarea');
  const send = panel.querySelector('.oa-send');

  let history = [];
  try { history = JSON.parse(sessionStorage.getItem(STORE) || '[]'); } catch (e) { history = []; }
  const save = () => { try { sessionStorage.setItem(STORE, JSON.stringify(history.slice(-20))); } catch (e) {} };

  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

  function getContext() {
    try {
      if (typeof window.assistantContext === 'function') return String(window.assistantContext() || '');
      const el = document.querySelector('[data-assistant-context]');
      if (el) return el.getAttribute('data-assistant-context') || '';
    } catch (e) {}
    return '';
  }

  function add(cls, html) {
    const d = document.createElement('div');
    d.className = 'oa-msg ' + cls;
    d.innerHTML = html;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
    return d;
  }

  function chips(list) {
    const w = document.createElement('div');
    w.className = 'oa-chips';
    list.forEach(q => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'oa-chip'; b.textContent = q;
      b.onclick = () => { w.remove(); ask(q); };
      w.appendChild(b);
    });
    body.appendChild(w);
  }

  async function welcome() {
    body.innerHTML = '';
    add('oa-bot', 'שלום! 👋 אני העוזר של המשרד.\nאפשר לשאול אותי <b>איך עושים</b> פעולה, <b>איפה מוצאים</b> נתון או <b>למי מעבירים</b> נושא.');
    const ctx = getContext();
    if (ctx) {
      const c = document.createElement('div');
      c.className = 'oa-ctx';
      c.textContent = '📌 אני רואה את המשימה הפתוחה: ' + ctx.split('\n')[0];
      body.appendChild(c);
    }
    history.forEach(m => add(m.role === 'user' ? 'oa-user' : 'oa-bot', m.role === 'user' ? esc(m.content) : fmt(m.content)));
    if (!history.length) {
      try {
        const r = await fetch(API + '/topics');
        const j = await r.json();
        chips((j.topics || []).slice(0, 6));
      } catch (e) {}
    }
  }

  async function ask(q) {
    q = (q || '').trim();
    if (!q || send.disabled) return;
    add('oa-user', esc(q));
    input.value = '';
    send.disabled = true;
    const wait = add('oa-bot', '<span class="oa-dots"><i></i><i></i><i></i></span>');
    try {
      const r = await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ question: q, history, context: getContext() }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
      let html = fmt(j.answer || '');
      if (j.source === 'kb') html += '<span class="oa-note">' + (j.note ? '⚠️ ' + esc(j.note) + ' – ' : '') + 'תשובה מתוך נהלי המשרד</span>';
      wait.innerHTML = html;
      history.push({ role: 'user', content: q }, { role: 'assistant', content: j.answer || '' });
      save();
    } catch (e) {
      wait.innerHTML = 'לא הצלחתי לקבל תשובה (' + esc(e.message) + '). נסי שוב בעוד רגע.';
    }
    send.disabled = false;
    body.scrollTop = body.scrollHeight;
    input.focus();
  }

  fab.onclick = () => {
    const open = panel.classList.toggle('open');
    if (open) { if (!body.children.length) welcome(); input.focus(); }
  };
  panel.querySelector('[data-act=close]').onclick = () => panel.classList.remove('open');
  panel.querySelector('[data-act=clear]').onclick = () => { history = []; save(); welcome(); };
  send.onclick = () => ask(input.value);
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(input.value); } });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') panel.classList.remove('open'); });
})();
