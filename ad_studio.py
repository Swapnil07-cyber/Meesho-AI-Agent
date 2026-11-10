"""
ad_studio.py - Facebook / Instagram / WhatsApp ad generator.

Standard library only. No external APIs, no auto-posting.
Generates ad copy + HTML visual preview. You review, then post manually.

Run:   python intake_app.py   (already includes ad studio via nav)
"""
import html
import os
import re
import urllib.parse
from datetime import datetime

import database as db
import product_analyzer as pa
import web_app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ templates --
AD_TEMPLATES = {
    "hooks": [
        "Just launched! {name} now at Rs. {price}",
        "Home essential alert: {name}",
        "Customers are loving this: {name}",
        "Limited stock: {name} at Rs. {price}",
        "Upgrade your {category} game with {name}",
        "Daily deal: {name} - Rs. {price}",
        "Trending now: {name}",
        "Value pick: {name} under Rs. {price}",
    ],
    "ctas": ["Shop Now", "Order Today", "Grab Yours", "Buy Now", "Check Price", "DM to Order"],
    "hashtag_sets": {
        "Kitchen": ["#kitchenware", "#homeorganizer", "#kitchenhack", "#homedecor", "#kitchenessential", "#homeutility"],
        "Apparel": ["#fashion", "#style", "#outfit", "#trendy", "#dailywear", "#indianfashion"],
        "Footwear": ["#footwear", "#shoes", "#comfort", "#style", "#trendy", "#dailywear"],
        "Jewellery": ["#jewellery", "#fashion", "#accessories", "#trendy", "#style", "#ethnic"],
        "Beauty": ["#beauty", "#skincare", "#glowup", "#selfcare", "#trendy", "#fragrance"],
        "Electronics": ["#gadgets", "#tech", "#electronics", "#musthave", "#deals", "#dailyuse"],
        "Home": ["#homedecor", "#homeessential", "#lifestyle", "#comfort", "#trendy", "#utility"],
        "Stationery": ["#stationery", "#studygram", "#officesupplies", "#productivity", "#dailyuse"],
        "Toys": ["#toys", "#kids", "#fun", "#giftideas", "#playtime", "#learning"],
        "Other": ["#deals", "#musthave", "#shopnow", "#trending", "#budgetfind", "#dailydeal"],
    }
}


def _esc(v):
    return html.escape("" if v is None else str(v))


def _money(v):
    try:
        return "Rs.%s" % format(float(v), ",.0f")
    except (TypeError, ValueError):
        return "Rs.0"


def _pick_hook(product):
    name = product.get("product_name", "This product")
    price = product.get("target_selling_price") or product.get("app_price") or 0
    category = (product.get("category") or "Other").lower()
    rating = product.get("rating") or 0
    reviews = product.get("review_count") or 0

    # Pick based on product traits
    if rating >= 4.3 and reviews >= 500:
        return "Customers are loving this: {name}"
    elif "limited" in name.lower() or "pack" in name.lower():
        return "Limited stock: {name} at Rs. {price}"
    elif category in ("kitchen", "home"):
        return "Home essential alert: {name}"
    elif category in ("beauty", "apparel"):
        return "Trending now: {name}"
    else:
        return "Daily deal: {name} - Rs. {price}"


def generate_fb_ad(product):
    """Facebook ad: primary_text, headline, description, cta."""
    name = product.get("product_name", "This product")
    price = int(product.get("target_selling_price") or product.get("app_price") or 0)
    rating = product.get("rating") or 0
    reviews = product.get("review_count") or 0
    delivery = product.get("delivery_estimate") or "soon"
    features = product.get("notes") or ""
    category = product.get("category") or "Other"

    hook_template = _pick_hook(product)
    hook = hook_template.format(name=name[:60], price=price, category=category.lower())

    benefits = []
    if features:
        clean = features[:100] + "..." if len(features) > 100 else features
        benefits.append("Verified: " + clean)
    if rating and reviews:
        benefits.append("Rated %.1f★ by %s+ buyers" % (rating, reviews))
    if delivery:
        benefits.append("Delivery: %s" % delivery)

    benefit_text = " | ".join(benefits) if benefits else "Quality checked listing"

    primary = "{hook}\n\n{benefits}\n\nPrice: Rs. {price}\nDM to order or tap below.".format(
        hook=hook, benefits=benefit_text, price=price)

    headline = "%s - Rs. %s" % (name[:50], price)
    description = "Rated %.1f★ | %s+ reviews | Delivery %s" % (rating, reviews, delivery) if rating else "Home delivery available"
    cta = "Shop Now"

    return {
        "platform": "Facebook",
        "primary_text": primary,
        "headline": headline,
        "description": description,
        "cta": cta,
    }


