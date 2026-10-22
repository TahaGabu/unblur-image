(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(pointer: fine)").matches;

  $$(".split").forEach((el) => {
    let delay = 0.12;
    const walk = (node) => {
      Array.from(node.childNodes).forEach((child) => {
        if (child.nodeType === Node.TEXT_NODE) {
          const frag = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach((part) => {
            if (!part) return;
            if (/^\s+$/.test(part)) {
              frag.appendChild(document.createTextNode(part));
              return;
            }
            const word = document.createElement("span");
            word.className = "w";
            const inner = document.createElement("span");
            inner.textContent = part;
            inner.style.setProperty("--d", `${delay.toFixed(2)}s`);
            delay += 0.07;
            word.appendChild(inner);
            frag.appendChild(word);
          });
          node.replaceChild(frag, child);
        } else if (child.nodeType === Node.ELEMENT_NODE && child.tagName !== "BR") {
          walk(child);
        }
      });
    };
    walk(el);
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add("in")));
  });

  const countUp = (el) => {
    const target = Number(el.dataset.count || 0);
    if (reduced || Number.isNaN(target)) {
      el.textContent = String(target || el.textContent);
      return;
    }
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / 1200);
      el.textContent = String(Math.round(target * (1 - Math.pow(1 - t, 4))));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  const reveal = (el) => {
    el.classList.add("in");
    $$("[data-count]", el).forEach(countUp);
  };

  if (reduced) {
    $$("[data-reveal]").forEach(reveal);
  } else {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          reveal(entry.target);
          io.unobserve(entry.target);
        });
      },
      { threshold: 0.16, rootMargin: "0px 0px -40px 0px" }
    );
    $$("[data-reveal]").forEach((el) => io.observe(el));
  }

  const nav = $(".nav");
  const bar = $(".scroll-bar");
  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    if (bar) bar.style.setProperty("--p", max > 0 ? (scrollY / max).toFixed(4) : "0");
    if (nav) nav.classList.toggle("stuck", scrollY > 20);
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  if (finePointer && !reduced) {
    const glow = $(".cursor-glow");
    const stage = $(".hero-stage");
    addEventListener(
      "pointermove",
      (event) => {
        if (glow) {
          glow.style.setProperty("--cx", `${event.clientX}px`);
          glow.style.setProperty("--cy", `${event.clientY}px`);
        }
        if (!stage) return;
        const rect = stage.getBoundingClientRect();
        const x = (event.clientX - (rect.left + rect.width / 2)) / rect.width;
        const y = (event.clientY - (rect.top + rect.height / 2)) / rect.height;
        $$(".shot", stage).forEach((shot) => {
          shot.style.setProperty("--px", `${(x * 18).toFixed(1)}px`);
          shot.style.setProperty("--py", `${(y * 18).toFixed(1)}px`);
          shot.style.setProperty("--ry", `${(-6 + x * 12).toFixed(2)}deg`);
          shot.style.setProperty("--rx", `${(4 - y * 8).toFixed(2)}deg`);
        });
      },
      { passive: true }
    );

    $$(".magnetic").forEach((btn) => {
      btn.addEventListener("pointermove", (event) => {
        const rect = btn.getBoundingClientRect();
        const x = event.clientX - rect.left - rect.width / 2;
        const y = event.clientY - rect.top - rect.height / 2;
        btn.style.transform = `translate(${x * 0.22}px, ${y * 0.32}px)`;
      });
      btn.addEventListener("pointerleave", () => {
        btn.style.transform = "";
      });
    });

    $$(".tilt").forEach((card) => {
      card.addEventListener("pointermove", (event) => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width;
        const y = (event.clientY - rect.top) / rect.height;
        card.style.transform = `perspective(900px) rotateX(${((0.5 - y) * 6).toFixed(2)}deg) rotateY(${((x - 0.5) * 8).toFixed(2)}deg) translateY(-4px)`;
      });
      card.addEventListener("pointerleave", () => {
        card.style.transform = "";
      });
    });
  }
})();
