"""
product_analyzer.py - 100-point heuristic scoring (project guide, section 6).

This is an internal decision-support heuristic, NOT a sales prediction.
Missing information is treated as "unknown" and awarded few or zero points -
we never invent data to make a score look good.
"""

WEIGHTS = {
    "demand": 20,     # Google Trends interest (optional signal)
    "rating": 15,     # rating + review volume
    "price": 15,      # price competitiveness / impulse-buy band
    "profit": 25,     # margin as a share of selling price
    "risk": 15,       # quality / return risk
    "marketing": 10,  # visual, demo-friendly category + original image
}

HIGH_RISK_CATEGORIES = ["apparel", "kurti", "dress", "shoe", "footwear", "saree",
                        "jeans", "lingerie", "bra", "legging"]
MEDIUM_RISK_CATEGORIES = ["jewellery", "jewelry", "watch", "bag", "toy",
                          "cosmetic", "makeup", "sunglass"]
STRONG_MARKETING_CATEGORIES = ["kitchen", "home", "organizer", "decor", "gadget",
                               "tool", "storage", "bedsheet", "stationery"]


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_demand(trends_interest):
    t = _as_float(trends_interest)
    if not t:
        return 0, "Demand: Google Trends interest not recorded (0/20)"
    if t >= 70:
        return 20, "Demand: Trends interest %.0f/100 - strong (20/20)" % t
    if t >= 45:
        return 14, "Demand: Trends interest %.0f/100 - average (14/20)" % t
    if t >= 25:
        return 8, "Demand: Trends interest %.0f/100 - weak (8/20)" % t
    return 2, "Demand: Trends interest %.0f/100 - very low (2/20)" % t


def _score_rating(rating, review_count):
    r = _as_float(rating)
    n = _as_float(review_count)
    if r is None or n is None:
        return 0, "Rating/reviews not recorded - verify in the Meesho app (0/15)"
    pts = 0
    if r >= 4.3:
        pts += 9
    elif r >= 4.0:
        pts += 6
    elif r >= 3.7:
        pts += 3
    if n >= 500:
        pts += 6
    elif n >= 200:
        pts += 4
    elif n >= 50:
        pts += 2
    return pts, "Rating %.1f with %d reviews (%d/15)" % (r, int(n), pts)


def _score_price(app_price):
    p = _as_float(app_price)
    if not p:
        return 0, "App price not recorded (0/15)"
    if 199 <= p <= 699:
        return 15, "Price Rs.%.0f is in the impulse-buy band (15/15)" % p
    if 150 <= p < 199:
        return 11, "Price Rs.%.0f - low ticket, small margin (11/15)" % p
    if 700 < p <= 1200:
        return 9, "Price Rs.%.0f - high ticket, COD refusal risk (9/15)" % p
    if p < 150:
        return 5, "Price Rs.%.0f - very low ticket (5/15)" % p
    return 3, "Price Rs.%.0f - too high for a cold social audience (3/15)" % p


def _score_profit(selling_price, margin):
    m = _as_float(margin) or 0.0
    s = _as_float(selling_price) or 0.0
    if m <= 0:
        return 0, "Profit: reselling margin not verified in the app (0/25)"
    if s <= 0:
        if m >= 150:
            return 18, "Profit: Rs.%.0f margin is healthy - add the selling price (18/25)" % m
        if m >= 90:
            return 12, "Profit: Rs.%.0f margin is fair (12/25)" % m
        return 6, "Profit: Rs.%.0f margin is thin (6/25)" % m
    pct = (m / s) * 100
    if pct >= 30:
        return 25, "Profit: Rs.%.0f margin = %.1f%% of selling price (25/25)" % (m, pct)
    if pct >= 22:
        return 19, "Profit: Rs.%.0f margin = %.1f%% of selling price (19/25)" % (m, pct)
    if pct >= 15:
        return 13, "Profit: Rs.%.0f margin = %.1f%% of selling price (13/25)" % (m, pct)
    if pct >= 9:
        return 7, "Profit: Rs.%.0f margin = %.1f%% of selling price - thin (7/25)" % (m, pct)
    return 3, "Profit: Rs.%.0f margin = %.1f%% of selling price - too thin (3/25)" % (m, pct)


