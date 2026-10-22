const cfg = JSON.parse(document.querySelector("#cfg")?.textContent || "{}");
const form = document.querySelector("#form");
const fileInput = document.querySelector("#file");
const drop = document.querySelector("#drop");
const dropLabel = document.querySelector("#drop-label");
const go = document.querySelector("#go");
const tokens = document.querySelector("#tokens");
const say = document.querySelector("#say");
const compare = document.querySelector("#compare");
const before = document.querySelector("#before");
const after = document.querySelector("#after");
const ghost = document.querySelector("#after-ghost");
const wait = document.querySelector("#wait");
const waitCopy = document.querySelector("#wait-copy");
const progress = document.querySelector("#progress");
const progressLabel = document.querySelector("#progress-label");
const progressPct = document.querySelector("#progress-pct");
const progressBar = document.querySelector("#progress-bar");
const progressTrack = document.querySelector("#progress-track");
const ready = document.querySelector("#ready");
const download = document.querySelector("#download");

let tokensLeft = cfg.free ?? 3;
let localUrl = "";
let polling = false;
let progressTimer = 0;
let progressValue = 0;

const note = (text, warn = false) => {
  if (!say) return;
  say.hidden = !text;
  say.textContent = text || "";
  say.classList.toggle("warn", warn);
  say.classList.remove("shake");
  if (warn && text) {
    void say.offsetWidth;
    say.classList.add("shake");
  }
};

const offer = () => `₹${cfg.price} for ${cfg.pack} more`;

const paintTokens = () => {
  if (!tokens) return;
  const free = cfg.free ?? 3;
  if (tokensLeft >= free) {
    tokens.textContent = `${free} free upscales. ${offer()}.`;
  } else if (tokensLeft > 0) {
    tokens.textContent = `${tokensLeft} of ${free} free upscales left. ${offer()}.`;
  } else {
    tokens.textContent = `Free upscales used. ${offer()}.`;
  }
  if (go && !polling) go.textContent = tokensLeft > 0 ? "Unblur this photo" : `Pay ₹${cfg.price} for ${cfg.pack} upscales`;
};

const setProgress = (value, label) => {
  progressValue = Math.max(0, Math.min(100, value));
  const shown = Math.round(progressValue);
  if (progressBar) progressBar.style.width = `${progressValue}%`;
  if (progressPct) progressPct.textContent = `${shown}%`;
  if (progressTrack) progressTrack.setAttribute("aria-valuenow", String(shown));
  if (label && progressLabel) progressLabel.textContent = label;
};

const stopProgress = () => {
  if (progressTimer) clearInterval(progressTimer);
  progressTimer = 0;
};

const startProgress = () => {
  stopProgress();
  if (wait) wait.hidden = false;
  if (wait) wait.classList.remove("idle");
  if (waitCopy) waitCopy.hidden = true;
  if (progress) progress.hidden = false;
  if (after) after.hidden = true;
  let value = 6;
  setProgress(value, "Uploading your photo");
  progressTimer = setInterval(() => {
    const cap = 92;
    value = Math.min(cap, value + Math.max(0.25, (cap - value) * 0.045));
    const label = value < 22 ? "Uploading your photo" : value < 62 ? "Rebuilding the detail" : "Finishing the sharp photo";
    setProgress(value, label);
  }, 220);
};

const finishProgress = () => new Promise((resolve) => {
  stopProgress();
  setProgress(100, "Sharp photo ready");
  setTimeout(resolve, 420);
});

async function read(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok && response.status !== 402) {
    throw new Error(data.detail || "Something went wrong.");
  }
  if (typeof data.tokens_left === "number") tokensLeft = data.tokens_left;
  return data;
}

async function refreshTokens() {
  try {
    const data = await read("/api/tokens");
    tokensLeft = Number(data.tokens_left ?? tokensLeft);
  } catch {
    /* keep the last known count */
  }
  paintTokens();
}

function showOriginal(file) {
  if (localUrl) URL.revokeObjectURL(localUrl);
  localUrl = URL.createObjectURL(file);
  before.src = localUrl;
  if (ghost) {
    ghost.src = localUrl;
    ghost.hidden = false;
  }
  if (after) {
    after.removeAttribute("src");
    after.hidden = true;
  }
  if (wait) {
    wait.hidden = false;
    wait.classList.add("idle");
  }
  if (waitCopy) {
    waitCopy.hidden = false;
    waitCopy.textContent = "The sharp photo will show here.";
  }
  if (progress) progress.hidden = true;
  stopProgress();
  setProgress(0, "Making the photo sharp");
  compare.hidden = false;
  compare.classList.add("in");
  compare.classList.remove("working", "done");
  ready.hidden = true;
  dropLabel.textContent = file.name;
}

