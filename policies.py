"""Pages Razorpay checks before it activates live payments."""

from __future__ import annotations

import os


def contact() -> dict:
    return {
        "business": os.environ.get("BUSINESS_NAME", "").strip() or "Unblur",
        "email": os.environ.get("CONTACT_EMAIL", "").strip(),
        "phone": os.environ.get("CONTACT_PHONE", "").strip(),
        "address": os.environ.get("BUSINESS_ADDRESS", "").strip(),
    }


def pages(price: int, pack: int) -> dict[str, dict]:
    c = contact()
    reach = c["email"] or "the email on the Contact page"
    return {
        "contact": {
            "title": "Contact us",
            "sections": [
                ("Who runs Unblur", [f"Unblur is run by {c['business']}."]),
                (
                    "How to reach us",
                    [
                        line
                        for line in (
                            f"Email: {c['email']}" if c["email"] else "",
                            f"Phone: {c['phone']}" if c["phone"] else "",
                            f"Address: {c['address']}" if c["address"] else "",
                            "We reply within 2 working days. For a payment problem, include your Razorpay order ID (it starts with order_).",
                        )
                        if line
                    ],
                ),
            ],
        },
        "terms": {
            "title": "Terms and conditions",
            "sections": [
                (
                    "What you are buying",
                    [
                        f"Each device can unblur {pack} photos for free, so you can see the result before you pay.",
                        f"One payment of ₹{price} adds {pack} more upscales. One token makes one photo.",
                        "The result is about twice the width and height of the photo you upload. It follows the picture you give us. It does not invent a new scene.",
                    ],
                ),
                (
                    "What you may upload",
                    [
                        "Upload a photo you have the right to use. Do not upload sexual content, content involving minors, or anything illegal in India. We may refuse those files.",
                    ],
                ),
                (
                    "Payments",
                    [
                        "Payments are processed by Razorpay. We never see or store your card, UPI, or bank details.",
                        "Prices are in Indian rupees and include all charges.",
                    ],
                ),
                (
                    "Changes",
                    ["We may update these terms. The version on this page is the one that applies to your order."],
                ),
            ],
        },
        "privacy": {
            "title": "Privacy policy",
            "sections": [
                (
                    "What we keep",
                    [
                        "The photo you upload, the sharpened file, your Razorpay order and payment IDs, and how many tokens this device has used.",
                        "Razorpay collects the payment details you enter at checkout under its own privacy policy. We do not receive your card or bank details.",
                    ],
                ),
                (
                    "Why we keep it",
                    [
                        "To sharpen the photo, let you download it, and handle refunds or support questions.",
                        "The photo is sent to our image provider (Replicate) only to run the upscaler.",
                    ],
                ),
                (
                    "How long",
                    [
                        "Photos may be deleted after 7 days to free space, so download yours soon after it is ready. Order records are kept for accounting.",
                    ],
                ),
                (
                    "Your choices",
                    [f"To ask what we hold about an order or to have it deleted, write to {reach} with the order ID."],
                ),
            ],
        },
        "refunds": {
            "title": "Cancellation and refund policy",
            "sections": [
                (
                    "Before you pay",
                    ["If you close checkout before paying, you are not charged. The free tries are not a purchase."],
                ),
                (
                    "If the upscale fails",
                    [
                        "If you were charged but the page shows an error, or the sharpened photo is not ready within 24 hours of payment, you get a full refund.",
                        f"Write to {reach} with your order ID. Nothing is shipped back. We refund to the original payment method within 5–7 working days of approving it.",
                    ],
                ),
                (
                    "After delivery",
                    [
                        "Because the file is made from your photo, we cannot cancel an order once the sharpened image has been delivered, unless the file is broken. In that case write to us within 7 days and we will run it again or refund it.",
                    ],
                ),
            ],
        },
        "delivery": {
            "title": "Shipping and delivery policy",
            "sections": [
                (
                    "Nothing is shipped",
                    ["Unblur sells a digital image only. Nothing is posted or shipped to an address."],
                ),
                (
                    "How you receive it",
                    [
                        "The sharpened photo appears on this page with a Download button when it is ready. A free try and a paid try work the same way.",
                        "Most photos are ready in a few minutes. Keep the page open until it finishes.",
                        f"If the page was closed or the photo did not arrive within 24 hours, write to {reach} with your order ID and we will send the file or refund you.",
                    ],
                ),
            ],
        },
    }
