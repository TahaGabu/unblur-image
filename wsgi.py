"""PythonAnywhere entry. Same shop, without the FastAPI adapter."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import (
    MAX_BYTES,
    OUT,
    VISITOR_COOKIE,
    client,
    cookie_header,
    credit_payment,
    free_tokens,
    load_orders,
    pack_tokens,
    page_context,
    parse_cookie,
    price_rupees,
    public_job,
    razorpay_keys,
    store_upload,
    templates,
    tokens_left,
    update_order,
)
from policies import pages
from seo import guide_map, guides, guides_index_seo, guide_seo, policy_seo, robots, sitemap

STATIC = ROOT / "static"
POLICY_SLUGS = {"contact", "terms", "privacy", "refunds", "delivery"}


def _send(start_response, status: str, body: bytes, content_type: str, extra: list | None = None):
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            *(extra or []),
        ],
    )
    return [body]


def _json(start_response, payload: dict, status: str = "200 OK", extra: list | None = None):
    return _send(start_response, status, json.dumps(payload).encode("utf-8"), "application/json", extra)


def _html(start_response, template: str, context: dict):
    body = templates.get_template(template).render(context).encode("utf-8")
    return _send(start_response, "200 OK", body, "text/html; charset=utf-8")


def _visitor(environ) -> tuple[str, bool]:
    current = parse_cookie(environ.get("HTTP_COOKIE", ""), VISITOR_COOKIE)
    if current:
        return current, False
    return uuid.uuid4().hex, True


def _ip(environ) -> str:
    forwarded = environ.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else ""
    return ip or environ.get("REMOTE_ADDR") or "unknown"


def _read_json(environ) -> dict:
    length = int(environ.get("CONTENT_LENGTH") or 0)
    raw = environ["wsgi.input"].read(length) if length else b""
    if not raw:
        return {}
    data = json.loads(raw.decode("utf-8"))
    return data if isinstance(data, dict) else {}


def _upload(environ) -> tuple[str, bytes]:
    ctype = environ.get("CONTENT_TYPE", "")
    if "boundary=" not in ctype:
        return "", b""
    boundary = ctype.split("boundary=", 1)[1].strip().strip('"').encode()
    length = int(environ.get("CONTENT_LENGTH") or 0)
    if length > MAX_BYTES + 200_000:
        raise ValueError("That photo is over 8 MB. Export a smaller JPG and try again.")
    body = environ["wsgi.input"].read(length) if length else b""
    fence = b"--" + boundary
    for part in body.split(fence):
        if b'name="image"' not in part:
            continue
        header, _, data = part.partition(b"\r\n\r\n")
        if data.endswith(b"\r\n"):
            data = data[:-2]
        filename = "photo"
        if b'filename="' in header:
            filename = header.split(b'filename="', 1)[1].split(b'"', 1)[0].decode("utf-8", "replace")
        return filename or "photo", data
    return "", b""


def _file(start_response, root: Path, relative: str):
    target = (root / relative).resolve()
    if not str(target).startswith(str(root.resolve())) or not target.is_file():
        return _json(start_response, {"detail": "Not found."}, "404 Not Found")
    path = target
    kind = "application/octet-stream"
    if path.suffix == ".css":
        kind = "text/css; charset=utf-8"
    elif path.suffix == ".js":
        kind = "text/javascript; charset=utf-8"
    elif path.suffix == ".svg":
        kind = "image/svg+xml"
    elif path.suffix in {".jpg", ".jpeg"}:
        kind = "image/jpeg"
    elif path.suffix == ".png":
        kind = "image/png"
    elif path.suffix == ".webp":
        kind = "image/webp"
    return _send(start_response, "200 OK", path.read_bytes(), kind)


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO") or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    if method == "GET" and path.startswith("/static/"):
        return _file(start_response, STATIC, path[len("/static/"):])
    if method == "GET" and path.startswith("/media/"):
        return _file(start_response, OUT, path[len("/media/"):])
    if method == "GET" and path == "/":
        return _html(start_response, "index.html", page_context())
    if method == "GET" and path == "/sitemap.xml":
        body = sitemap(price_rupees(), free_tokens(), pack_tokens()).encode("utf-8")
        return _send(start_response, "200 OK", body, "application/xml")
    if method == "GET" and path == "/robots.txt":
        return _send(start_response, "200 OK", robots().encode("utf-8"), "text/plain; charset=utf-8")
    if method == "GET" and path == "/guides":
        price, free, pack = price_rupees(), free_tokens(), pack_tokens()
        return _html(
            start_response,
            "guides.html",
            {"guides": guides(price, free, pack), "seo": guides_index_seo(price, free)},
        )
    if method == "GET" and path.startswith("/guides/"):
        guide = guide_map(price_rupees(), free_tokens(), pack_tokens()).get(path[len("/guides/"):])
        if not guide:
            return _json(start_response, {"detail": "Not found."}, "404 Not Found")
        return _html(start_response, "guide.html", {"guide": guide, "seo": guide_seo(guide)})

    if method == "GET" and path == "/api/tokens":
        visitor_id, fresh = _visitor(environ)
        extra = [("Set-Cookie", cookie_header(visitor_id))] if fresh else None
        return _json(
            start_response,
            {"tokens_left": tokens_left(visitor_id), "free": free_tokens(), "pack": pack_tokens()},
            extra=extra,
        )

    if method == "POST" and path == "/api/upscale":
        visitor_id, fresh = _visitor(environ)
        extra = [("Set-Cookie", cookie_header(visitor_id))] if fresh else None
        try:
            filename, data = _upload(environ)
        except ValueError as exc:
            return _json(start_response, {"detail": str(exc)}, "400 Bad Request", extra)
        payload, reason, status = store_upload(visitor_id, _ip(environ), filename, data)
        http = "200 OK"
        if status == 402:
            http = "402 Payment Required"
        elif status == 400:
            http = "400 Bad Request"
        elif status == 429:
            http = "429 Too Many Requests"
        elif status >= 500:
            http = "503 Service Unavailable"
        if reason and status != 402:
            payload = {"detail": reason, "tokens_left": tokens_left(visitor_id)}
        return _json(start_response, payload, http, extra)

    if method == "GET" and path.startswith("/api/jobs/"):
        job_id = path[len("/api/jobs/"):].strip("/")
        row = load_orders().get(job_id)
        if not row or row.get("kind") != "upscale":
            return _json(start_response, {"detail": "Photo not found."}, "404 Not Found")
        return _json(start_response, public_job(row))

    if method == "POST" and path == "/api/order":
        visitor_id, fresh = _visitor(environ)
        extra = [("Set-Cookie", cookie_header(visitor_id))] if fresh else None
        try:
            body = _read_json(environ)
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
                job_id=str(body.get("job_id") or ""),
                visitor_id=visitor_id,
                ip=_ip(environ),
                amount=amount,
                currency="INR",
                status="created",
                message="Waiting for payment.",
                created_at=datetime.now().isoformat(timespec="seconds"),
            )
            return _json(
                start_response,
                {"id": order["id"], "amount": amount, "currency": "INR", "key_id": razorpay_keys()[0]},
                extra=extra,
            )
        except Exception as exc:
            return _json(start_response, {"detail": str(exc)}, "500 Internal Server Error", extra)

    if method == "POST" and path == "/api/verify":
        try:
            body = _read_json(environ)
            order_id = str(body.get("razorpay_order_id") or "")
            payment_id = str(body.get("razorpay_payment_id") or "")
            signature = str(body.get("razorpay_signature") or "")
            row = load_orders().get(order_id)
            if not row or row.get("kind") != "payment":
                return _json(start_response, {"detail": "Order not found. Start again from the page."}, "404 Not Found")
            if not row.get("payment_id"):
                client().utility.verify_payment_signature(
                    {
                        "razorpay_order_id": order_id,
                        "razorpay_payment_id": payment_id,
                        "razorpay_signature": signature,
                    }
                )
                credit_payment(order_id, payment_id)
            job = load_orders().get(row.get("job_id") or "") or {}
            payload = public_job(job) if job else {"status": "paid"}
            payload["tokens_left"] = tokens_left(row.get("visitor_id") or "")
            payload["payment_id"] = order_id
            return _json(start_response, payload)
        except Exception:
            return _json(start_response, {"detail": "Payment could not be verified."}, "400 Bad Request")

    if method == "GET" and path.startswith("/") and path.count("/") == 1:
        slug = path[1:]
        if slug in POLICY_SLUGS:
            page = pages(price_rupees(), pack_tokens()).get(slug)
            if page:
                return _html(start_response, "policy.html", {"page": page, "seo": policy_seo(slug, page)})
    return _json(start_response, {"detail": "Not found."}, "404 Not Found")
