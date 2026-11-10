"""
ai_content.py - offline marketing drafts for human review.

Uses only verified details you provided. Never invents a claim, never sends a
message, never posts anything. Every draft is text on disk that you read first.
"""

import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADS_DIR = os.path.join(BASE_DIR, "generated_ads")


def _clean_price(value):
    try:
        return "Rs.%s" % format(float(value), ",.0f")
    except (TypeError, ValueError):
        return ""


def generate_drafts(product):
    """Build drafts strictly from the details supplied. Nothing is assumed."""
    name = (product.get("product_name") or "").strip() or "This product"
    price_text = _clean_price(product.get("selling_price"))
    features = (product.get("verified_features") or "").strip().rstrip(".")
    delivery = (product.get("delivery_estimate") or "").strip()
    cod_available = product.get("cod_available") is True

    facts = []
    if price_text:
        facts.append("Price: %s." % price_text)
    if features:
        facts.append("%s." % features)
    if cod_available:
        facts.append("Cash on Delivery is available.")
    if delivery:
        facts.append("Delivery estimate: %s." % delivery)

    facts_text = " ".join(facts)
    facts_sentence = (" " + facts_text) if facts_text else ""

    return {
        "whatsapp_status": (
            "%s.%s Message me your delivery PIN code to check availability."
            % (name, facts_sentence)
        ),
        "social_caption": (
            "%s\n\n%s\n\nSend a message with your delivery PIN code to check availability."
            % (name, facts_text)
        ),
        "customer_reply": (
            "Thanks for asking about %s.%s "
            "Please share your delivery PIN code so availability can be checked."
            % (name, facts_sentence)
        ),
    }


def save_drafts(product, drafts):
    """Write the drafts to a text file for you to review before posting."""
    os.makedirs(ADS_DIR, exist_ok=True)

    raw_name = product.get("product_name") or "product"
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", raw_name).strip("_")[:40] or "product"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(ADS_DIR, "%s_%s.txt" % (safe_name, timestamp))

    with open(filepath, "w", encoding="utf-8") as file:
        file.write("MARKETING DRAFTS - REVIEW BEFORE USE\n")
        file.write("Product: %s\n" % raw_name)
        file.write("Created: %s\n" % datetime.now().strftime("%Y-%m-%d %H:%M"))
        file.write("Not verified, not sent, not posted automatically.\n\n")
        file.write("WHATSAPP STATUS\n%s\n\n" % drafts["whatsapp_status"])
        file.write("SOCIAL CAPTION\n%s\n\n" % drafts["social_caption"])
        file.write("CUSTOMER REPLY\n%s\n" % drafts["customer_reply"])

    return filepath


def generate_ad_package(product):
    """Wrapper for intake_app.py compatibility."""
    drafts = generate_drafts(product)
    return {
        "ad_copy": drafts.get("whatsapp_status", ""),
        "social_caption": drafts.get("social_caption", ""),
        "customer_reply": drafts.get("customer_reply", ""),
        "whatsapp_status": drafts.get("whatsapp_status", ""),
    }


if __name__ == "__main__":
    demo_product = {
        "product_name": "DEMO: Kitchen Storage Rack",
        "selling_price": 499,
        "verified_features": "Demo feature: three shelves",
        "delivery_estimate": "4-6 days",
        "cod_available": False,
    }

    drafts = generate_drafts(demo_product)

    for title, key in [
        ("WhatsApp Status", "whatsapp_status"),
        ("Social Caption", "social_caption"),
        ("Customer Reply", "customer_reply"),
    ]:
        print("\n--- %s ---" % title)
        print(drafts[key])

    print("\nSaved:", save_drafts(demo_product, drafts))