def generate_ig_post(product):
    """Instagram caption + hashtags."""
    name = product.get("product_name", "This product")
    price = int(product.get("target_selling_price") or product.get("app_price") or 0)
    rating = product.get("rating") or 0
    reviews = product.get("review_count") or 0
    delivery = product.get("delivery_estimate") or "soon"
    features = product.get("notes") or ""
    category = product.get("category") or "Other"

    lines = [
        "✨ %s ✨" % name[:70],
        "",
        "Price: Rs. %s" % price,
    ]
    if features:
        clean = features[:90] + "..." if len(features) > 90 else features
        lines.append("Features: %s" % clean)
    if rating:
        lines.append("⭐ %.1f★ (%s+ reviews)" % (rating, reviews))
    if delivery:
        lines.append("📦 Delivery: %s" % delivery)
    lines.extend(["", "DM to order 📩", "COD available 💵"])

    hashtags = AD_TEMPLATES["hashtag_sets"].get(category, AD_TEMPLATES["hashtag_sets"]["Other"])
    name_words = [w.lower() for w in re.findall(r"[A-Za-z]+", name) if len(w) > 3][:3]
    extra_tags = ["#" + w for w in name_words]
    all_tags = list(dict.fromkeys(hashtags + extra_tags))
    hashtag_block = " ".join(all_tags[:10])

    return {
        "platform": "Instagram",
        "caption": "\n".join(lines),
        "hashtags": hashtag_block,
    }


def generate_whatsapp_status(product):
    """Short WhatsApp status text."""
    name = product.get("product_name", "This product")
    price = int(product.get("target_selling_price") or product.get("app_price") or 0)
    rating = product.get("rating") or 0
    delivery = product.get("delivery_estimate") or "soon"

    parts = ["%s - Rs. %s" % (name[:45], price)]
    if rating:
        parts.append("%.1f★" % rating)
    if delivery:
        parts.append("Delivery %s" % delivery)
    parts.append("DM to order")
    return " | ".join(parts)


def generate_ad_package(product):
    """Full ad package for a product."""
    return {
        "facebook": generate_fb_ad(product),
        "instagram": generate_ig_post(product),
        "whatsapp": generate_whatsapp_status(product),
        "product_name": product.get("product_name", ""),
        "product_id": product.get("id"),
    }


