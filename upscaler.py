"""Clarity upscaler."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import replicate
import requests

MODEL = (
    os.environ.get("IMAGE_MODEL", "").strip()
    or "philz1337x/clarity-upscaler:b8a46b09384dc1ac996596bc14058e2b7604971128ee7de709a40d4bbf982d2c"
)


def _proxy() -> str | None:
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    if os.environ.get("PYTHONANYWHERE_DOMAIN") or os.environ.get("PYTHONANYWHERE_SITE"):
        return "http://proxy.server:3128"
    return None


def _client() -> replicate.Client:
    return replicate.Client(
        api_token=os.environ.get("REPLICATE_API_TOKEN", "").strip(),
        transport=httpx.HTTPTransport(proxy=_proxy()),
        timeout=httpx.Timeout(30.0, read=120.0, write=180.0, connect=30.0, pool=30.0),
    )


def _url(output) -> str:
    if isinstance(output, str):
        return output
    if hasattr(output, "url") and output.url:
        return output.url
    if isinstance(output, (list, tuple)) and output:
        return _url(output[0])
    raise RuntimeError("The upscaler returned nothing.")


def _kind(header: bytes) -> str:
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    return ""


def _download(url: str, dest: Path) -> Path:
    proxy = _proxy()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    with requests.get(url, timeout=300, stream=True, proxies=proxies) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=256 * 1024):
                if chunk:
                    handle.write(chunk)
    if dest.stat().st_size < 1000:
        raise RuntimeError("The download was empty.")
    kind = _kind(dest.read_bytes()[:16])
    if kind and dest.suffix.lower() != f".{kind}":
        renamed = dest.with_suffix(f".{kind}")
        dest.replace(renamed)
        return renamed
    return dest


def upscale(source: Path, dest: Path, scale: int = 2) -> Path:
    if not os.environ.get("REPLICATE_API_TOKEN", "").strip():
        raise RuntimeError("Add REPLICATE_API_TOKEN before an upscale can run.")
    handle = source.open("rb")
    try:
        output = _client().run(
            MODEL,
            input={
                "image": handle,
                "prompt": os.environ.get(
                    "IMAGE_PROMPT",
                    "masterpiece, best quality, highres, <lora:more_details:0.5> <lora:SDXLrender_v2.0:1>",
                ),
                "dynamic": 6,
                "sd_model": os.environ.get("IMAGE_SD_MODEL", "").strip()
                or "juggernaut_reborn.safetensors [338b85bc4f]",
                "scheduler": "DPM++ 3M SDE Karras",
                "creativity": 0.35,
                "lora_links": "",
                "downscaling": False,
                "resemblance": 0.6,
                "scale_factor": scale,
                "tiling_width": 112,
                "tiling_height": 144,
                "custom_sd_model": "",
                "negative_prompt": os.environ.get(
                    "IMAGE_NEGATIVE_PROMPT",
                    "(worst quality, low quality, normal quality:2) JuggernautNegative-neg",
                ),
                "num_inference_steps": 18,
                "downscaling_resolution": 768,
            },
            wait=False,
        )
    finally:
        handle.close()
    return _download(_url(output), dest)
