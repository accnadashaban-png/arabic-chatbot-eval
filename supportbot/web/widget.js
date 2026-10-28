/*
 * Support widget: a launcher button in the corner that opens a chat panel.
 *
 *   <script src="https://your-bot-host/widget.js" data-api="https://your-bot-host" data-name="Support" defer></script>
 *
 * Optional attributes: data-lang="ar|en" (default: the page's lang), data-position="right|left".
 * Everything renders inside a Shadow DOM, so the host page's styles cannot break it and it cannot break them.
 * All text is inserted as text, never as HTML.
 */
(() => {
  const script = document.currentScript;
  const api = (script && script.dataset.api) || "";
  const name = (script && script.dataset.name) || "Support";
  const side = (script && script.dataset.position) === "left" ? "left" : "right";
  const pageLang = () => ((script && script.dataset.lang) || document.documentElement.lang || "en").slice(0, 2) === "ar" ? "ar" : "en";

  const T = {
    en: { hello: "Hi! I'm the virtual assistant. How can I help you today?", placeholder: "Write a message…", online: "Online · replies in seconds",
          note: "Automated assistant · our team can take over anytime", open: "Open chat", close: "Close chat", send: "Send",
          handoff: "Passed to our support team", error: "Something went wrong. Please try again.",
          chips: ["How much is the subscription?", "How do I cancel?", "I forgot my password", "Talk to a person"] },
    ar: { hello: "أهلًا! أنا المساعد الآلي. إزاي أقدر أساعدك النهارده؟", placeholder: "اكتب رسالتك…", online: "متصل · بيرد في ثواني",
          note: "مساعد آلي · فريق الدعم يقدر يكمل معاك في أي وقت", open: "افتح المحادثة", close: "اقفل المحادثة", send: "إرسال",
          handoff: "اتحوّلت لفريق الدعم", error: "حصلت مشكلة، جرّب تاني.",
          chips: ["الاشتراك بكام؟", "إزاي ألغي الاشتراك؟", "نسيت الباسورد", "عايز أكلم حد"] },
  };

  const css = `
    :host { all: initial; }
    * { box-sizing: border-box; font-family: "Inter", "IBM Plex Sans Arabic", system-ui, -apple-system, "Segoe UI", Tahoma, sans-serif; }
    .wrap { --bg:#0F131C; --panel:#151A25; --raise:#1C2230; --line:#262D3D; --fg:#E8EBF2; --muted:#8C94A8; --faint:#5F677C;
            --accent:#7C6CFF; --accent2:#5B4BEB; --ok:#34D399; --warn:#F5B454;
            position: fixed; bottom: 22px; ${side}: 22px; z-index: 2147483000; color: var(--fg); font-size: 14.5px; line-height: 1.55; }
    .launcher { width: 58px; height: 58px; border-radius: 50%; border: 0; cursor: pointer; display: grid; place-items: center; color: #fff;
                background: linear-gradient(145deg, var(--accent), var(--accent2)); box-shadow: 0 10px 30px rgba(91,75,235,.45), 0 2px 6px rgba(0,0,0,.35);
                transition: transform .18s ease, box-shadow .18s ease; margin-${side}: auto; display: flex; align-items: center; justify-content: center; }
    .launcher:hover { transform: translateY(-2px) scale(1.03); }
    .launcher:focus-visible, button:focus-visible { outline: 2px solid #A99CFF; outline-offset: 3px; }
    textarea:focus-visible { outline: none; }
    .launcher svg { width: 26px; height: 26px; transition: transform .2s ease, opacity .2s ease; }
    .panel { position: absolute; bottom: 74px; ${side}: 0; width: 380px; height: min(620px, calc(100vh - 110px)); background: var(--bg);
             border: 1px solid var(--line); border-radius: 20px; overflow: hidden; display: flex; flex-direction: column;
             box-shadow: 0 24px 70px rgba(0,0,0,.55), 0 4px 14px rgba(0,0,0,.35);
             transform-origin: bottom ${side}; transition: transform .2s ease, opacity .2s ease; }
    .panel[hidden] { display: flex; opacity: 0; transform: translateY(12px) scale(.96); pointer-events: none; visibility: hidden; }
    header { display: flex; align-items: center; gap: 12px; padding: 16px 16px 14px; background: linear-gradient(180deg, #171C29, var(--bg));
             border-bottom: 1px solid var(--line); }
    .avatar { width: 38px; height: 38px; border-radius: 12px; flex: none; display: grid; place-items: center;
              background: linear-gradient(145deg, var(--accent), var(--accent2)); }
    .avatar svg { width: 22px; height: 22px; }
    .title { font-weight: 650; font-size: 15px; letter-spacing: -.01em; }
    .status { font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px; }
    .status i { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 0 3px rgba(52,211,153,.18); }
    .x { margin-inline-start: auto; width: 32px; height: 32px; border-radius: 10px; border: 0; background: transparent; color: var(--muted); cursor: pointer;
         display: grid; place-items: center; }
    .x:hover { background: var(--raise); color: var(--fg); }
    .log { flex: 1; overflow-y: auto; padding: 18px 14px 8px; display: flex; flex-direction: column; gap: 10px; scrollbar-width: thin;
           scrollbar-color: var(--line) transparent; }
    .msg { max-width: 82%; padding: 10px 13px; border-radius: 16px; white-space: pre-wrap; overflow-wrap: anywhere; }
    .bot { align-self: flex-start; background: var(--raise); border: 1px solid var(--line); border-end-start-radius: 6px; }
    .me { align-self: flex-end; background: linear-gradient(145deg, var(--accent), var(--accent2)); color: #fff; border-end-end-radius: 6px; }
    .tag { align-self: flex-start; font-size: 11.5px; color: var(--warn); background: rgba(245,180,84,.1); border: 1px solid rgba(245,180,84,.25);
           padding: 3px 9px; border-radius: 999px; margin-top: -4px; }
    .typing { align-self: flex-start; display: flex; gap: 4px; padding: 13px 14px; background: var(--raise); border: 1px solid var(--line); border-radius: 16px; }
    .typing span { width: 6px; height: 6px; border-radius: 50%; background: var(--muted); animation: blink 1.2s infinite ease-in-out; }
    .typing span:nth-child(2) { animation-delay: .15s; } .typing span:nth-child(3) { animation-delay: .3s; }
    @keyframes blink { 0%, 80%, 100% { opacity: .25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-2px); } }
    .chips { display: flex; flex-wrap: wrap; gap: 7px; padding: 6px 14px 10px; }
    .chips button { flex: none; border: 1px solid #3A3480; background: rgba(124,108,255,.08); color: #C9C2FF; border-radius: 999px; padding: 7px 12px;
                    font-size: 13px; cursor: pointer; white-space: nowrap; }
    .chips button:hover { background: rgba(124,108,255,.18); }
    form { display: flex; align-items: flex-end; gap: 8px; margin: 0 12px; padding: 8px 8px 8px 14px; background: var(--panel);
           border: 1px solid var(--line); border-radius: 16px; }
    form:focus-within { border-color: #4A42A8; }
    textarea { flex: 1; resize: none; border: 0; outline: 0; background: transparent; color: var(--fg); font-size: 14.5px; line-height: 1.5;
               max-height: 110px; padding: 6px 0; }
    textarea::placeholder { color: var(--faint); }
    .send { width: 36px; height: 36px; flex: none; border: 0; border-radius: 11px; cursor: pointer; color: #fff; display: grid; place-items: center;
            background: linear-gradient(145deg, var(--accent), var(--accent2)); }
    .send:disabled { opacity: .35; cursor: default; }
    .send svg { width: 18px; height: 18px; }
    .wrap[dir="rtl"] .send svg { transform: scaleX(-1); }
    .note { text-align: center; font-size: 11px; color: var(--faint); padding: 8px 12px 12px; }
    @media (max-width: 480px) {
      .wrap { bottom: 16px; ${side}: 16px; }
      .panel { position: fixed; inset: 0; width: 100%; height: 100%; border-radius: 0; border: 0; }
    }`;

  const ICON_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.4 8.4 0 0 1-9 8.3 8.9 8.9 0 0 1-4-.9L3 20l1.2-4.2A8.2 8.2 0 0 1 3 11.5 8.6 8.6 0 0 1 12 3a8.6 8.6 0 0 1 9 8.5Z"/></svg>';
  const ICON_X = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>';
  const ICON_SEND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13M13 6l6 6-6 6"/></svg>';
  const ICON_SPARK = '<svg viewBox="0 0 24 24" fill="#fff"><path d="M11 3.5c.6 4.7 2.8 6.9 7.5 7.5-4.7.6-6.9 2.8-7.5 7.5-.6-4.7-2.8-6.9-7.5-7.5 4.7-.6 6.9-2.8 7.5-7.5Z"/><path opacity=".7" d="M18.5 2c.2 1.5.9 2.2 2.4 2.4-1.5.2-2.2.9-2.4 2.4-.2-1.5-.9-2.2-2.4-2.4 1.5-.2 2.2-.9 2.4-2.4Z"/></svg>';

  const host = document.createElement("div");
  host.setAttribute("data-support-widget", "");
  const root = host.attachShadow({ mode: "closed" });
  root.innerHTML = `<style>${css}</style>
    <div class="wrap">
      <section class="panel" role="dialog" aria-modal="false" hidden>
        <header><div class="avatar">${ICON_SPARK}</div>
          <div><div class="title"></div><div class="status"><i></i><span class="online"></span></div></div>
          <button class="x" type="button">${ICON_X}</button></header>
        <div class="log" aria-live="polite"></div>
        <div class="chips"></div>
        <form><textarea rows="1" maxlength="1000"></textarea><button class="send" type="submit">${ICON_SEND}</button></form>
        <div class="note"></div>
      </section>
      <button class="launcher" type="button" aria-expanded="false">${ICON_CHAT}</button>
    </div>`;

  const $ = (s) => root.querySelector(s);
  const panel = $(".panel"), log = $(".log"), chips = $(".chips"), input = $("textarea"), send = $(".send"), launcher = $(".launcher");
  const messages = [];
  let lang = pageLang(), started = false, busy = false;

  function texts() {
    const t = T[lang];
    $(".wrap").dir = lang === "ar" ? "rtl" : "ltr";
    $(".title").textContent = name;
    $(".online").textContent = t.online;
    $(".note").textContent = t.note;
    input.placeholder = t.placeholder;
    send.setAttribute("aria-label", t.send);
    $(".x").setAttribute("aria-label", t.close);
    launcher.setAttribute("aria-label", panel.hidden ? t.open : t.close);
    panel.setAttribute("aria-label", name);
    chips.replaceChildren(...(started ? [] : t.chips.map((c) => {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = c; b.onclick = () => ask(c);
      return b;
    })));
    chips.hidden = started;
  }

  function bubble(text, who) {
    const d = document.createElement("div");
    d.className = `msg ${who}`; d.dir = "auto"; d.textContent = text;
    log.appendChild(d); log.scrollTop = log.scrollHeight;
    return d;
  }

  function note(text) {
    const d = document.createElement("div");
    d.className = "tag"; d.textContent = text; log.appendChild(d);
  }

  function toggle(open) {
    panel.hidden = !open;
    launcher.innerHTML = open ? ICON_X : ICON_CHAT;
    launcher.setAttribute("aria-expanded", String(open));
    if (open && !log.childElementCount) bubble(T[lang].hello, "bot");
    texts();
    if (open) setTimeout(() => input.focus(), 50);
  }

  async function ask(text) {
    if (busy || !text.trim()) return;
    busy = true; send.disabled = true; started = true; texts();
    bubble(text, "me");
    messages.push({ role: "user", content: text });
    const typing = document.createElement("div");
    typing.className = "typing"; typing.innerHTML = "<span></span><span></span><span></span>";
    log.appendChild(typing); log.scrollTop = log.scrollHeight;
    try {
      const r = await fetch(`${api}/v1/chat/completions`, { method: "POST", headers: { "Content-Type": "application/json" },
                                                            body: JSON.stringify({ messages: messages.slice(-20) }) });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "error");
      const reply = data.choices[0].message.content;
      messages.push({ role: "assistant", content: reply });
      typing.remove();
      bubble(reply, "bot");
      if (data.supportbot && data.supportbot.behavior === "handoff") note(T[lang].handoff);
    } catch (e) {
      typing.remove();
      bubble(T[lang].error, "bot");
    } finally {
      busy = false; send.disabled = false; input.focus(); log.scrollTop = log.scrollHeight;
    }
  }

  launcher.onclick = () => toggle(panel.hidden);
  $(".x").onclick = () => toggle(false);
  root.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) toggle(false); });
  $("form").onsubmit = (e) => { e.preventDefault(); const v = input.value; input.value = ""; input.style.height = ""; ask(v); };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("form").requestSubmit(); } });
  input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = `${Math.min(input.scrollHeight, 110)}px`; });
  new MutationObserver(() => { const l = pageLang(); if (l !== lang) { lang = l; texts(); } })
    .observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });

  texts();
  (document.body || document.documentElement).appendChild(host);
})();
