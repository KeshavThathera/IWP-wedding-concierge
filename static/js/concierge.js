(() => {
  const root = document.getElementById("concierge-widget");
  if (!root) return;

  const $ = (sel) => root.querySelector(sel);
  const overlay = $("[data-chat-overlay]");
  const launcher = $("[data-chat-open]");
  const unread = $("[data-unread]");
  const log = $("[data-chat-log]");
  const form = $("[data-chat-form]");
  const input = $("[data-chat-input]");
  const send = $("[data-chat-send]");
  const restart = $("[data-chat-restart]");
  const header = { avatar: $("[data-chat-avatar]"), title: $("[data-chat-title]"), status: $("[data-chat-status]"), dot: $("[data-chat-dot]"), route: $("[data-chat-route]") };
  const defaultAvatar = header.avatar.innerHTML;
  const defaultAvatarClass = header.avatar.className;
  let departmentLabel = $("[data-chat-department]");

  const tpl = (name) => root.querySelector(`template[data-tpl="${name}"]`).content.firstElementChild.cloneNode(true);
  const csrf = () => document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] ?? "";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const isOpen = () => !overlay.classList.contains("hidden");
  const initials = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

  let state = null;     // last full payload from the server
  let shown = 0;        // messages rendered from state.messages (before handoff)
  let seen = new Set(); // database ids already rendered (live chat)
  let live = null;      // { status, agent, agentTyping, cursor } once handed off
  let busy = false;
  let unreadCount = 0;
  let agentTypingEl = null;
  let pollTimer = null;

  const scrollDown = () => log.scrollTo({ top: log.scrollHeight, behavior: "smooth" });

  function renderMessage(m) {
    if (m.id) seen.add(m.id);
    let el;
    if (m.role === "agent") {
      el = tpl("agent");
      el.querySelector("[data-author]").textContent = m.author || "Planner";
      el.querySelector("[data-initials]").textContent = initials(m.author || "Planner");
    } else if (m.role === "system") {
      el = tpl("system");
    } else {
      el = tpl(m.role === "visitor" ? "visitor" : "assistant");
      if (m.ai) el.querySelector("[data-ai]")?.classList.replace("hidden", "flex");
    }
    el.querySelector("[data-text]").textContent = m.text;
    if (agentTypingEl?.isConnected) agentTypingEl.before(el);
    else log.append(el);
    return el;
  }

  function setDepartment(name) {
    if (departmentLabel.textContent === name) return;
    const clone = departmentLabel.cloneNode(false); // restart the fade-in animation
    clone.textContent = name;
    departmentLabel.replaceWith(clone);
    departmentLabel = clone;
  }

  function renderQuickActions(actions) {
    if (!actions?.length) return;
    const wrap = tpl("quick-actions");
    wrap.dataset.quickActions = "";
    actions.forEach((label) => {
      const btn = tpl("quick-action");
      btn.textContent = label;
      btn.addEventListener("click", () => submit(label));
      wrap.append(btn);
    });
    log.append(wrap);
  }

  function renderHandoff(handoff) {
    const card = tpl("handoff");
    card.querySelector("[data-ticket]").textContent = handoff.ticket;
    card.querySelector("[data-department]").textContent = handoff.department;
    card.querySelector("[data-inbox]").href = handoff.inboxUrl;
    log.append(card);
  }

  function setFinished(finished) {
    form.classList.toggle("hidden", finished);
    form.classList.toggle("flex", !finished);
    restart.classList.toggle("hidden", !finished);
  }

  function applyLive(next) {
    live = next;
    header.avatar.className = defaultAvatarClass;
    if (!live) {
      header.avatar.innerHTML = defaultAvatar;
      header.title.textContent = "The Concierge";
      header.status.textContent = "Online · English, हिन्दी, Hinglish";
      header.dot.className = "h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400";
      header.route.textContent = "Routing to";
      setFinished(Boolean(state?.ticket));
      return;
    }
    if (live.agent) {
      header.avatar.textContent = live.agent.initials;
      header.avatar.className = defaultAvatarClass.replace("border-champagne/40", "border-transparent bg-burgundy text-paper");
      header.title.textContent = live.agent.name;
    } else {
      header.avatar.innerHTML = defaultAvatar;
      header.title.textContent = "The Concierge";
    }
    const view = {
      waiting: ["Waiting for a planner to join…", "bg-gold animate-pulse", "Connecting to"],
      connected: [`Online now · ${state?.department || "our team"}`, "bg-emerald-400", "Connected to"],
      closed: ["This conversation is closed", "bg-paper/30", "Closed by"],
    }[live.status];
    header.status.textContent = view[0];
    header.dot.className = `h-1.5 w-1.5 shrink-0 rounded-full ${view[1]}`;
    header.route.textContent = view[2];
    setFinished(live.status === "closed");
    showAgentTyping(live.agentTyping && live.status === "connected");
  }

  function showAgentTyping(on) {
    if (on && !agentTypingEl?.isConnected) {
      agentTypingEl = tpl("agent-typing");
      agentTypingEl.querySelector("[data-initials]").textContent = live?.agent?.initials || "";
      log.append(agentTypingEl);
      scrollDown();
    } else if (!on && agentTypingEl?.isConnected) {
      agentTypingEl.remove();
    }
  }

  function setUnread(n) {
    unreadCount = n;
    unread.textContent = n;
    unread.classList.toggle("hidden", n === 0);
    unread.classList.toggle("grid", n > 0);
  }

  function renderAll(data) {
    log.replaceChildren();
    agentTypingEl = null;
    seen = new Set();
    state = data;
    data.messages.forEach(renderMessage);
    shown = data.messages.length;
    renderQuickActions(data.quickActions);
    setDepartment(data.department);
    applyLive(data.live);
    if (data.live) schedulePoll(0);
    scrollDown();
  }

  async function api(url, body) {
    const res = await fetch(url, {
      method: body === undefined ? "GET" : "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    return data;
  }

  // poll faster while the chat is open
  function schedulePoll(delay) {
    clearTimeout(pollTimer);
    if (!live || live.status === "closed") return;
    pollTimer = setTimeout(poll, delay ?? (isOpen() ? 1000 : 5000));
  }

  async function poll() {
    if (document.hidden || busy || !live) return schedulePoll();
    try {
      const data = await api(`${root.dataset.liveUrl}?after=${live.cursor}`);
      const fresh = data.new.filter((m) => !seen.has(m.id));
      fresh.forEach(renderMessage);
      if (fresh.length) {
        scrollDown();
        if (!isOpen()) setUnread(unreadCount + fresh.filter((m) => m.role !== "visitor").length);
      }
      applyLive(data.live);
    } catch {
      /* transient network error: try again next tick */
    }
    schedulePoll();
  }

  const isReload = performance.getEntriesByType("navigation")[0]?.type === "reload";
  let initialStateRequest;

  function initialState() {
    initialStateRequest ??= isReload
      ? api(root.dataset.resetUrl, {})
      : api(root.dataset.stateUrl);
    return initialStateRequest;
  }

  async function load() {
    if (state) return;
    renderAll(await initialState());
  }

  async function sendLive(text) {
    const data = await api(root.dataset.messageUrl, { text });
    data.new.filter((m) => !seen.has(m.id)).forEach(renderMessage);
    applyLive(data.live);
  }

  async function sendToConcierge(text) {
    log.querySelector("[data-quick-actions]")?.remove();
    renderMessage({ role: "visitor", text });
    shown += 1;
    const typing = tpl("typing");
    log.append(typing);
    scrollDown();
    const started = Date.now();
    try {
      const data = await api(root.dataset.messageUrl, { text });
      const fresh = data.messages.slice(shown);
      const pause = 650 + Math.min(fresh[0]?.text.length ?? 80, 160) * 4;
      await sleep(Math.max(0, pause - (Date.now() - started)));
      typing.remove();
      state = data;
      data.messages.slice(0, shown).forEach((m) => m.id && seen.add(m.id)); // ids assigned at handoff
      fresh.forEach(renderMessage);
      shown = data.messages.length;
      renderQuickActions(data.quickActions); // e.g. "which team do you need?" choices
      setDepartment(data.department);
      if (data.handoff) renderHandoff(data.handoff);
      if (data.live) {
        applyLive(data.live);
        schedulePoll();
      }
    } catch (err) {
      typing.remove();
      renderMessage({ role: "assistant", text: err.message });
    }
  }

  async function submit(raw) {
    const text = raw.trim();
    if (!text || busy || live?.status === "closed") return;
    busy = true;
    input.value = "";
    send.disabled = true;
    try {
      await (live ? sendLive(text) : sendToConcierge(text));
    } catch (err) {
      renderMessage({ role: "system", text: err.message });
    } finally {
      busy = false;
      scrollDown();
    }
  }

  async function open(prompt) {
    overlay.classList.replace("hidden", "flex");
    launcher.dataset.hidden = "true";
    setUnread(0);
    await load();
    schedulePoll(0);
    input.focus();
    if (prompt && !live) {
      await sleep(250);
      submit(prompt);
    }
  }

  function close() {
    overlay.classList.replace("flex", "hidden");
    launcher.dataset.hidden = "false";
    schedulePoll();
  }

  let lastTypingPing = 0;
  input.addEventListener("input", () => {
    send.disabled = !input.value.trim() || busy;
    if (live && live.status !== "closed" && input.value.trim() && Date.now() - lastTypingPing > 2500) {
      lastTypingPing = Date.now();
      fetch(root.dataset.typingUrl, { method: "POST", headers: { "X-CSRFToken": csrf() }, credentials: "same-origin" }).catch(() => {});
    }
  });

  launcher.addEventListener("click", () => open());
  $("[data-chat-close]").addEventListener("click", close);
  overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) close(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && isOpen()) close(); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) schedulePoll(0); });
  form.addEventListener("submit", (e) => { e.preventDefault(); submit(input.value); });
  restart.addEventListener("click", async () => {
    clearTimeout(pollTimer);
    renderAll(await api(root.dataset.resetUrl, {}));
    input.focus();
  });

  // [data-ask] buttons open the chat
  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-ask]");
    if (!trigger) return;
    e.preventDefault();
    open(trigger.dataset.ask || undefined);
  });

  if (new URLSearchParams(window.location.search).get("chat") === "open") open();

  initialState().then((data) => { if (data.live && !state) renderAll(data); }).catch(() => {});
})();
