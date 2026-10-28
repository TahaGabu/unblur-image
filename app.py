from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

import razorpay
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from policies import pages
from seo import faqs, guide_map, guides, guides_index_seo, guide_seo, home_seo, policy_seo, robots, sitemap
from upscaler import upscale

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
INBOX = DATA / "inbox"
OUT = DATA / "out"
ORDERS = DATA / "orders.json"
TOKENS = DATA / "tokens.json"
VISITOR_COOKIE = "unblur_vid"
MAX_BYTES = 8_000_000
for folder in (DATA, INBOX, OUT):
    folder.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Unblur")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


def _media_type(path: Path) -> str:
    header = path.read_bytes()[:16]
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


@app.get("/media/{name}")
def media_file(name: str):
    path = (OUT / name).resolve()
    if path.parent != OUT.resolve() or not path.is_file():
        raise HTTPException(404, "Photo not found.")
    return FileResponse(path, media_type=_media_type(path))
templates = Jinja2Templates(directory=str(ROOT / "templates"))
lock = threading.Lock()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def is_free() -> bool:
    return os.environ.get("FREE_MODE", "1").strip().lower() not in {"0", "false", "no"}


def price_rupees() -> int:
    return 0 if is_free() else max(1, _int_env("PRICE_RUPEES", 20))


def free_tokens() -> int:
    return max(0, _int_env("FREE_TOKENS", 3))


def pack_tokens() -> int:
    return max(1, _int_env("PACK_TOKENS", 3))


def scale_factor() -> int:
    return 2 if _int_env("SCALE_FACTOR", 2) not in (2, 4) else _int_env("SCALE_FACTOR", 2)


def razorpay_keys() -> tuple[str, str]:
    return (
        os.environ.get("RAZORPAY_KEY_ID", "").strip(),
        os.environ.get("RAZORPAY_KEY_SECRET", "").strip(),
    )


def payments_ready() -> bool:
    key_id, secret = razorpay_keys()
    return bool(key_id and secret)


def render_ready() -> bool:
    return bool(os.environ.get("REPLICATE_API_TOKEN", "").strip())


def page_context() -> dict:
    key_id, _secret = razorpay_keys()
    price = price_rupees()
    free = free_tokens()
    pack = pack_tokens()
    return {
        "price": price,
        "free_tokens": free,
        "pack_tokens": pack,
        "scale": scale_factor(),
        "payments_ready": payments_ready(),
        "test_mode": key_id.startswith("rzp_test_"),
        "key_id": key_id,
        "render_ready": render_ready(),
        "faqs": faqs(price, free, pack),
        "guides": guides(price, free, pack),
        "seo": home_seo(price, free, pack),
        "config_json": json.dumps(
            {
                "price": price,
                "free": free,
                "pack": pack,
                "freeMode": is_free(),
                "paymentsReady": payments_ready() and not is_free(),
                "keyId": key_id,
                "renderReady": render_ready(),
            }
        ),
    }


def client() -> razorpay.Client:
    key_id, secret = razorpay_keys()
    if not key_id or not secret:
        raise HTTPException(400, "Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env, then restart.")
    return razorpay.Client(auth=(key_id, secret))


def load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback
    return data if isinstance(data, dict) else fallback


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_orders() -> dict:
    return load_json(ORDERS, {})


def save_orders(orders: dict) -> None:
    save_json(ORDERS, orders)


def load_tokens() -> dict:
    data = load_json(TOKENS, {"visitors": {}, "ips": {}})
    data.setdefault("visitors", {})
    data.setdefault("ips", {})
    return data


def save_tokens(data: dict) -> None:
    save_json(TOKENS, data)


def _visitor_row(data: dict, visitor_id: str) -> dict:
    row = data["visitors"].get(visitor_id) or {"free_used": 0, "paid": 0}
    row["free_used"] = int(row.get("free_used") or 0)
    row["paid"] = int(row.get("paid") or 0)
    return row


def tokens_left(visitor_id: str) -> int:
    row = _visitor_row(load_tokens(), visitor_id)
    return max(0, free_tokens() - row["free_used"]) + row["paid"]