def _score_risk(return_risk, category):
    cat = (category or "").lower()
    if str(return_risk or "Unknown").title() == "Unknown":
        if any(k in cat for k in HIGH_RISK_CATEGORIES):
            return 4, "Risk: unknown, but category is size-dependent - treat as HIGH (4/15)"
        if any(k in cat for k in MEDIUM_RISK_CATEGORIES):
            return 9, "Risk: unknown, category is medium risk (9/15)"
        return 7, "Risk: unknown - check supplier quality and return reasons (7/15)"
    pts = {"Low": 15, "Medium": 9, "High": 3}.get(str(return_risk).title(), 7)
    return pts, "Risk: %s return risk (%d/15)" % (return_risk, pts)


def _score_marketing(category, has_image):
    cat = (category or "").lower()
    pts = 4
    if any(k in cat for k in STRONG_MARKETING_CATEGORIES):
        pts = 7
    if has_image:
        pts = min(pts + 3, 10)
        return pts, "Marketing: visual category + original product image (%d/10)" % pts
    return pts, "Marketing: %d/10 - add your own original product image" % pts


def analyze(product: dict) -> dict:
    """Score one product dict and explain every point awarded."""
    d_pts, d_msg = _score_demand(product.get("trends_interest"))
    r_pts, r_msg = _score_rating(product.get("rating"), product.get("review_count"))
    p_pts, p_msg = _score_price(product.get("app_price"))
    pf_pts, pf_msg = _score_profit(
        product.get("target_selling_price"), product.get("reselling_margin"))
    rk_pts, rk_msg = _score_risk(product.get("return_risk"), product.get("category"))
    m_pts, m_msg = _score_marketing(
        product.get("category"), bool(product.get("image_reference")))

    reasons = [d_msg, r_msg, p_msg, pf_msg, rk_msg, m_msg]

    missing = []
    if not _as_float(product.get("trends_interest")):
        missing.append("Google Trends interest (optional signal)")
    if _as_float(product.get("rating")) is None or _as_float(product.get("review_count")) is None:
        missing.append("Rating and review count")
    if not _as_float(product.get("reselling_margin")):
        missing.append("Reselling margin shown in the Meesho app")
    if str(product.get("return_risk") or "Unknown").title() == "Unknown":
        missing.append("Return risk assessment")
    if not product.get("image_reference"):
        missing.append("Original product image reference")
    if not product.get("delivery_estimate"):
        missing.append("Delivery estimate")

    total = round(d_pts + r_pts + p_pts + pf_pts + rk_pts + m_pts, 1)

    if total >= 80:
        decision = "TEST"
        verdict = "Test candidate - validate with 5-10 real orders."
    elif total >= 65:
        decision = "RESEARCH"
        verdict = "Research more - fill the missing fields, then decide."
    else:
        decision = "SKIP"
        verdict = "Avoid for now - the score is too low."

    hard_stops = []
    if not _as_float(product.get("reselling_margin")):
        hard_stops.append("Reselling margin not verified in the app.")
    rating = _as_float(product.get("rating"))
    if rating is not None and rating < 3.5:
        hard_stops.append("Rating below 3.5 - quality risk is too high.")
    if str(product.get("return_risk") or "").title() == "High":
        hard_stops.append("High return risk - RTOs will eat the margin.")

    return {
        "score": total,
        "decision": decision,
        "verdict": verdict,
        "reasons": reasons,
        "missing": missing,
        "hard_stops": hard_stops,
        "breakdown": {
            "demand": d_pts, "rating": r_pts, "price": p_pts,
            "profit": pf_pts, "risk": rk_pts, "marketing": m_pts,
        },
    }


def score_product_row(row: dict) -> dict:
    """Convenience wrapper for a row read from the database."""
    keys = ("app_price", "target_selling_price", "reselling_margin", "rating",
            "review_count", "category", "return_risk", "trends_interest",
            "image_reference", "delivery_estimate")
    return analyze({k: row.get(k) for k in keys})


if __name__ == "__main__":
    demo = {
        "category": "Kitchen", "app_price": 349, "target_selling_price": 499,
        "reselling_margin": 150, "rating": 4.3, "review_count": 820,
        "return_risk": "Low", "trends_interest": 62,
        "image_reference": "assets/rack.jpg", "delivery_estimate": "4-6 days",
    }
    out = analyze(demo)
    print("Score:", out["score"], "|", out["decision"])
    print(out["verdict"])
    for line in out["reasons"]:
        print("  -", line)
    print("Missing:", out["missing"])
    print("Hard stops:", out["hard_stops"])