async function poll(id) {
  polling = true;
  go.disabled = true;
  compare?.classList.add("working");
  compare?.classList.remove("done");
  if (!progressTimer) startProgress();
  note("");
  for (let i = 0; i < 400; i += 1) {
    const job = await read(`/api/jobs/${id}`);
    if (job.status === "ready" && job.image_url) {
      await finishProgress();
      if (job.original_url) before.src = job.original_url;
      after.src = `${job.image_url}?t=${Date.now()}`;
      after.hidden = false;
      if (ghost) ghost.hidden = true;
      if (wait) wait.hidden = true;
      download.href = job.image_url;
      ready.hidden = false;
      compare.hidden = false;
      compare.classList.remove("working");
      compare.classList.add("in", "done");
      note("");
      polling = false;
      go.disabled = false;
      paintTokens();
      return;
    }
    if (job.status === "error") {
      stopProgress();
      if (progress) progress.hidden = true;
      if (wait) wait.classList.add("idle");
      if (waitCopy) {
        waitCopy.hidden = false;
        waitCopy.textContent = "The sharp photo will show here.";
      }
      note(job.message || "The upscale failed. The token was returned.", true);
      compare?.classList.remove("working");
      polling = false;
      go.disabled = false;
      paintTokens();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  stopProgress();
  note("This is taking longer than usual. Keep the page open and check again.", true);
  polling = false;
  go.disabled = false;
}

async function pay(jobId) {
  if (!cfg.paymentsReady) {
    note("Payments are not switched on yet.", true);
    return;
  }
  if (typeof window.Razorpay !== "function") {
    note("Checkout is still loading. Try again in a moment.", true);
    return;
  }
  note("Opening secure checkout…");
  const order = await read("/api/order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId }),
  });
  const checkout = new window.Razorpay({
    key: order.key_id || cfg.keyId,
    amount: order.amount,
    currency: "INR",
    name: "Unblur",
    description: `${cfg.pack} image upscales`,
    order_id: order.id,
    theme: { color: "#ff6a3d" },
    handler: async (response) => {
      try {
        const job = await read("/api/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(response),
        });
        paintTokens();
        if (job.id) poll(job.id);
        else note(job.message || "Upscales added.");
      } catch (err) {
        note(err.message, true);
      }
    },
    modal: { ondismiss: () => note("Checkout closed. You have not been charged.") },
  });
  checkout.on("payment.failed", (resp) => {
    note(resp.error?.description || "Payment failed. You have not been charged.", true);
  });
  checkout.open();
}

fileInput?.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) showOriginal(file);
});
["dragover", "dragleave", "drop"].forEach((name) => {
  drop?.addEventListener(name, (event) => {
    event.preventDefault();
    drop.classList.toggle("hot", name === "dragover");
    if (name === "drop" && event.dataTransfer?.files?.[0]) {
      fileInput.files = event.dataTransfer.files;
      showOriginal(event.dataTransfer.files[0]);
    }
  });
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput?.files?.[0];
  if (!file) {
    note("Choose a photo first.", true);
    return;
  }
  if (!cfg.renderReady) {
    note("Upscales are paused right now.", true);
    return;
  }
  go.disabled = true;
  if (tokensLeft > 0) startProgress();
  else note("Your free tries are used. Opening payment…");
  try {
    const body = new FormData();
    body.append("image", file);
    const response = await fetch("/api/upscale", { method: "POST", body });
    const data = await response.json().catch(() => ({}));
    if (typeof data.tokens_left === "number") tokensLeft = data.tokens_left;
    paintTokens();
    if (response.status === 402 || data.need_payment) {
      stopProgress();
      if (progress) progress.hidden = true;
      if (waitCopy) waitCopy.hidden = false;
      go.disabled = false;
      await pay(data.id);
      return;
    }
    if (!response.ok) throw new Error(data.detail || "The photo could not be uploaded.");
    if (data.id) await poll(data.id);
  } catch (err) {
    stopProgress();
    if (progress) progress.hidden = true;
    if (wait) wait.classList.add("idle");
    if (waitCopy) waitCopy.hidden = false;
    note(err.message, true);
    go.disabled = false;
  }
});

refreshTokens();