def _ip_cap() -> int:
    default = 40 if is_free() else (free_tokens() or 3)
    return max(1, _int_env("FREE_IP_LIMIT", default))


def spend_token(visitor_id: str, ip: str) -> tuple[str, str]:
    """Spend one token. Returns (bucket, error). bucket is free or paid."""
    with lock:
        data = load_tokens()
        row = _visitor_row(data, visitor_id)
        if is_free() or row["free_used"] < free_tokens():
            today = datetime.now().date().isoformat()
            ip_row = data["ips"].get(ip) or {}
            if int(ip_row.get(today) or 0) >= _ip_cap():
                if is_free():
                    return "", "This connection has used today's free photos. Come back tomorrow."
                return "", "Free upscales are paused for today on this connection. You can still pay ₹%s for %s more." % (
                    price_rupees(),
                    pack_tokens(),
                )
            row["free_used"] += 1
            ip_row[today] = int(ip_row.get(today) or 0) + 1
            data["ips"][ip] = ip_row
            data["visitors"][visitor_id] = row
            save_tokens(data)
            return "free", ""
        if row["paid"] > 0:
            row["paid"] -= 1
            data["visitors"][visitor_id] = row
            save_tokens(data)
            return "paid", ""
        return "", f"Your free {free_tokens()} upscales are used. ₹{price_rupees()} adds {pack_tokens()} more."


def refund_token(visitor_id: str, ip: str, bucket: str) -> None:
    if bucket not in ("free", "paid"):
        return
    with lock:
        data = load_tokens()
        row = _visitor_row(data, visitor_id)
        if bucket == "free":
            row["free_used"] = max(0, row["free_used"] - 1)
            today = datetime.now().date().isoformat()
            ip_row = data["ips"].get(ip) or {}
            if today in ip_row:
                ip_row[today] = max(0, int(ip_row[today]) - 1)
                data["ips"][ip] = ip_row
        else:
            row["paid"] += 1
        data["visitors"][visitor_id] = row
        save_tokens(data)


def add_paid_tokens(visitor_id: str, count: int) -> None:
    with lock:
        data = load_tokens()
        row = _visitor_row(data, visitor_id)
        row["paid"] += count
        data["visitors"][visitor_id] = row
        save_tokens(data)


def update_order(order_id: str, **fields) -> dict:
    with lock:
        orders = load_orders()
        row = orders.get(order_id, {})
        row.update(fields)
        orders[order_id] = row
        save_orders(orders)
        return row


def public_job(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "status": row.get("status"),
        "message": row.get("message"),
        "image_url": row.get("image_url"),
        "original_url": row.get("original_url"),
        "tokens_left": tokens_left(row.get("visitor_id") or "") if row.get("visitor_id") else None,
        "need_payment": row.get("status") == "awaiting_payment",
    }


