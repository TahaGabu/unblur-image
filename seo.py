"""Titles, descriptions, and structured data.

The ranking name is "Unblur image". That phrase, plus "AI image upscaler",
is what people type when they want a blurry photo made sharp.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

SITE = os.environ.get("SITE_URL", "http://127.0.0.1:8000").rstrip("/")


def is_free() -> bool:
    return os.environ.get("FREE_MODE", "1").strip().lower() not in {"0", "false", "no"}


PUBLISHED = "2026-10-22"


def url(path: str = "/") -> str:
    if not path.startswith("/"):
        path = "/" + path
    return SITE if path == "/" else SITE + path


def output_scale() -> int:
    try:
        value = int(os.environ.get("SCALE_FACTOR", "4"))
    except ValueError:
        return 4
    return value if value in (2, 4) else 2


def faqs(price: int, free: int, pack: int) -> list[dict]:
    scale = output_scale()
    return [
        {
            "q": "How do I unblur an image?",
            "a": (
                "Open this page, choose a JPG, PNG, or WebP photo, and press Unblur. "
                f"The result is about {scale}× as wide and {scale}× as tall, with the blur reduced."
            ),
        },
        {
            "q": "Is the image upscaler free?",
            "a": (
                "Yes. Unblur image is free right now. Upload a JPG, PNG, or WebP, then download the sharp photo. No account."
                if is_free()
                else (
                    f"The first {free} photos on a device are free, so you can see the quality before you pay. "
                    f"After that, ₹{price} adds {pack} more upscales."
                )
            ),
        },
        {
            "q": "Will it recover a photo that is completely out of focus?",
            "a": (
                "It restores detail on soft, small, and lightly blurred photos. "
                "A photo with no detail left in the subject cannot be made perfect. Try one of the free photos and judge it yourself."
            ),
        },
        {
            "q": "What size do I get back?",
            "a": f"About {scale}× the width and {scale}× the height of the file you upload. A 1000×1000 photo comes back near {1000 * scale}×{1000 * scale}.",
        },
        {
            "q": "Do I need an account?",
            "a": (
                "No. Unblur image is free and stays on this device. There is no signup."
                if is_free()
                else "No. The free tries and the paid pack stay on this device. There is no signup."
            ),
        },
        {
            "q": "What if the file fails?",
            "a": (
                "If the upscale errors, try again with a JPG, PNG, or WebP under 8 MB. The token is returned so you can run it again."
                if is_free()
                else (
                    "If a paid upscale errors or does not appear within 24 hours, write to us with the order ID "
                    "and we refund it in full."
                )
            ),
        },
    ]


def guides(price: int, free: int, pack: int) -> list[dict]:
    scale = output_scale()
    return [
        {
            "slug": "unblur-image",
            "title": "Unblur image",
            "description": "Unblur image free, online. AI image upscaler with no account and no watermark." if is_free() else f"Unblur a photo online. {free} free tries, then ₹{price} for {pack} more. No account.",
            "h1": "Unblur image online",
            "lede": "A soft photo can be made readable again when some detail is still in the file. Unblur does that in the browser.",
            "sections": [
                (
                    "What to upload",
                    [
                        "Use a JPG, PNG, or WebP under 8 MB. Portraits, product photos, old scans, and screenshots all work.",
                        "The closer the subject is to sharp already, the better the result. Heavy motion blur is harder than a photo that is only a little soft.",
                    ],
                ),
                (
                    "What you get",
                    [
                        "Unblur image is free right now. There is no account and no watermark." if is_free() else f"The first {free} photos on this device are free. ₹{price} then adds {pack} more.",
                        f"Each result is about {scale}× the width and height, without a watermark.",
                    ],
                ),
            ],
        },
        {
            "slug": "ai-image-upscaler",
            "title": "AI image upscaler",
            "description": f"Free AI image upscaler. Enlarge a photo by {scale}× with no account." if is_free() else f"AI image upscaler that enlarges a photo by {scale}×. {free} free upscales, then ₹{price} for {pack}.",
            "h1": "AI image upscaler",
            "lede": "An upscaler makes a small photo larger without simply stretching the pixels.",
            "sections": [
                (
                    "When to upscale",
                    [
                        "Use it when a picture looks fine on a phone and breaks into blocks on a laptop, or when a marketplace asks for a larger file.",
                        "Upload the original, not a photo of a photo, when you still have it.",
                    ],
                ),
                (
                    "How this one works",
                    [
                        f"Unblur is a free AI image upscaler and returns a {scale}× file." if is_free() else f"Unblur runs a clarity model and returns a {scale}× file. {free} tries are free. ₹{price} buys {pack} more.",
                    ],
                ),
            ],
        },
        {
            "slug": "blur-remover",
            "title": "Blur remover",
            "description": "Free blur remover. Unblur a photo online and download it on this page." if is_free() else "Remove light blur from a photo. Free tries, then a small pack in rupees. Download on this page.",
            "h1": "Blur remover for photos",
            "lede": "Blur from a shaky hand or a small file is different from a photo that never had detail. This tool is for the first kind.",
            "sections": [
                (
                    "Try it on one photo",
                    [
                        "Pick the picture, wait a few minutes, and compare it with the original on the same page.",
                        "If the eyes, text, or product edge look better, download it. The tool is free right now." if is_free() else "If the eyes, text, or product edge look better, download it. If they do not, you have not paid.",
                    ],
                ),
            ],
        },
        {
            "slug": "upscale-image",
            "title": "Upscale image",
            "description": f"Upscale image free to {scale}× the width and height. No account." if is_free() else f"Upscale an image to {scale}× the size. {free} free, then ₹{price} for {pack} photos.",
            "h1": f"Upscale image to {scale}× the size",
            "lede": f"A {scale}× photo is the largest size this upscaler runs. That is the useful step for printing, listings, and slides.",
            "sections": [
                (
                    f"{scale}×, not a guess",
                    [
                        f"Every upscale on this page is {scale}× the width and height. That is the highest size this model is set to run.",
                        "You can upscale a photo for free right now. There is no subscription." if is_free() else f"You can upscale {free} photos free. After that, ₹{price} is {pack} more photos, not a subscription.",
                    ],
                ),
            ],
        },
    ]


def guide_map(price: int, free: int, pack: int) -> dict[str, dict]:
    return {item["slug"]: item for item in guides(price, free, pack)}


def _graph(*nodes: dict) -> str:
    return json.dumps({"@context": "https://schema.org", "@graph": list(nodes)}, ensure_ascii=False)


def _org() -> dict:
    node = {
        "@type": "Organization",
        "@id": url("/") + "#business",
        "name": "Unblur",
        "url": url("/"),
        "logo": url("/static/favicon.svg"),
        "address": {"@type": "PostalAddress", "addressCountry": "IN"},
    }
    email = os.environ.get("CONTACT_EMAIL", "").strip()
    if email:
        node["email"] = email
    locality = os.environ.get("BUSINESS_ADDRESS", "").strip()
    if locality:
        node["address"]["addressLocality"] = locality
    return node


REVIEWS_FILE = Path(__file__).resolve().parent / "reviews.json"


def load_reviews() -> list[dict]:
    """Real customer reviews only. Each one is also shown on the home page."""
    try:
        data = json.loads(REVIEWS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for r in data if isinstance(data, list) else []:
        try:
            rating = float(r["rating"])
            name = str(r["author"]).strip()
            body = str(r["body"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if name and body and 1 <= rating <= 5:
            out.append({"author": name, "body": body, "rating": rating, "date": str(r.get("date", "")).strip()})
    return out


def _review_markup() -> dict:
    """aggregateRating/review for the Product, built from reviews.json.

    Returns nothing when there are no real reviews: Google only allows
    ratings that are genuine and visible on the page.
    """
    reviews = load_reviews()
    if not reviews:
        return {}
    avg = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
    nodes = []
    for r in reviews:
        node = {
            "@type": "Review",
            "reviewRating": {"@type": "Rating", "ratingValue": r["rating"], "bestRating": 5, "worstRating": 1},
            "author": {"@type": "Person", "name": r["author"]},
            "reviewBody": r["body"],
        }
        if r["date"]:
            node["datePublished"] = r["date"]
        nodes.append(node)
    return {
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": avg,
            "reviewCount": len(reviews),
            "bestRating": 5,
            "worstRating": 1,
        },
        "review": nodes,
    }


def _offer(price: int) -> dict:
    return {
        "@type": "Offer",
        "url": url("/"),
        "priceCurrency": "INR",
        "price": price,
        "availability": "https://schema.org/OnlineOnly",
        "itemCondition": "https://schema.org/NewCondition",
        "shippingDetails": {
            "@type": "OfferShippingDetails",
            "shippingRate": {"@type": "MonetaryAmount", "value": 0, "currency": "INR"},
            "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "IN"},
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": {"@type": "QuantitativeValue", "minValue": 0, "maxValue": 1, "unitCode": "DAY"},
                "transitTime": {"@type": "QuantitativeValue", "minValue": 0, "maxValue": 0, "unitCode": "DAY"},
            },
        },
        "hasMerchantReturnPolicy": {
            "@type": "MerchantReturnPolicy",
            "applicableCountry": "IN",
            "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
            "merchantReturnDays": 7,
            "returnMethod": "https://schema.org/ReturnByMail",
            "returnFees": "https://schema.org/FreeReturn",
            "merchantReturnLink": url("/refunds"),
        },
    }


def home_seo(price: int, free: int, pack: int) -> dict:
    scale = output_scale()
    if is_free():
        title = "Unblur Image Free — AI Image Upscaler"
        description = (
            f"Unblur image free with an AI image upscaler. "
            f"Remove blur and upscale a photo about {scale}×. No account and no watermark."
        )
        offer = _offer(0)
    else:
        title = "Unblur Image — AI Image Upscaler"
        description = (
            f"Unblur image online with an AI image upscaler. "
            f"{free} photos free, then ₹{price} for {pack} more. About {scale}× larger, no account."
        )
        offer = _offer(price)
    faq_node = {
        "@type": "FAQPage",
        "@id": url("/") + "#faq",
        "mainEntity": [
            {"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
            for item in faqs(price, free, pack)
        ],
    }
    product = {
        "@type": "Product",
        "name": "Free AI image upscaler" if is_free() else f"{pack} AI image upscales",
        "description": description,
        "brand": {"@type": "Brand", "name": "Unblur"},
        "image": url("/static/favicon.svg"),
        "offers": offer,
    }
    product.update(_review_markup())
    app_node = {
        "@type": "WebApplication",
        "name": "Unblur Image",
        "applicationCategory": "PhotographyApplication",
        "operatingSystem": "Web",
        "browserRequirements": "Requires a modern web browser",
        "isAccessibleForFree": is_free(),
        "offers": offer,
        "url": url("/"),
        "description": description,
    }
    website = {
        "@type": "WebSite",
        "@id": url("/") + "#website",
        "name": "Unblur",
        "url": url("/"),
        "description": "Unblur image and upscale a photo online.",
        "publisher": {"@id": url("/") + "#business"},
        "inLanguage": "en",
    }
    return pack_meta(title, description, "/", "website", _graph(_org(), website, product, app_node, faq_node))


def policy_seo(slug: str, page: dict) -> dict:
    descriptions = {
        "contact": "Email, phone, and address for Unblur, the AI image upscaler.",
        "terms": "How to use Unblur, the free AI image upscaler.",
        "privacy": "What Unblur stores about a photo, why, and how long the file stays.",
        "refunds": "When Unblur refunds an upscale pack, and how to ask.",
        "delivery": "Unblur delivers a digital image on this page. Nothing is shipped.",
    }
    title = f"{page['title']} | Unblur"
    description = descriptions.get(slug, page["title"])
    crumbs = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Unblur", "item": url("/")},
            {"@type": "ListItem", "position": 2, "name": page["title"], "item": url("/" + slug)},
        ],
    }
    return pack_meta(title, description, "/" + slug, "website", _graph(_org(), crumbs))


def guide_seo(guide: dict) -> dict:
    path = "/guides/" + guide["slug"]
    article = {
        "@type": "Article",
        "headline": guide["h1"],
        "description": guide["description"],
        "datePublished": PUBLISHED,
        "dateModified": PUBLISHED,
        "author": {"@id": url("/") + "#business"},
        "publisher": {"@id": url("/") + "#business"},
        "mainEntityOfPage": url(path),
        "image": url("/static/favicon.svg"),
    }
    crumbs = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Unblur", "item": url("/")},
            {"@type": "ListItem", "position": 2, "name": "Guides", "item": url("/guides")},
            {"@type": "ListItem", "position": 3, "name": guide["title"], "item": url(path)},
        ],
    }
    return pack_meta(guide["title"] + " | Unblur", guide["description"], path, "article", _graph(_org(), article, crumbs))


def guides_index_seo(price: int, free: int) -> dict:
    title = "Guides: unblur image, upscale, and remove blur | Unblur"
    description = (
        "How to unblur a photo and upscale it free. No account."
        if is_free()
        else f"How to unblur a photo and upscale it. {free} free tries, then ₹{price}."
    )
    return pack_meta(title, description, "/guides", "website", _graph(_org()))


def pack_meta(title: str, description: str, path: str, kind: str, schema: str) -> dict:
    return {
        "title": title,
        "description": description,
        "url": url(path),
        "type": kind,
        "schema": schema,
    }


def sitemap(price: int, free: int, pack: int) -> str:
    paths = ["/", "/guides", "/contact", "/terms", "/privacy", "/refunds", "/delivery"]
    paths += [f"/guides/{item['slug']}" for item in guides(price, free, pack)]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in paths:
        lines.append("  <url>")
        lines.append(f"    <loc>{url(path)}</loc>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def robots() -> str:
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /api/",
            "Disallow: /media/",
            "",
            f"Sitemap: {url('/sitemap.xml')}",
            "",
        ]
    )
