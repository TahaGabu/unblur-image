(() => {
  const cfg = window.UB || {};
  const GA = cfg.ga || "";
  if (!GA) return;

  const track = (name, params) => {
    try {
      if (typeof window.gtag !== "function") return;
      const extra = {
        page_type: cfg.page || "page",
        page_path: location.pathname,
      };
      if (cfg.pageId) extra.page_id = cfg.pageId;
      window.gtag("event", name, Object.assign(extra, params || {}));
    } catch (err) {
      /* analytics must not break the page */
    }
  };
  window.ubTrack = track;

  let clientId = "";
  let sessionId = "";

  const readIds = () => {
    const ga = document.cookie.match(/(?:^|;\s*)_ga=([^;]+)/);
    if (ga) {
      const parts = decodeURIComponent(ga[1]).split(".");
      if (parts.length >= 4) clientId = parts.slice(-2).join(".");
    }
    const suffix = GA.replace(/^G-/, "");
    const gs = document.cookie.match(new RegExp("(?:^|;\\s*)_ga_" + suffix + "=([^;]+)"));
    if (!gs) return;
    const raw = decodeURIComponent(gs[1]);
    const modern = raw.match(/(?:^|[.$])s(\d{5,})/);
    if (modern) {
      sessionId = modern[1];
      return;
    }
    const bits = raw.split(".");
    if (bits[0] === "GS1" && bits[2]) sessionId = bits[2];
  };

  const refreshIds = () => {
    readIds();
    if (typeof window.gtag !== "function") return;
    window.gtag("get", GA, "client_id", (id) => {
      if (id) clientId = String(id);
    });
    window.gtag("get", GA, "session_id", (id) => {
      if (id) sessionId = String(id);
    });
  };

  refreshIds();
  let tries = 0;
  const idTimer = setInterval(() => {
    refreshIds();
    tries += 1;
    if ((clientId && sessionId) || tries > 10) clearInterval(idTimer);
  }, 500);

  const origFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    refreshIds();
    const next = init ? Object.assign({}, init) : {};
    const headers = new Headers(next.headers || {});
    if (clientId) headers.set("X-GA-Client", clientId);
    if (sessionId) headers.set("X-GA-Session", sessionId);
    next.headers = headers;
    return origFetch(input, next);
  };

  const labelOf = (el) => (el.getAttribute("aria-label") || el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 80);
  const safeUrl = (href) => {
    try {
      const url = new URL(href, location.href);
      return url.origin === location.origin ? url.pathname : `${url.origin}${url.pathname}`;
    } catch (err) {
      return "";
    }
  };

  if (cfg.page === "guides") {
    track("view_item_list", { item_list_id: "guides", item_list_name: "Guides" });
  }
  if (cfg.page === "guide" && cfg.pageId) {
    track("tutorial_begin", { tutorial_id: cfg.pageId });
  }
  if (cfg.page === "home" && !cfg.freeMode) {
    track("view_item", {
      currency: "INR",
      value: Number(cfg.price) || 0,
      items: [
        {
          item_id: "upscale_pack",
          item_name: `${cfg.pack} image upscales`,
          price: Number(cfg.price) || 0,
          quantity: 1,
        },
      ],
    });
  }

  try {
    const query = new URLSearchParams(location.search);
    const term = query.get("q") || query.get("s") || query.get("search") || query.get("query") || "";
    if (term) track("search", { search_term: term.slice(0, 80) });
  } catch (err) {
    /* ignore malformed search */
  }

  try {
    const hour = new Date().getTimezoneOffset();
    track("device_context", {
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      dpr: Math.round((window.devicePixelRatio || 1) * 100) / 100,
      lang: (navigator.language || "").slice(0, 20),
      timezone_offset: hour,
      connection: (navigator.connection && navigator.connection.effectiveType) || "",
      device: window.innerWidth < 720 ? "mobile" : window.innerWidth < 1100 ? "tablet" : "desktop",
      reduced_motion: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "yes" : "no",
    });
  } catch (err) {
    /* device details are optional */
  }

  const marks = [25, 50, 75, 90, 100];
  const seenScroll = new Set();
  let tutorialDone = false;
  const onScroll = () => {
    const height = document.documentElement.scrollHeight - window.innerHeight;
    const pct = height <= 0 ? 100 : Math.min(100, Math.round((window.scrollY / height) * 100));
    marks.forEach((mark) => {
      if (pct < mark || seenScroll.has(mark)) return;
      seenScroll.add(mark);
      track("scroll_depth", { percent_scrolled: mark });
    });
    if (!tutorialDone && cfg.page === "guide" && pct >= 90) {
      tutorialDone = true;
      track("tutorial_complete", { tutorial_id: cfg.pageId || location.pathname });
    }
  };
  document.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  [10, 30, 60, 120, 300].forEach((seconds) => {
    window.setTimeout(() => {
      if (document.visibilityState === "visible") track("engaged_time", { engagement_seconds: seconds });
    }, seconds * 1000);
  });

  const started = performance.now();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      track("tab_hidden", { engagement_seconds: Math.round((performance.now() - started) / 1000) });
      flushVitals();
    }
  });
  window.addEventListener("pagehide", () => {
    track("page_leave", { engagement_seconds: Math.round((performance.now() - started) / 1000) });
    flushVitals();
  });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) track("page_restore", { page_path: location.pathname });
  });
  window.addEventListener("offline", () => track("connection_change", { state: "offline" }));
  window.addEventListener("online", () => track("connection_change", { state: "online" }));
  document.addEventListener("copy", () => track("copy_text", { page_path: location.pathname }));

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const el = target ? target.closest("a, button, summary") : null;
    if (!el) return;
    const text = labelOf(el);
    if (el.tagName === "SUMMARY") {
      const details = el.parentElement;
      if (details && details.tagName === "DETAILS" && !details.open) {
        track("faq_open", { question: text });
      }
      return;
    }
    if (el.tagName === "BUTTON") {
      track("cta_click", { cta_id: el.id || "", cta_text: text, link_url: location.pathname });
      return;
    }
    const raw = el.getAttribute("href") || "";
    if (el.id === "download") {
      const path = safeUrl(el.href);
      const ext = (path.split(".").pop() || "").toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 8);
      track("download_result", { file_extension: ext, link_url: path, source: "result" });
      return;
    }
    if (raw.startsWith("mailto:") || raw.startsWith("tel:")) {
      track("contact_click", { method: raw.startsWith("mailto:") ? "email" : "phone" });
      return;
    }
    if (raw.startsWith("#")) {
      track("select_content", { content_type: "anchor", content_id: raw.slice(1, 60) || "top" });
      if (el.matches("a.btn, a.btn-ghost, a.btn-small, a.btn-big")) {
        track("cta_click", { cta_id: el.id || raw.slice(1, 40), cta_text: text, link_url: raw });
      }
      return;
    }
    let outbound = false;
    try {
      outbound = Boolean(raw) && new URL(el.href, location.href).origin !== location.origin;
    } catch (err) {
      outbound = false;
    }
    const path = safeUrl(el.href);
    if (outbound) {
      track("outbound_click", { link_url: path, link_text: text });
      return;
    }
    const isCta = el.matches("a.btn, a.btn-ghost, a.btn-small, a.btn-big");
    if (isCta) track("cta_click", { cta_id: el.id || "", cta_text: text, link_url: path || location.pathname });
    if (path === "/guides" || path.startsWith("/guides/")) {
      track("select_content", { content_type: "guide", content_id: path.slice(0, 80) });
      return;
    }
    if (el.closest("header.nav, .foot")) {
      track("select_content", { content_type: "nav", content_id: (path || text).slice(0, 80) });
      return;
    }
    if (!isCta && path) track("select_content", { content_type: "link", content_id: path.slice(0, 80) });
  });

  document.querySelector("#form")?.addEventListener(
    "focusin",
    () => track("form_start", { form_id: "upscale", form_name: "unblur" }),
    { once: true },
  );
  document.querySelector("#drop")?.addEventListener(
    "dragenter",
    () => track("file_drag", { form_id: "upscale" }),
    { once: true },
  );

  const sections = [
    [".hero", "hero"],
    ["#how", "how"],
    ["#studio", "studio"],
    ["#reviews", "reviews"],
    [".faq", "faq"],
    [".sheet", "article"],
  ];
  if ("IntersectionObserver" in window) {
    const seenSection = new Set();
    const watcher = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting || entry.intersectionRatio < 0.35) return;
          const name = entry.target.getAttribute("data-section");
          if (!name || seenSection.has(name)) return;
          seenSection.add(name);
          track("view_section", { section: name });
          watcher.unobserve(entry.target);
        });
      },
      { threshold: [0.35] },
    );
    sections.forEach(([selector, name]) => {
      document.querySelectorAll(selector).forEach((el) => {
        if (el.getAttribute("data-section")) return;
        el.setAttribute("data-section", name);
        watcher.observe(el);
      });
    });
  }

  const vitals = {};
  let vitalsSent = false;
  const rate = (name, value) => {
    const bounds = { LCP: [2500, 4000], CLS: [0.1, 0.25], INP: [200, 500], FCP: [1800, 3000], TTFB: [800, 1800] };
    const pair = bounds[name];
    if (!pair) return "unknown";
    if (value <= pair[0]) return "good";
    if (value <= pair[1]) return "needs_improvement";
    return "poor";
  };
  const remember = (name, value) => {
    vitals[name] = value;
  };
  const flushVitals = () => {
    if (vitalsSent) return;
    vitalsSent = true;
    Object.keys(vitals).forEach((name) => {
      const value = vitals[name];
      track("web_vitals", {
        metric_name: name,
        metric_value: Math.round(name === "CLS" ? value * 1000 : value),
        metric_rating: rate(name, value),
      });
    });
  };
  try {
    const nav = performance.getEntriesByType("navigation")[0];
    if (nav) remember("TTFB", nav.responseStart);
  } catch (err) {
    /* navigation timing is optional */
  }
  const observe = (type, cb, extra) => {
    try {
      const obs = new PerformanceObserver((list) => cb(list));
      obs.observe(Object.assign({ type, buffered: true }, extra || {}));
    } catch (err) {
      /* this metric is not supported */
    }
  };
  observe("paint", (list) => {
    list.getEntries().forEach((entry) => {
      if (entry.name === "first-contentful-paint") remember("FCP", entry.startTime);
    });
  });
  observe("largest-contentful-paint", (list) => {
    const entries = list.getEntries();
    const last = entries[entries.length - 1];
    if (last) remember("LCP", last.startTime);
  });
  let cls = 0;
  observe("layout-shift", (list) => {
    list.getEntries().forEach((entry) => {
      if (!entry.hadRecentInput) cls += entry.value;
    });
    remember("CLS", cls);
  });
  let inp = 0;
  observe(
    "event",
    (list) => {
      list.getEntries().forEach((entry) => {
        if (entry.duration > inp) inp = entry.duration;
      });
      if (inp) remember("INP", inp);
    },
    { durationThreshold: 40 },
  );
  window.setTimeout(flushVitals, 12000);

  const seenErrors = new Set();
  const reportError = (message) => {
    const description = String(message || "error").replace(/\s+/g, " ").slice(0, 100);
    if (!description || seenErrors.has(description)) return;
    seenErrors.add(description);
    track("exception", { description, fatal: false });
  };
  window.addEventListener("error", (event) => reportError(event.message));
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    reportError(reason && reason.message ? reason.message : reason);
  });
})();
