// Staff workspace enhancements. Every action also works as a plain form post without JS.
(() => {
  // Mobile sidebar
  const sidebar = document.querySelector("[data-sidebar]");
  const scrim = document.querySelector("[data-sidebar-scrim]");
  const setSidebar = (open) => {
    if (!sidebar) return;
    sidebar.dataset.open = String(open);
    scrim?.classList.toggle("hidden", !open);
  };
  document.querySelector("[data-sidebar-open]")?.addEventListener("click", () => setSidebar(true));
  document.querySelector("[data-sidebar-close]")?.addEventListener("click", () => setSidebar(false));
  scrim?.addEventListener("click", () => setSidebar(false));

  // Donut: hovering a slice or legend row highlights it and shows its count in the centre.
  document.querySelectorAll("[data-donut]").forEach((donut) => {
    const value = donut.querySelector("[data-donut-value]");
    const label = donut.querySelector("[data-donut-label]");
    const rows = [...donut.querySelectorAll("li[data-segment]")];
    const arcs = [...donut.querySelectorAll("circle[data-segment]")];
    const focus = (index) => {
      arcs.forEach((arc) => {
        const on = index === null || arc.dataset.segment === index;
        arc.style.opacity = on ? "1" : ".35";
        arc.setAttribute("stroke-width", index !== null && arc.dataset.segment === index ? "22" : "18");
      });
      rows.forEach((row) => { row.dataset.active = String(row.dataset.segment === index); });
      const row = rows.find((r) => r.dataset.segment === index);
      value.textContent = row ? row.dataset.value : value.dataset.default;
      label.textContent = row ? row.dataset.name : label.dataset.default;
    };
    [...rows, ...arcs].forEach((el) => {
      el.addEventListener("mouseenter", () => focus(el.dataset.segment));
      el.addEventListener("mouseleave", () => focus(null));
    });
  });

  // Inbox: keep the newest message in view after load and after each HTMX swap.
  const scrollThread = () => document.querySelectorAll("[data-thread]").forEach((t) => { t.scrollTop = t.scrollHeight; });
  scrollThread();
  document.body.addEventListener("htmx:afterSwap", scrollThread);

  // Inbox reply box: Enter sends, Shift+Enter adds a line.
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" || e.shiftKey || !e.target.matches?.("[data-reply]")) return;
    e.preventDefault();
    if (e.target.value.trim()) e.target.form.requestSubmit();
  });

  // Live thread: poll for new messages and the visitor's typing state. Re-armed after every HTMX swap.
  const csrf = () => document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] ?? "";
  let liveTimer = null;
  const STATUS_DOT = { open: "bg-emerald-500", waiting: "bg-gold", resolved: "bg-charcoal/25" };
  const BUTTON_ON = ["bg-paper", "text-ink", "shadow-card"];
  const BUTTON_OFF = ["text-charcoal/55", "hover:text-ink"];
  // The visitor writing (or a colleague acting) can change the status; keep the open thread in step.
  const syncStatus = (status, label) => {
    const pill = document.querySelector("[data-status-pill]");
    if (!pill || pill.dataset.statusPill === status) return;
    pill.dataset.statusPill = status;
    pill.querySelector("[data-status-label]").textContent = label;
    pill.querySelector("[data-status-dot]").className = `h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`;
    document.querySelectorAll("[data-status-button]").forEach((b) => {
      const on = b.dataset.statusButton === status;
      b.classList.remove(...BUTTON_ON, ...BUTTON_OFF);
      b.classList.add(...(on ? BUTTON_ON : BUTTON_OFF));
    });
  };
  const startLiveThread = () => {
    clearInterval(liveTimer);
    const thread = document.querySelector("[data-thread][data-updates-url]");
    if (!thread) return;
    const typing = document.querySelector("[data-visitor-typing]");
    let inFlight = false;
    liveTimer = setInterval(async () => {
      if (!document.contains(thread)) return clearInterval(liveTimer);
      if (document.hidden || inFlight) return;
      inFlight = true;
      try {
        const res = await fetch(`${thread.dataset.updatesUrl}?after=${thread.dataset.cursor}`, { credentials: "same-origin" });
        if (!res.ok) return;
        const data = await res.json();
        if (data.html) {
          const nearBottom = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 120;
          thread.insertAdjacentHTML("beforeend", data.html);
          if (nearBottom) thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
        }
        thread.dataset.cursor = data.cursor;
        syncStatus(data.status, data.statusLabel);
        typing?.classList.toggle("hidden", !data.visitorTyping);
        typing?.classList.toggle("flex", data.visitorTyping);
      } catch { /* network blip: try again next tick */ } finally {
        inFlight = false;
      }
    }, 1200);
  };
  startLiveThread();
  document.body.addEventListener("htmx:afterSwap", (e) => { if (e.detail.target.id === "inbox-panel") startLiveThread(); });

  // Tell the visitor we're typing (at most every 2.5 s).
  let lastTypingPing = 0;
  document.addEventListener("input", (e) => {
    const box = e.target.closest?.("[data-typing-url]");
    if (!box || !box.value.trim() || Date.now() - lastTypingPing < 2500) return;
    lastTypingPing = Date.now();
    fetch(box.dataset.typingUrl, { method: "POST", headers: { "X-CSRFToken": csrf() }, credentials: "same-origin" }).catch(() => {});
  });

  // Lead pipeline drag-and-drop (delegated, so it survives HTMX swaps of #board).
  let dragged = null;
  document.addEventListener("dragstart", (e) => {
    const card = e.target.closest?.("[data-lead]");
    if (!card) return;
    dragged = card;
    card.dataset.dragging = "true";
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", card.dataset.lead);
  });
  document.addEventListener("dragend", () => {
    if (dragged) dragged.dataset.dragging = "false";
    document.querySelectorAll("[data-stage][data-over]").forEach((c) => delete c.dataset.over);
    dragged = null;
  });
  document.addEventListener("dragover", (e) => {
    const column = e.target.closest?.("[data-stage]");
    if (!column || !dragged) return;
    e.preventDefault();
    document.querySelectorAll("[data-stage][data-over]").forEach((c) => { if (c !== column) delete c.dataset.over; });
    column.dataset.over = "true";
  });
  document.addEventListener("drop", (e) => {
    const column = e.target.closest?.("[data-stage]");
    if (!column || !dragged) return;
    e.preventDefault();
    window.htmx.ajax("POST", dragged.dataset.moveUrl, { target: "#board", swap: "outerHTML", values: { stage: column.dataset.stage } });
  });
})();