def sniff_image(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(data) > 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return ""


def run_upscale(job_id: str) -> None:
    row = load_orders().get(job_id) or {}
    source = Path(row.get("source") or "")
    dest = OUT / f"{job_id}.jpg"
    try:
        update_order(job_id, status="working", message="Making the photo sharp…")
        saved = upscale(source, dest, scale_factor())
        original = ""
        if source.exists():
            public_original = OUT / f"{job_id}-original{source.suffix.lower()}"
            public_original.write_bytes(source.read_bytes())
            original = f"/media/{public_original.name}"
        update_order(
            job_id,
            status="ready",
            message="Your photo is sharp. Download it now.",
            image_url=f"/media/{saved.name}",
            original_url=original,
            finished_at=datetime.now().isoformat(timespec="seconds"),
        )
    except Exception as exc:
        refund_token(row.get("visitor_id") or "", row.get("ip") or "", row.get("bucket") or "")
        update_order(job_id, status="error", message=str(exc))


def start_paid_or_free(job_id: str, visitor_id: str, ip: str) -> tuple[dict, str]:
    bucket, reason = spend_token(visitor_id, ip)
    if reason:
        update_order(job_id, status="awaiting_payment", message=reason, visitor_id=visitor_id, ip=ip)
        payload = public_job(load_orders()[job_id])
        payload["tokens_left"] = tokens_left(visitor_id)
        return payload, reason
    update_order(
        job_id,
        status="working",
        bucket=bucket,
        visitor_id=visitor_id,
        ip=ip,
        message="Making the photo sharp…",
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    threading.Thread(target=run_upscale, args=(job_id,), daemon=True).start()
    payload = public_job(load_orders()[job_id])
    payload["tokens_left"] = tokens_left(visitor_id)
    return payload, ""


def store_upload(visitor_id: str, ip: str, filename: str, data: bytes) -> tuple[dict, str, int]:
    if len(data) < 32:
        return {}, "Choose a photo first.", 400
    if len(data) > MAX_BYTES:
        return {}, "That photo is over 8 MB. Export a smaller JPG and try again.", 400
    kind = sniff_image(data)
    if not kind:
        return {}, "Use a JPG, PNG, or WebP photo.", 400
    if not render_ready():
        return {}, "Upscales are paused right now.", 503
    job_id = "img_" + uuid.uuid4().hex[:12]
    source = INBOX / f"{job_id}.{kind}"
    source.write_bytes(data)
    update_order(
        job_id,
        id=job_id,
        kind="upscale",
        filename=filename[:180],
        source=str(source),
        visitor_id=visitor_id,
        ip=ip,
        status="created",
        message="Photo received.",
        created_at=datetime.now().isoformat(timespec="seconds"),
        image_url=None,
    )
    payload, reason = start_paid_or_free(job_id, visitor_id, ip)
    status = 402 if payload.get("need_payment") else 200
    if reason and not payload.get("need_payment"):
        return payload, reason, 429
    return payload, "", status


def credit_payment(order_id: str, payment_id: str) -> dict:
    with lock:
        orders = load_orders()
        row = orders.get(order_id) or {}
        already = bool(row.get("payment_id"))
        if not already:
            row["payment_id"] = payment_id
            row["status"] = "paid"
            row["message"] = f"Payment received. {pack_tokens()} upscales were added."
            orders[order_id] = row
            save_orders(orders)
            visitor_id = row.get("visitor_id") or ""
            data = load_tokens()
            visitor = _visitor_row(data, visitor_id)
            visitor["paid"] += pack_tokens()
            data["visitors"][visitor_id] = visitor
            save_tokens(data)
        job_id = row.get("job_id") or ""
        visitor_id = row.get("visitor_id") or ""
        ip = row.get("ip") or ""
    if not already and job_id:
        job = load_orders().get(job_id) or {}
        if job.get("status") == "awaiting_payment":
            start_paid_or_free(job_id, visitor_id, ip or job.get("ip") or "")
    return load_orders().get(order_id) or {}


def cookie_header(visitor_id: str) -> str:
    return f"{VISITOR_COOKIE}={visitor_id}; Max-Age=31536000; Path=/; HttpOnly; SameSite=Lax"


def parse_cookie(header: str, name: str) -> str:
    for part in (header or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        if key == name:
            return value.strip()[:80]
    return ""


def _visitor(request: Request) -> tuple[str, bool]:
    current = request.cookies.get(VISITOR_COOKIE, "")
    if current and len(current) <= 80:
        return current, False
    return uuid.uuid4().hex, True


def _with_cookie(payload: dict, visitor_id: str, fresh: bool, status: int = 200) -> JSONResponse:
    response = JSONResponse(payload, status_code=status)
    if fresh:
        response.set_cookie(VISITOR_COOKIE, visitor_id, max_age=31536000, httponly=True, samesite="lax", path="/")
    return response


def _request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not ip and request.client:
        ip = request.client.host or ""
    return ip or "unknown"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, **page_context()})


@app.get("/sitemap.xml")
async def sitemap_xml():
    return Response(
        sitemap(price_rupees(), free_tokens(), pack_tokens()),
        media_type="application/xml",
    )


@app.get("/robots.txt")
async def robots_txt():
    return Response(robots(), media_type="text/plain")


@app.get("/guides", response_class=HTMLResponse)
async def guide_index(request: Request):
    price, free, pack = price_rupees(), free_tokens(), pack_tokens()
    return templates.TemplateResponse(
        "guides.html",
        {"request": request, "guides": guides(price, free, pack), "seo": guides_index_seo(price, free)},
    )


@app.get("/guides/{slug}", response_class=HTMLResponse)
async def guide_page(request: Request, slug: str):
    guide = guide_map(price_rupees(), free_tokens(), pack_tokens()).get(slug)
    if not guide:
        raise HTTPException(404, "Not found.")
    return templates.TemplateResponse(
        "guide.html",
        {"request": request, "guide": guide, "seo": guide_seo(guide)},
    )


@app.get("/api/tokens")
async def token_status(request: Request):
    visitor_id, fresh = _visitor(request)
    return _with_cookie(
        {"tokens_left": tokens_left(visitor_id), "free": free_tokens(), "pack": pack_tokens()},
        visitor_id,
        fresh,
    )


@app.post("/api/upscale")
async def create_upscale(request: Request, image: UploadFile = File(...)):
    visitor_id, fresh = _visitor(request)
    data = await image.read()
    payload, reason, status = store_upload(visitor_id, _request_ip(request), image.filename or "photo", data)
    if reason and status != 402:
        payload = {"detail": reason, "tokens_left": tokens_left(visitor_id)}
    return _with_cookie(payload, visitor_id, fresh, status)


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    row = load_orders().get(job_id)
    if not row or row.get("kind") != "upscale":
        raise HTTPException(404, "Photo not found.")
    return public_job(row)


@app.post("/api/order")
async def create_order(request: Request):
    visitor_id, fresh = _visitor(request)
    body = {}
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
    job_id = str(body.get("job_id") or "")
    amount = price_rupees() * 100
    receipt = "unb_" + uuid.uuid4().hex[:10]
    order = client().order.create(
        {
            "amount": amount,
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
            "notes": {"product": f"{pack_tokens()} image upscales"},
        }
    )
    update_order(
        order["id"],
        id=order["id"],
        kind="payment",
        receipt=receipt,
        job_id=job_id,
        visitor_id=visitor_id,
        ip=_request_ip(request),
        amount=amount,
        currency="INR",
        status="created",
        message="Waiting for payment.",
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    return _with_cookie(
        {"id": order["id"], "amount": amount, "currency": "INR", "key_id": razorpay_keys()[0]},
        visitor_id,
        fresh,
    )


@app.post("/api/verify")
async def verify_payment(request: Request):
    body = await request.json()
    order_id = str(body.get("razorpay_order_id") or "")
    payment_id = str(body.get("razorpay_payment_id") or "")
    signature = str(body.get("razorpay_signature") or "")
    row = load_orders().get(order_id)
    if not row or row.get("kind") != "payment":
        raise HTTPException(404, "Order not found. Start again from the page.")
    if not row.get("payment_id"):
        try:
            client().utility.verify_payment_signature(
                {
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                }
            )
        except Exception as exc:
            raise HTTPException(400, "Payment could not be verified.") from exc
        credit_payment(order_id, payment_id)
    job_id = (load_orders().get(order_id) or {}).get("job_id") or ""
    job = load_orders().get(job_id) or {}
    payload = public_job(job) if job else {"status": "paid", "message": f"{pack_tokens()} upscales were added."}
    payload["tokens_left"] = tokens_left(row.get("visitor_id") or "")
    payload["payment_id"] = order_id
    return payload


@app.get("/{slug}", response_class=HTMLResponse)
async def policy_page(request: Request, slug: str):
    page = pages(price_rupees(), pack_tokens()).get(slug)
    if not page:
        raise HTTPException(404, "Not found.")
    return templates.TemplateResponse(
        "policy.html",
        {"request": request, "page": page, "seo": policy_seo(slug, page)},
    )
