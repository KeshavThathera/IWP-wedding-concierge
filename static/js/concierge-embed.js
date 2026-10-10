(() => {
  const script = document.currentScript;
  if (!script || document.querySelector("iframe[data-iwp-concierge]")) return;

  const endpoint = new URL(script.dataset.conciergeUrl || "/embed/", script.src);
  const frame = document.createElement("iframe");
  frame.dataset.iwpConcierge = "";
  frame.src = endpoint.href;
  frame.title = "Wedding concierge";
  frame.setAttribute("allow", "clipboard-write");
  Object.assign(frame.style, {
    position: "fixed",
    zIndex: "2147483000",
    right: "0",
    bottom: "0",
    width: "112px",
    height: "112px",
    border: "0",
    background: "transparent",
    colorScheme: "normal",
  });

  const resize = (open) => {
    const mobile = window.matchMedia("(max-width: 639px)").matches;
    if (!open) {
      Object.assign(frame.style, { inset: "auto 0 0 auto", width: "112px", height: "112px" });
    } else if (mobile) {
      Object.assign(frame.style, { inset: "0", width: "100vw", height: "100dvh" });
    } else {
      Object.assign(frame.style, {
        inset: "auto 8px 8px auto",
        width: "480px",
        height: `${Math.min(780, window.innerHeight - 16)}px`,
      });
    }
  };

  let open = false;
  window.addEventListener("message", (event) => {
    if (event.origin !== endpoint.origin || event.source !== frame.contentWindow) return;
    if (event.data?.type === "iwp-concierge:open") open = true;
    if (event.data?.type === "iwp-concierge:close") open = false;
    if (event.data?.type?.startsWith("iwp-concierge:")) resize(open);
  });
  window.addEventListener("resize", () => resize(open));
  document.body.append(frame);
})();
