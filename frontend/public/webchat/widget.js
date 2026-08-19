/**
 * Wow Chat — embeddable web chat widget
 *
 * Usage (add to any website's <body>):
 *
 *   <script
 *     src="https://wow.gpayauto.org/webchat/widget.js"
 *     data-widget-key="YOUR_WIDGET_KEY"
 *     data-primary-color="#6366f1"          (optional)
 *     data-bot-name="Support"               (optional)
 *     data-position="bottom-right"          (optional: bottom-left)
 *   ></script>
 */
(function () {
  "use strict";

  // ── Config from script tag attributes ──────────────────────────────────────
  var script = document.currentScript ||
    document.querySelector('script[data-widget-key]');
  if (!script) return;

  var WIDGET_KEY    = script.getAttribute("data-widget-key");
  var PRIMARY       = script.getAttribute("data-primary-color") || "#6366f1";
  var BOT_NAME      = script.getAttribute("data-bot-name")      || "AI Assistant";
  var POSITION      = script.getAttribute("data-position")      || "bottom-right";
  var API_BASE      = script.src.replace(/\/webchat\/widget\.js.*$/, "");
  var WS_BASE       = API_BASE.replace(/^http/, "ws");

  if (!WIDGET_KEY) {
    console.warn("[WowChat] data-widget-key is required.");
    return;
  }

  // ── State ──────────────────────────────────────────────────────────────────
  var sessionId    = null;
  var ws           = null;
  var wsReady      = false;
  var messageQueue = [];     // messages sent before WS ready
  var pendingMsgs  = [];     // messages sent by visitor, awaiting echo or reply
  var isOpen       = false;
  var botName      = BOT_NAME;
  var welcomeMsg   = null;
  var reconnectTimer = null;
  var reconnectDelay = 1000;

  // Persist session across page loads (24 h TTL handled server-side)
  var STORAGE_KEY = "wowchat_session_" + WIDGET_KEY;
  var storedSession = null;
  try { storedSession = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); } catch(_) {}
  if (storedSession && Date.now() - storedSession.ts > 86400000) { storedSession = null; }

  // ── Shadow DOM setup ───────────────────────────────────────────────────────
  var host = document.createElement("div");
  host.id = "wowchat-host";
  host.style.cssText = "position:fixed;z-index:2147483647;" +
    (POSITION === "bottom-left" ? "left:24px;" : "right:24px;") +
    "bottom:24px;font-family:system-ui,-apple-system,sans-serif;";
  document.body.appendChild(host);

  var shadow = host.attachShadow({ mode: "open" });

  // ── CSS ────────────────────────────────────────────────────────────────────
  var style = document.createElement("style");
  style.textContent = [
    ":host{all:initial}",
    "*{box-sizing:border-box;margin:0;padding:0}",

    /* Bubble */
    "#bubble{width:56px;height:56px;border-radius:50%;background:VAR_PRIMARY;",
    "display:flex;align-items:center;justify-content:center;cursor:pointer;",
    "box-shadow:0 4px 20px rgba(0,0,0,.25);transition:transform .15s,box-shadow .15s;}",
    "#bubble:hover{transform:scale(1.08);box-shadow:0 6px 24px rgba(0,0,0,.3);}",
    "#bubble svg{fill:none;stroke:#fff;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;}",
    "#badge{position:absolute;top:-3px;right:-3px;min-width:18px;height:18px;",
    "background:#ef4444;color:#fff;border-radius:9px;font-size:11px;font-weight:700;",
    "display:none;align-items:center;justify-content:center;padding:0 4px;}",

    /* Panel */
    "#panel{display:none;flex-direction:column;position:absolute;",
    POSITION === "bottom-left" ? "left:0;" : "right:0;",
    "bottom:68px;width:360px;height:520px;max-height:80vh;",
    "background:#fff;border-radius:16px;overflow:hidden;",
    "box-shadow:0 12px 48px rgba(0,0,0,.18);",
    "animation:slideUp .2s ease;}",
    "#panel.open{display:flex;}",
    "@keyframes slideUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}",

    /* Header */
    "#header{padding:16px 16px 12px;background:VAR_PRIMARY;color:#fff;}",
    "#header-top{display:flex;align-items:center;justify-content:space-between;}",
    "#header-info{display:flex;align-items:center;gap:10px;}",
    "#avatar{width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,.2);",
    "display:flex;align-items:center;justify-content:center;}",
    "#avatar svg{fill:none;stroke:#fff;stroke-width:2;}",
    "#bot-name{font-size:14px;font-weight:700;}",
    "#status{font-size:11px;opacity:.85;display:flex;align-items:center;gap:4px;margin-top:1px;}",
    "#status-dot{width:7px;height:7px;border-radius:50%;background:#4ade80;}",
    "#status-dot.connecting{background:#fbbf24;}",
    "#close-btn{background:rgba(255,255,255,.2);border:none;cursor:pointer;color:#fff;",
    "width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;}",
    "#close-btn:hover{background:rgba(255,255,255,.3);}",
    "#close-btn svg{fill:none;stroke:#fff;stroke-width:2.5;}",

    /* Messages */
    "#messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px;",
    "background:#f9fafb;}",
    "#messages::-webkit-scrollbar{width:4px;}",
    "#messages::-webkit-scrollbar-track{background:transparent;}",
    "#messages::-webkit-scrollbar-thumb{background:#d1d5db;border-radius:2px;}",

    /* Bubbles */
    ".msg{max-width:80%;display:flex;flex-direction:column;gap:2px;}",
    ".msg.in{align-self:flex-start;}",
    ".msg.out{align-self:flex-end;}",
    ".bubble{padding:10px 14px;border-radius:16px;font-size:13.5px;line-height:1.5;word-break:break-word;}",
    ".msg.in .bubble{background:#fff;border:1px solid #e5e7eb;border-bottom-left-radius:4px;color:#111;}",
    ".msg.out .bubble{background:VAR_PRIMARY;color:#fff;border-bottom-right-radius:4px;}",
    ".ts{font-size:10px;color:#9ca3af;padding:0 4px;}",
    ".msg.out .ts{text-align:right;}",

    /* Typing indicator */
    "#typing{display:none;align-self:flex-start;padding:12px 14px;background:#fff;",
    "border:1px solid #e5e7eb;border-radius:16px;border-bottom-left-radius:4px;gap:4px;}",
    "#typing.show{display:flex;}",
    ".dot{width:7px;height:7px;border-radius:50%;background:#9ca3af;",
    "animation:bounce .9s infinite ease-in-out;}",
    ".dot:nth-child(2){animation-delay:.15s;}",
    ".dot:nth-child(3){animation-delay:.3s;}",
    "@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}",

    /* Input row */
    "#footer{padding:12px;border-top:1px solid #e5e7eb;display:flex;gap:8px;background:#fff;}",
    "#input{flex:1;padding:10px 14px;border:1.5px solid #e5e7eb;border-radius:12px;",
    "font-size:13.5px;outline:none;resize:none;font-family:inherit;line-height:1.4;",
    "max-height:120px;overflow-y:auto;transition:border-color .15s;}",
    "#input:focus{border-color:VAR_PRIMARY;}",
    "#send{width:40px;height:40px;border-radius:12px;background:VAR_PRIMARY;border:none;",
    "cursor:pointer;display:flex;align-items:center;justify-content:center;",
    "transition:opacity .15s;flex-shrink:0;}",
    "#send:hover{opacity:.88;}",
    "#send:disabled{opacity:.4;cursor:not-allowed;}",
    "#send svg{fill:none;stroke:#fff;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;}",

    /* Powered by */
    "#powered{text-align:center;padding:4px 0 8px;font-size:10px;color:#9ca3af;background:#fff;}",
    "#powered a{color:inherit;text-decoration:none;}",
    "#powered a:hover{color:#6b7280;}",
  ].join("").replaceAll("VAR_PRIMARY", PRIMARY);

  shadow.appendChild(style);

  // ── HTML ───────────────────────────────────────────────────────────────────
  var container = document.createElement("div");
  container.innerHTML = [
    /* Bubble */
    '<div id="bubble" role="button" aria-label="Open chat" tabindex="0">',
      '<svg width="26" height="26" viewBox="0 0 24 24">',
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
      '</svg>',
      '<span id="badge"></span>',
    '</div>',

    /* Panel */
    '<div id="panel" role="dialog" aria-label="Chat window">',
      /* Header */
      '<div id="header">',
        '<div id="header-top">',
          '<div id="header-info">',
            '<div id="avatar">',
              '<svg width="20" height="20" viewBox="0 0 24 24">',
                '<circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>',
              '</svg>',
            '</div>',
            '<div>',
              '<div id="bot-name"></div>',
              '<div id="status"><span id="status-dot" class="connecting"></span><span id="status-text">Connecting…</span></div>',
            '</div>',
          '</div>',
          '<button id="close-btn" aria-label="Close chat">',
            '<svg width="14" height="14" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
          '</button>',
        '</div>',
      '</div>',

      /* Messages */
      '<div id="messages"></div>',

      /* Footer */
      '<div id="footer">',
        '<textarea id="input" rows="1" placeholder="Type a message…" aria-label="Message"></textarea>',
        '<button id="send" disabled aria-label="Send">',
          '<svg width="18" height="18" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
        '</button>',
      '</div>',
      '<div id="powered"><a href="https://wow.gpayauto.org" target="_blank" rel="noopener">Powered by Wow Chat</a></div>',
    '</div>',
  ].join("");

  shadow.appendChild(container);

  // ── Element refs ───────────────────────────────────────────────────────────
  var $bubble   = shadow.getElementById("bubble");
  var $badge    = shadow.getElementById("badge");
  var $panel    = shadow.getElementById("panel");
  var $botName  = shadow.getElementById("bot-name");
  var $statusDot= shadow.getElementById("status-dot");
  var $statusTxt= shadow.getElementById("status-text");
  var $messages = shadow.getElementById("messages");
  var $input    = shadow.getElementById("input");
  var $send     = shadow.getElementById("send");
  var unreadCount = 0;

  // ── Session init ───────────────────────────────────────────────────────────
  function initSession() {
    var body = { widget_key: WIDGET_KEY };
    if (storedSession) body.session_id = storedSession.id;

    fetch(API_BASE + "/api/v1/webchat/session/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.error) { console.error("[WowChat]", data.error); return; }
      sessionId = data.session_id;
      botName   = data.bot_name   || BOT_NAME;
      welcomeMsg= data.welcome_message;

      try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ id: sessionId, ts: Date.now() })); }
      catch(_) {}

      $botName.textContent = botName;
      connectWS();

      if (!data.resumed && welcomeMsg) {
        setTimeout(function() {
          appendMessage("in", welcomeMsg);
        }, 600);
      }
    })
    .catch(function(e) {
      console.error("[WowChat] Session init failed:", e);
      setStatus("offline");
    });
  }

  // ── WebSocket ──────────────────────────────────────────────────────────────
  function connectWS() {
    if (!sessionId) return;
    if (ws) { try { ws.close(); } catch(_) {} }

    setStatus("connecting");
    var url = WS_BASE + "/ws/webchat/" + sessionId + "/";
    ws = new WebSocket(url);

    ws.onopen = function() {
      wsReady = true;
      reconnectDelay = 1000;
      setStatus("online");
      $send.disabled = false;

      // Flush queued messages
      while (messageQueue.length) {
        ws.send(JSON.stringify(messageQueue.shift()));
      }
    };

    ws.onmessage = function(evt) {
      var data;
      try { data = JSON.parse(evt.data); } catch(_) { return; }
      if (data.type === "pong") return;
      if (data.type === "message" && data.direction === "outbound") {
        removeTypingIndicator();
        appendMessage("in", data.content);
        if (!isOpen) {
          unreadCount++;
          showBadge();
        }
      }
    };

    ws.onclose = function(evt) {
      wsReady = false;
      $send.disabled = true;
      if (evt.code === 4004) {
        setStatus("offline");
        return; // invalid session — don't reconnect
      }
      setStatus("reconnecting");
      reconnectTimer = setTimeout(function() {
        reconnectDelay = Math.min(reconnectDelay * 1.5, 15000);
        connectWS();
      }, reconnectDelay);
    };

    ws.onerror = function() {
      setStatus("error");
    };
  }

  // Keep-alive ping every 25 s
  setInterval(function() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "ping" }));
    }
  }, 25000);

  // ── Status helpers ─────────────────────────────────────────────────────────
  function setStatus(state) {
    var labels = {
      connecting:   ["connecting", "Connecting…"],
      online:       ["",          "Online"],
      reconnecting: ["connecting","Reconnecting…"],
      offline:      ["connecting","Offline"],
      error:        ["connecting","Error"],
    };
    var s = labels[state] || labels.offline;
    $statusDot.className = s[0] ? "connecting" : "";
    $statusTxt.textContent = s[1];
  }

  // ── Message rendering ──────────────────────────────────────────────────────
  function appendMessage(dir, text) {
    // Remove typing indicator before adding bot reply
    var typing = shadow.getElementById("typing");
    if (typing) typing.remove();

    var wrapper = document.createElement("div");
    wrapper.className = "msg " + dir;

    var bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    var ts = document.createElement("div");
    ts.className = "ts";
    ts.textContent = formatTime(new Date());

    wrapper.appendChild(bubble);
    wrapper.appendChild(ts);
    $messages.appendChild(wrapper);
    scrollToBottom();
  }

  function showTypingIndicator() {
    if (shadow.getElementById("typing")) return;
    var el = document.createElement("div");
    el.id = "typing";
    el.className = "typing show";
    el.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
    $messages.appendChild(el);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    var el = shadow.getElementById("typing");
    if (el) el.remove();
  }

  function scrollToBottom() {
    requestAnimationFrame(function() {
      $messages.scrollTop = $messages.scrollHeight;
    });
  }

  function formatTime(d) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // ── Badge ──────────────────────────────────────────────────────────────────
  function showBadge() {
    $badge.style.display = "flex";
    $badge.textContent = unreadCount > 9 ? "9+" : String(unreadCount);
  }

  function clearBadge() {
    unreadCount = 0;
    $badge.style.display = "none";
  }

  // ── Open / close ───────────────────────────────────────────────────────────
  function openPanel() {
    isOpen = true;
    $panel.classList.add("open");
    clearBadge();
    $bubble.setAttribute("aria-label", "Close chat");
    scrollToBottom();
    setTimeout(function() { $input.focus(); }, 50);
  }

  function closePanel() {
    isOpen = false;
    $panel.classList.remove("open");
    $bubble.setAttribute("aria-label", "Open chat");
  }

  $bubble.addEventListener("click", function() { isOpen ? closePanel() : openPanel(); });
  $bubble.addEventListener("keydown", function(e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); isOpen ? closePanel() : openPanel(); } });
  shadow.getElementById("close-btn").addEventListener("click", closePanel);

  // ── Send ───────────────────────────────────────────────────────────────────
  function sendMessage() {
    var text = $input.value.trim();
    if (!text) return;

    appendMessage("out", text);
    $input.value = "";
    $input.style.height = "auto";
    showTypingIndicator();

    var payload = { type: "message", content: text, sender_name: "You" };
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    } else {
      messageQueue.push(payload);
    }
  }

  $send.addEventListener("click", sendMessage);

  $input.addEventListener("keydown", function(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea
  $input.addEventListener("input", function() {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 120) + "px";
  });

  // ── Boot ───────────────────────────────────────────────────────────────────
  $botName.textContent = botName;
  setStatus("connecting");
  initSession();

})();
