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
const ready = document.querySelector("#ready");
const download = document.querySelector("#download");

let tokensLeft = cfg.free ?? 3;
let localUrl = "";
let polling = false;

const note = (text, warn = false) => {
  if (!say) return;
  say.hidden = !text;
  say.textContent = text || "";
  say.classList.toggle("warn", warn);
};

const paintTokens = () => {
  if (!tokens) return;
  if (tokensLeft > 0) {
    tokens.textContent = tokensLeft === 1
      ? "1 upscale left on this device."
      : `${tokensLeft} upscales left on this device. The first ${cfg.free} are free.`;
  } else {
    tokens.textContent = `Free tries used. ₹${cfg.price} adds ${cfg.pack} more upscales.`;
  }
  if (go && !polling) go.textContent = tokensLeft > 0 ? "Unblur this photo" : `Pay ₹${cfg.price} for ${cfg.pack} upscales`;
};

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
  after.removeAttribute("src");
  compare.hidden = false;
  ready.hidden = true;
  dropLabel.textContent = file.name;
}

async function poll(id) {
  polling = true;
  go.disabled = true;
  for (let i = 0; i < 90; i += 1) {
    const job = await read(`/api/jobs/${id}`);
    note(job.message || "Making the photo sharp…");
    if (job.status === "ready" && job.image_url) {
      if (job.original_url) before.src = job.original_url;
      after.src = job.image_url + "?t=" + Date.now();
      download.href = job.image_url;
      ready.hidden = false;
      compare.hidden = false;
      note("");
      polling = false;
      go.disabled = false;
      paintTokens();
      return;
    }
    if (job.status === "error") {
      note(job.message || "The upscale failed. The token was returned.", true);
      polling = false;
      go.disabled = false;
      paintTokens();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
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
    theme: { color: "#171910" },
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
  note(tokensLeft > 0 ? "Uploading your photo…" : "Your free tries are used. Opening payment…");
  try {
    const body = new FormData();
    body.append("image", file);
    const response = await fetch("/api/upscale", { method: "POST", body });
    const data = await response.json().catch(() => ({}));
    if (typeof data.tokens_left === "number") tokensLeft = data.tokens_left;
    paintTokens();
    if (response.status === 402 || data.need_payment) {
      go.disabled = false;
      await pay(data.id);
      return;
    }
    if (!response.ok) throw new Error(data.detail || "The photo could not be uploaded.");
    if (data.id) await poll(data.id);
  } catch (err) {
    note(err.message, true);
    go.disabled = false;
  }
});

refreshTokens();
