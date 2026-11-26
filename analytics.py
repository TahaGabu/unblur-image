"""Google Analytics 4. The measurement id is public. The API secret stays in the environment."""

from __future__ import annotations

import json
import os
import re
import threading
import urllib.parse
import urllib.request

_CLIENT_OK = re.compile(r"^[A-Za-z0-9._:-]{8,80}$")
_MEASUREMENT_OK = re.compile(r"^G-[A-Z0-9]+$")
_DEFAULT_MEASUREMENT_ID = "G-NGEN5HTTM2"


def measurement_id() -> str:
    value = os.environ.get("GA_MEASUREMENT_ID", "").strip() or _DEFAULT_MEASUREMENT_ID
    if not _MEASUREMENT_OK.fullmatch(value):
        return _DEFAULT_MEASUREMENT_ID
    return value


def safe_error(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[A-Za-z]:\\[^\s]+", "", text)
    text = re.sub(r"/[^\s]+", "", text)
    text = " ".join(text.split()).strip()[:80]
    return text or exc.__class__.__name__


def _cookie(header: str, name: str) -> str:
    prefix = name + "="
    for part in (header or "").split(";"):
        part = part.strip()
        if part.startswith(prefix):
            return urllib.parse.unquote(part[len(prefix):])
    return ""


def _clean_client(value: str) -> str:
    value = (value or "").strip()
    if value.lower() in {"undefined", "null", "none"}:
        return ""
    return value if _CLIENT_OK.fullmatch(value) else ""


def _client_from_cookie(header: str) -> str:
    parts = _cookie(header, "_ga").split(".")
    if len(parts) >= 4 and parts[-2].isdigit() and parts[-1].isdigit():
        return f"{parts[-2]}.{parts[-1]}"
    return ""


def _session_from_cookie(header: str) -> str:
    mid = measurement_id()
    suffix = mid[2:] if mid.startswith("G-") else mid
    raw = _cookie(header, f"_ga_{suffix}")
    if not raw:
        return ""
    match = re.search(r"(?:^|[.$])s(\d{5,})", raw)
    if match:
        return match.group(1)
    parts = raw.split(".")
    if len(parts) >= 3 and parts[0] == "GS1" and parts[2].isdigit():
        return parts[2]
    return ""


def _page_location(referer: str) -> str:
    referer = (referer or "").strip()
    if not referer.startswith("http"):
        return ""
    return referer.split("#", 1)[0].split("?", 1)[0][:150]


def collect_ids(cookie: str, client_header: str, session_header: str, referer: str, user_id: str = "") -> dict:
    client_id = _clean_client(client_header) or _client_from_cookie(cookie) or _clean_client(user_id)
    session_id = _clean_client(session_header) if (session_header or "").strip().isdigit() else ""
    if not session_id:
        session_id = _session_from_cookie(cookie)
    return {
        "client_id": client_id,
        "session_id": session_id if session_id.isdigit() else "",
        "page_location": _page_location(referer),
        "user_id": _clean_client(user_id),
    }


def ga_from_request(request, user_id: str = "") -> dict:
    return collect_ids(
        request.headers.get("cookie", ""),
        request.headers.get("x-ga-client", ""),
        request.headers.get("x-ga-session", ""),
        request.headers.get("referer", ""),
        user_id,
    )


def ga_from_environ(environ: dict, user_id: str = "") -> dict:
    return collect_ids(
        environ.get("HTTP_COOKIE", ""),
        environ.get("HTTP_X_GA_CLIENT", ""),
        environ.get("HTTP_X_GA_SESSION", ""),
        environ.get("HTTP_REFERER", ""),
        user_id,
    )


def _clean_params(params: dict, session_id: str, page_location: str) -> dict:
    clean: dict = {"engagement_time_msec": 100, "via": "server"}
    if session_id.isdigit():
        clean["session_id"] = int(session_id)
    if page_location:
        clean["page_location"] = page_location[:150]
    for key, value in params.items():
        if len(clean) >= 25:
            break
        name = re.sub(r"[^A-Za-z0-9_]", "_", str(key))[:40]
        if not name or name[0].isdigit() or name in clean:
            continue
        if name == "items" and isinstance(value, list):
            clean["items"] = value[:10]
            continue
        if isinstance(value, bool):
            clean[name] = "yes" if value else "no"
        elif isinstance(value, (int, float)):
            clean[name] = value
        elif value is None:
            continue
        else:
            clean[name] = str(value)[:100]
    return clean


def track(name: str, ga: dict | None = None, params: dict | None = None) -> None:
    """Send one Measurement Protocol event. No-op without GA_API_SECRET. Never raises."""
    secret = os.environ.get("GA_API_SECRET", "").strip()
    mid = measurement_id()
    if not secret or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", name):
        return
    ga = ga or {}
    client_id = _clean_client(str(ga.get("client_id") or "")) or _clean_client(str(ga.get("user_id") or ""))
    if not client_id:
        return
    body: dict = {
        "client_id": client_id,
        "events": [
            {
                "name": name,
                "params": _clean_params(
                    params or {},
                    str(ga.get("session_id") or ""),
                    str(ga.get("page_location") or ""),
                ),
            }
        ],
    }
    user_id = _clean_client(str(ga.get("user_id") or ""))
    if user_id:
        body["user_id"] = user_id
    query = urllib.parse.urlencode({"measurement_id": mid, "api_secret": secret})
    url = "https://www.google-analytics.com/mp/collect?" + query
    payload = json.dumps(body).encode("utf-8")

    def _send() -> None:
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                resp.read()
        except Exception:
            return

    threading.Thread(target=_send, daemon=True).start()