def save_ad_package(pkg, base_dir=BASE_DIR):
    """Save all ad variants to generated_ads/ folder."""
    folder = os.path.join(base_dir, "generated_ads")
    os.makedirs(folder, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in (pkg["product_name"] or "ad"))[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    txt_path = os.path.join(folder, "AD_%s_%s.txt" % (safe, ts))
    lines = [
        "AD PACKAGE: %s" % pkg["product_name"],
        "=" * 50,
        "",
        "FACEBOOK AD",
        "-" * 30,
        "Primary Text:", pkg["facebook"]["primary_text"],
        "",
        "Headline:", pkg["facebook"]["headline"],
        "",
        "Description:", pkg["facebook"]["description"],
        "",
        "CTA:", pkg["facebook"]["cta"],
        "",
        "INSTAGRAM POST",
        "-" * 30,
        pkg["instagram"]["caption"],
        "",
        "Hashtags:", pkg["instagram"]["hashtags"],
        "",
        "WHATSAPP STATUS",
        "-" * 30,
        pkg["whatsapp"],
        "",
        "Generated: %s" % ts,
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    html_path = os.path.join(folder, "AD_%s_%s.html" % (safe, ts))
    html_content = build_ad_html_preview(pkg)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return txt_path, html_path


def build_ad_html_preview(pkg):
    """Styled HTML preview that looks like social media posts."""
    fb = pkg["facebook"]
    ig = pkg["instagram"]
    wa = pkg["whatsapp"]
    name = _esc(pkg["product_name"])

    css = """
    body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;padding:20px;margin:0}
    .wrap{max-width:720px;margin:0 auto}
    .card{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,0.1)}
    .label{font-size:11px;color:#65676b;font-weight:600;text-transform:uppercase;margin-bottom:6px}
    .fb-primary{white-space:pre-wrap;font-size:15px;line-height:1.5;color:#1c1e21}
    .fb-box{background:#f0f2f5;border-radius:6px;padding:10px;margin-top:10px}
    .fb-head{font-weight:600;font-size:16px;color:#1c1e21}
    .fb-desc{font-size:13px;color:#65676b;margin-top:4px}
    .fb-cta{display:inline-block;background:#1877f2;color:#fff;padding:6px 14px;border-radius:4px;font-size:13px;font-weight:600;margin-top:8px}
    .ig-caption{white-space:pre-wrap;font-size:14px;line-height:1.5;color:#262626}
    .ig-hashtags{color:#00376b;font-size:14px;margin-top:8px}
    .wa-text{font-size:14px;color:#128c7e;background:#dcf8c6;padding:10px 14px;border-radius:8px;display:inline-block}
    h2{font-size:18px;margin:0 0 14px;color:#1c1e21}
    .muted{font-size:12px;color:#65676b}
    """

    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><title>Ad Preview - %s</title>"
            "<style>%s</style></head><body><div class='wrap'>"
            "<h2>Ad Preview: %s</h2>"
            "<div class='card'><div class='label'>Facebook Ad</div>"
            "<div class='fb-primary'>%s</div>"
            "<div class='fb-box'><div class='fb-head'>%s</div>"
            "<div class='fb-desc'>%s</div><div class='fb-cta'>%s</div></div></div>"
            "<div class='card'><div class='label'>Instagram Post</div>"
            "<div class='ig-caption'>%s</div>"
            "<div class='ig-hashtags'>%s</div></div>"
            "<div class='card'><div class='label'>WhatsApp Status</div>"
            "<div class='wa-text'>%s</div></div>"
            "<p class='muted'>Open this HTML file in any browser. Take a screenshot to use as your image.</p>"
            "</div></body></html>"
            % (name, css, name,
               _esc(fb["primary_text"]), _esc(fb["headline"]),
               _esc(fb["description"]), _esc(fb["cta"]),
               _esc(ig["caption"]), _esc(ig["hashtags"]), _esc(wa)))


# ------------------------------------------------------------------ UI --
def v_adstudio(flash="", product=None, pkg=None):
    products = db.list_products()
    body = ("<h2>Ad Studio</h2><p class='sub'>Select a product and generate ad copy for "
            "Facebook, Instagram, and WhatsApp. Review every line before posting. "
            "No automatic posting — you control what goes live.</p>" + flash)

    if not products:
        return web_app.page("Ad Studio", body + "<div class='info'>Add a product first.</div>", "/adstudio")

    popts = "".join("<option value='%s'>%s (%s)</option>"
                    % (p["id"], _esc(p["product_name"]), _esc(p["category"])) for p in products)

    body += ("<div class='panel'><form method='post' action='/adstudio/generate'>"
             "<label>Product</label><select name='product_id'>" + popts + "</select>"
             "<label style='font-weight:400'><input type='checkbox' name='save' value='1' "
             "style='width:auto;margin-right:6px'>Also save to generated_ads/ folder</label>"
             "<button type='submit'>Generate ad package</button></form></div>")

    if pkg and product:
        body += "<h3>Ads for %s</h3>" % _esc(product["product_name"])

        # Facebook
        fb = pkg["facebook"]
        body += ("<div class='panel'><div class='label' style='margin-bottom:8px'>Facebook Ad</div>"
                 "<label>Primary Text</label><div class='mono'>%s</div>"
                 "<label>Headline</label><div class='mono'>%s</div>"
                 "<label>Description</label><div class='mono'>%s</div>"
                 "<label>CTA</label><div class='mono'>%s</div></div>"
                 % (_esc(fb["primary_text"]), _esc(fb["headline"]),
                    _esc(fb["description"]), _esc(fb["cta"])))

        # Instagram
        ig = pkg["instagram"]
        body += ("<div class='panel'><div class='label' style='margin-bottom:8px'>Instagram Post</div>"
                 "<label>Caption</label><div class='mono'>%s</div>"
                 "<label>Hashtags</label><div class='mono'>%s</div></div>"
                 % (_esc(ig["caption"]), _esc(ig["hashtags"])))

        # WhatsApp
        body += ("<div class='panel'><div class='label' style='margin-bottom:8px'>WhatsApp Status</div>"
                 "<div class='mono'>%s</div></div>" % _esc(pkg["whatsapp"]))

        body += ("<div class='warn'>Read every line. Remove anything you cannot verify. "
                  "Edit in your own words before posting.</div>")

    return web_app.page("Ad Studio", body, "/adstudio")