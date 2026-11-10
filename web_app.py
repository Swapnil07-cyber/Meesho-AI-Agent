"""
web_app.py - the dashboard, built on the Python standard library only.

No Streamlit, no pandas, no numpy, no pyarrow - pure Python http.server.

Run:   python web_app.py
Open:  http://localhost:8501
Stop:  Ctrl + C in this terminal.
"""
import html
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import ai_content
import customer_manager as cm
import database as db
import product_analyzer as pa
import profit_calculator as pc
import reports

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8501

CATEGORIES = ["Kitchen", "Home", "Apparel", "Footwear", "Jewellery", "Beauty",
              "Electronics", "Stationery", "Toys", "Other"]
RISK_OPTIONS = ["Unknown", "Low", "Medium", "High"]
NAV = [
    ("/", "Dashboard", "dashboard"),
    ("/products", "Products", "inventory_2"),
    ("/profit", "Profit", "calculate"),
    ("/marketing", "Marketing", "campaign"),
    ("/customers", "Customers", "group"),
    ("/orders", "Orders", "shopping_bag"),
    ("/reports", "Reports", "analytics"),
    ("/guide", "Guide", "menu_book"),
]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');
body{margin:0;font-family:'Inter','Segoe UI',Arial,sans-serif;background:linear-gradient(180deg,#f5f7fb,#edf3ff);color:#1c2430;line-height:1.5}
header{background:linear-gradient(135deg,#0b2036,#1b3d63);color:#fff;padding:14px 20px;box-shadow:0 8px 20px rgba(11,32,54,0.14)}
header h1{margin:0;font-size:18px;font-weight:700;display:flex;align-items:center;gap:10px}header h1::before{content:'auto_awesome';font-family:'Material Symbols Outlined';font-size:20px;vertical-align:middle}
header p{margin:3px 0 0;font-size:12px;color:#9fb3c8}
nav{background:rgba(17,44,72,0.98);padding:0 10px;white-space:nowrap;overflow-x:auto;border-bottom:1px solid rgba(255,255,255,0.08)}
nav a{display:inline-flex;align-items:center;gap:7px;color:#dfeaf8;text-decoration:none;padding:12px 14px;font-size:13px;border-bottom:3px solid transparent;transition:all .2s ease}
nav a:hover{background:rgba(255,255,255,0.04);color:#fff}
nav a.on{color:#fff;border-bottom-color:#f0a726;background:rgba(240,167,38,0.08)}
.material-symbols-outlined{font-family:'Material Symbols Outlined';font-weight:normal;font-style:normal;font-size:18px;line-height:1;letter-spacing:normal;text-transform:none;display:inline-block;white-space:nowrap;word-wrap:normal;direction:ltr;-webkit-font-smoothing:antialiased;font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24}
main{max-width:1000px;margin:0 auto;padding:20px 16px 50px}
h2{font-size:19px;margin:0 0 3px}h3{font-size:14px;margin:18px 0 7px}
.sub{color:#5c6b7d;font-size:12.5px;margin:0 0 14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:12px;box-shadow:0 8px 20px rgba(17,24,39,0.04)}
.card .k{font-size:11px;color:#5c6b7d;text-transform:uppercase;letter-spacing:.4px}
.card .v{font-size:20px;font-weight:600;margin-top:3px}
.panel{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:16px;margin-bottom:14px;box-shadow:0 8px 20px rgba(17,24,39,0.04)}
label{display:block;font-size:12px;font-weight:600;color:#34465c;margin:0 0 4px}
input,select,textarea{width:100%;padding:7px 9px;border:1px solid #c8d3df;border-radius:5px;font-size:13.5px;font-family:inherit;background:#fff;margin-bottom:10px;box-sizing:border-box}
textarea{min-height:64px;resize:vertical}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
@media(max-width:700px){.grid2{grid-template-columns:1fr}}
button,.btn{background:linear-gradient(180deg,#122d4a,#0b2036);color:#fff;border:0;border-radius:5px;padding:8px 14px;font-size:13.5px;cursor:pointer;text-decoration:none;display:inline-block;font-family:inherit;box-shadow:0 6px 16px rgba(11,32,54,0.18)}
button:hover,.btn:hover{background:linear-gradient(180deg,#17395c,#122d4a)}.btn.alt{background:#e8eef5;color:#1c2430;box-shadow:none}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid #e8eef4}
th{background:#f7f9fc;font-size:11px;text-transform:uppercase;color:#5c6b7d}
.ok{background:#e8f7ed;border-left:4px solid #1f9d55;padding:9px 13px;border-radius:5px;margin-bottom:12px;font-size:13px}
.err{background:#fdeaea;border-left:4px solid #d64545;padding:9px 13px;border-radius:5px;margin-bottom:12px;font-size:13px}
.warn{background:#fff8e6;border-left:4px solid #F0A726;padding:9px 13px;border-radius:5px;margin-bottom:12px;font-size:13px}
.info{background:#eaf2fb;border-left:4px solid #2b6cb0;padding:9px 13px;border-radius:5px;margin-bottom:12px;font-size:13px}
.muted{color:#5c6b7d;font-size:12px}
.mono{font-family:Consolas,monospace;font-size:12px;white-space:pre-wrap;background:#f7f9fc;padding:11px;border-radius:5px;border:1px solid #e8eef4}
.tag{display:inline-block;padding:2px 7px;border-radius:9px;font-size:11px;font-weight:600;background:#eef2f6;color:#5c6b7d}
.t-test{background:#e8f7ed;color:#1f7a43}.t-research{background:#fff2d9;color:#8a5a00}.t-skip{background:#fdeaea;color:#a33}
footer{text-align:center;color:#8595a8;font-size:11.5px;padding:18px}
"""


def esc(v):
    return html.escape("" if v is None else str(v))


def money(v):
    try:
        return "Rs.%s" % format(float(v), ",.0f")
    except (TypeError, ValueError):
        return "Rs.0"


def num(v, default=None):
    try:
        s = str(v).strip()
        return default if s == "" else float(s)
    except (TypeError, ValueError):
        return default


def page(title, body, active="/"):
    links = "".join(
        '<a href="%s" class="%s"><span class="material-symbols-outlined" aria-hidden="true">%s</span><span>%s</span></a>'
        % (h, "on" if h == active else "", icon, t)
        for h, t, icon in NAV)
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>%s - Meesho AI Reselling Agent</title><style>%s</style></head><body>"
            "<header><h1>Meesho AI Reselling Agent</h1>"
            "<p>Local only. Manual verification. Human approval at every step.</p></header>"
            "<nav>%s</nav><main>%s</main>"
            "<footer>A practical build, not a guarantee of income.</footer></body></html>"
            % (esc(title), CSS, links, body))


def tag(decision):
    cls = {"TEST": "t-test", "RESEARCH": "t-research", "SKIP": "t-skip"}.get(decision, "")
    return '<span class="tag %s">%s</span>' % (cls, esc(decision or "unscored"))


def opts(name, values, selected=None, blank=None):
    out = ['<option value="">%s</option>' % esc(blank)] if blank else []
    for v in values:
        out.append('<option value="%s"%s>%s</option>'
                   % (esc(v), " selected" if str(v) == str(selected) else "", esc(v)))
    return "<select name='%s'>%s</select>" % (name, "".join(out))


def cards(pairs):
    return '<div class="cards">%s</div>' % "".join(
        '<div class="card"><div class="k">%s</div><div class="v">%s</div></div>'
        % (esc(k), esc(v)) for k, v in pairs)


# ------------------------------------------------------------------ pages --
def v_dashboard():
    m = db.dashboard_metrics()
    body = "<h2>Dashboard</h2><p class='sub'>Everything here comes from records you entered after checking the Meesho app yourself.</p>"
    body += cards([("Products", m["products"]), ("Inquiries", m["customers"]),
                   ("Orders", m["orders"]), ("Realised profit", money(m["realized_profit"])),
                   ("Delivered", m["delivered"]), ("Lost / RTO", m["lost"]),
                   ("Inquiry to order", "%s%%" % m["conversion_pct"]),
                   ("Loss rate", "%s%%" % m["rto_rate"])])
    body += ("<h3>Expected vs realised</h3><div class='panel'>"
             "<p style='margin:0 0 6px'><strong>Expected</strong> from open orders: %s</p>"
             "<p style='margin:0'><strong>Realised</strong> from paid orders: %s</p></div>"
             % (money(m["expected_profit"]), money(m["realized_profit"])))
    body += ("<div class='warn'>Expected profit is a hope, not income. It only becomes real "
             "when the order is delivered and the margin reaches your bank account.</div>")
    body += ("<h3>Start here</h3><div class='panel'><ol style='margin:0;padding-left:18px'>"
             "<li><a href='/products'>Products</a> - add listings you verified in the app.</li>"
             "<li><a href='/profit'>Profit</a> - confirm the margin is worth your time.</li>"
             "<li><a href='/marketing'>Marketing</a> - generate drafts, edit, post manually.</li>"
             "<li><a href='/customers'>Customers</a> - record inquiries and consent.</li>"
             "<li><a href='/orders'>Orders</a> - move each order through its real status.</li>"
             "</ol></div>")
    rows = db.list_products()[:10]
    if rows:
        body += "<h3>Top scored products</h3><div class='panel'><table><tr><th>Product</th><th>Category</th><th>Score</th><th>Decision</th><th>Margin</th></tr>"
        body += "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                        % (esc(p["product_name"]), esc(p["category"]), esc(p["score"]),
                           tag(p["decision"]), money(p["reselling_margin"])) for p in rows)
        body += "</table></div>"
    return page("Dashboard", body, "/")


def v_products(flash=""):
    form = ("<div class='panel'><form method='post' action='/products/add'><div class='grid2'><div>"
            "<label>Product name *</label><input name='product_name' required>"
            "<label>Meesho app link (optional)</label><input name='product_link'>"
            "<label>Category</label>" + opts("category", CATEGORIES, "Kitchen") +
            "<label>App price (Rs.)</label><input name='app_price' type='number' step='1' min='0'>"
            "<label>Your selling price (Rs.)</label><input name='target_selling_price' type='number' step='1' min='0'>"
            "<label>Reselling margin shown in the app (Rs.)</label><input name='reselling_margin' type='number' step='1' min='0'>"
            "</div><div>"
            "<label>Rating (blank if not checked)</label><input name='rating' type='number' step='0.1' min='0' max='5'>"
            "<label>Review count</label><input name='review_count' type='number' step='10' min='0'>"
            "<label>Delivery estimate</label><input name='delivery_estimate' placeholder='4-6 days'>"
            "<label>Return risk</label>" + opts("return_risk", RISK_OPTIONS, "Unknown") +
            "<label>Google Trends interest (optional)</label><input name='trends_interest' type='number' step='1' min='0' max='100'>"
            "<label>Original image reference</label><input name='image_reference' placeholder='assets/my-photo.jpg'>"
            "<label>Verified features</label><textarea name='notes' placeholder='Only facts you confirmed in the app'></textarea>"
            "</div></div><button type='submit'>Score and save</button></form></div>")

    items = []
    for p in db.list_products():
        r = pa.score_product_row(p)
        stops = "".join("<div class='warn'>%s</div>" % esc(s) for s in r["hard_stops"])
        reasons = "".join("<div class='muted'>- %s</div>" % esc(x) for x in r["reasons"])
        missing = ("<div class='info'>Still missing: %s</div>" % esc(", ".join(r["missing"]))
                   if r["missing"] else "")
        items.append(
            "<div class='panel'><table><tr><td style='width:70%%'><strong>%s</strong><br>"
            "<span class='muted'>%s | app %s | sell %s | margin %s | rating %s (%s reviews) | risk %s</span>"
            "</td><td style='text-align:right'><strong style='font-size:18px'>%s</strong>/100<br>%s</td></tr></table>"
            "<p style='margin:7px 0 3px'><em>%s</em></p>%s%s"
            "<form method='post' action='/products/delete' onsubmit=\"return confirm('Delete this product?')\" style='margin-top:9px'>"
            "<input type='hidden' name='product_id' value='%s'><button class='btn alt' type='submit'>Delete</button></form></div>"
            % (esc(p["product_name"]), esc(p["category"] or "-"), money(p["app_price"]),
               money(p["target_selling_price"]), money(p["reselling_margin"]),
               esc(p["rating"] or "-"), esc(p["review_count"] or 0), esc(p["return_risk"]),
               esc(p["score"]), tag(p["decision"]), esc(r["verdict"]), reasons + stops, missing,
               p["id"]))

    body = ("<h2>Products</h2><p class='sub'>Check the listing in the Meesho app yourself, then type the real values. "
            "Leave a field blank if you could not verify it - the score reflects that instead of guessing.</p>"
            + flash + form + "<h3>Saved products (%d)</h3>" % len(items))
    body += "".join(items) if items else "<div class='info'>No products yet.</div>"
    return page("Products", body, "/products")


def v_profit(query):
    products = db.list_products()
    pid = query.get("product", [""])[0]
    row = next((p for p in products if str(p["id"]) == pid), None)
    app = num(query.get("app", [None])[0], float(row["app_price"] or 0) if row else 349.0)
    sell = num(query.get("sell", [None])[0],
               float(row["target_selling_price"] or row["app_price"] or 0) if row else 499.0)
    extra = num(query.get("extra", [None])[0], 20.0)
    rto = num(query.get("rto", [None])[0], 22.0)
    fixed = num(query.get("fixed", [None])[0], 500.0)
    target = num(query.get("target", [None])[0], 100.0)

    out = pc.full_breakdown(app, sell, extra, rto / 100.0)
    be = pc.break_even_orders(fixed, out["expected_value"])

    popts = "".join("<option value='%s'%s>%s (app %s)</option>"
                    % (p["id"], " selected" if str(p["id"]) == pid else "",
                       esc(p["product_name"]), money(p["app_price"])) for p in products)

    body = ("<h2>Profit</h2><p class='sub'>Use the reselling margin the app actually shows. "
            "Do not copy supplier-panel payout rules into customer-side reselling.</p>")
    body += ("<div class='panel'><form method='get' action='/profit'><div class='grid2'><div>"
             "<label>Load a saved product (optional)</label><select name='product' onchange=\"this.form.submit()\">"
             "<option value=''>Manual entry</option>" + popts + "</select>"
             "<label>App price (Rs.)</label><input name='app' type='number' step='1' min='0' value='%.0f'>"
             "<label>Selling price (Rs.)</label><input name='sell' type='number' step='1' min='0' value='%.0f'>"
             "</div><div>"
             "<label>Extra cost per order (Rs.)</label><input name='extra' type='number' step='1' min='0' value='%.0f'>"
             "<label>Share of orders assumed to fail / RTO (%%), use 0 for clean estimate</label>"
             "<input name='rto' type='number' step='1' min='0' max='80' value='%.0f'>"
             "<label>Target net profit per order (Rs.)</label><input name='target' type='number' step='10' min='0' value='%.0f'>"
             "<label>Fixed spend to recover (Rs.)</label><input name='fixed' type='number' step='100' min='0' value='%.0f'>"
             "</div></div><button type='submit'>Calculate</button></form></div>"
             % (app, sell, extra, rto, target, fixed))
    body += "<h3>Result</h3>" + cards([
        ("Gross margin", money(out["margin"])), ("Margin %", "%s%%" % out["margin_percent"]),
        ("Estimated net profit", money(out["estimated_net_profit"])),
        ("Expected value / order", money(out["expected_value"]))])
    body += ("<div class='warn' style='margin-top:12px'>Expected value is the number that matters. "
             "A %s margin with a %.0f%% failure rate is closer to %s, not %s."
             % (money(out["margin"]), rto, money(out["expected_value"]), money(out["margin"])))
    body += ("<h3>Reverse the maths</h3><div class='panel'>"
             "<p style='margin:0 0 6px'>To net %s per order you must charge at least <strong>%s</strong> "
             "<span class='muted'>(app price %s + margin %s)</span></p>"
             % (money(target), money(pc.suggest_selling_price(app, target, extra)),
                money(app), money(pc.required_margin(app, target, extra))))
    if be is None:
        body += ("<div class='err'>Expected value per order is zero or negative - "
                 "this product cannot cover fixed costs.</div>")
    else:
        body += ("<div class='ok'>You need <strong>%d delivered orders</strong> to recover %s. "
                 "Delivered, not merely placed.</div>" % (be, money(fixed)))
    body += "</div>"

    payout = num(query.get("payout", [None])[0], 0.0) or 0.0
    acost = num(query.get("acost", [None])[0], 0.0) or 0.0
    body += ("<h3>Actual result of a completed order</h3><div class='panel'>"
             "<p class='sub' style='margin-top:0'>Fill this only when the outcome is final. "
             "Cancelled or returned orders are never sales.</p>"
             "<form method='get' action='/profit'>"
             "<input type='hidden' name='app' value='%.0f'><input type='hidden' name='sell' value='%.0f'>"
             "<div class='grid2'><div><label>Actual payout received (Rs.)</label>"
             "<input name='payout' type='number' step='1' min='0' value='%.0f'></div>"
             "<div><label>Actual extra cost (Rs.)</label>"
             "<input name='acost' type='number' step='1' min='0' value='%.0f'></div></div>"
             "<button type='submit'>Work out actual profit</button></form>"
             % (app, sell, payout, acost))
    if payout > 0:
        body += ("<div class='ok'>Actual net profit: <strong>%s</strong></div>"
                 % money(pc.actual_net_profit(payout, acost)))
    body += "</div>"
    return page("Profit", body, "/profit")


def v_marketing(flash="", drafts=None, product=None):
    products = db.list_products()
    body = ("<h2>Marketing</h2><p class='sub'>Drafts only. Nothing here posts or sends anything. "
            "Never present an AI-generated image as the real product photo.</p>" + flash)
    if not products:
        return page("Marketing", body + "<div class='info'>Add a product first in Products.</div>",
                    "/marketing")
    popts = "".join("<option value='%s'>%s (%s)</option>"
                    % (p["id"], esc(p["product_name"]), esc(p["category"])) for p in products)
    body += ("<div class='panel'><form method='post' action='/marketing/generate'>"
             "<label>Product</label><select name='product_id'>" + popts + "</select>"
             "<label style='font-weight:400'><input type='checkbox' name='save' value='1' "
             "style='width:auto;margin-right:6px'>Also save the drafts to generated_ads/</label>"
             "<button type='submit'>Generate drafts</button></form></div>")
    if drafts and product:
        body += "<h3>Drafts for %s</h3>" % esc(product["product_name"])
        for label, key in [("WhatsApp Status", "whatsapp_status"),
                           ("Social caption", "social_caption"),
                           ("Customer reply", "customer_reply")]:
            if key in drafts:
                body += ("<div class='panel'><label>%s</label><div class='mono'>%s</div></div>"
                         % (esc(label), esc(drafts[key])))
        body += ("<div class='warn'>Read every line before posting. Remove anything you cannot "
                 "verify about the product.</div>")
    return page("Marketing", body, "/marketing")


def v_customers(flash=""):
    body = ("<h2>Customers</h2><p class='sub'>Record an inquiry only when the customer contacted "
            "you or gave consent. Unsolicited bulk messaging breaks platform rules and loses trust.</p>"
            + flash)
    body += ("<div class='panel'><form method='post' action='/customers/add'><div class='grid2'><div>"
             "<label>Customer name *</label><input name='customer_name' required>"
             "<label>Mobile number *</label><input name='contact' required placeholder='9876543210'>"
             "<label>Source channel</label>" + opts("channel", cm.CHANNELS, "WhatsApp") +
             "<label>Consent to be messaged</label><select name='consent_status'>"
             "<option value='No'>No</option><option value='Yes'>Yes</option></select>"
             "</div><div><label>City</label><input name='city'>"
             "<label>Pincode</label><input name='pincode' placeholder='302001'>"
             "<label>What did they ask about?</label><textarea name='notes'></textarea>"
             "</div></div><button type='submit'>Save inquiry</button></form></div>")

    summary = {}
    for c in db.list_customers():
        ch = c["channel"] or "Unknown"
        summary[ch] = summary.get(ch, 0) + 1
    if summary:
        body += ("<h3>Inquiries by channel</h3><div class='panel'><table>"
                 "<tr><th>Channel</th><th>Inquiries</th></tr>"
                 + "".join("<tr><td>%s</td><td>%s</td></tr>" % (esc(k), esc(v))
                           for k, v in sorted(summary.items(), key=lambda x: -x[1]))
                 + "</table></div>")

    consented = cm.follow_up_list()
    body += "<h3>Follow-up list (consented customers only)</h3>"
    if consented:
        body += ("<div class='panel'><table><tr><th>Name</th><th>Contact</th><th>Channel</th>"
                 "<th>City</th><th>Notes</th></tr>"
                 + "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                           % (esc(c["customer_name"]), esc(c["contact"]), esc(c["channel"]),
                              esc(c["city"] or "-"), esc(c["notes"] or "-")) for c in consented)
                 + "</table></div>")
    else:
        body += "<div class='warn'>Nobody has given consent yet - do not message anyone else.</div>"

    allc = db.list_customers()
    body += "<h3>All records</h3>"
    if allc:
        body += ("<div class='panel'><table><tr><th>ID</th><th>Name</th><th>Contact</th>"
                 "<th>Channel</th><th>Consent</th><th>Date</th><th></th></tr>"
                 + "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                           "<td><form method='post' action='/customers/delete' "
                           "onsubmit=\"return confirm('Delete this record?')\">"
                           "<input type='hidden' name='customer_id' value='%s'>"
                           "<button class='btn alt' type='submit'>Delete</button></form></td></tr>"
                           % (esc(c["id"]), esc(c["customer_name"]), esc(c["contact"]),
                              esc(c["channel"]), esc(c["consent_status"]),
                              esc(c["inquiry_date"]), c["id"]) for c in allc)
                 + "</table></div>")
    else:
        body += "<div class='info'>No customers recorded yet.</div>"
    return page("Customers", body, "/customers")


def v_orders(flash=""):
    products, customers = db.list_products(), db.list_customers()
    body = ("<h2>Orders</h2><p class='sub'>Place the order yourself in the Meesho app, then record "
            "the reference here. Move the status only when the real status changes.</p>" + flash)
    if not products or not customers:
        return page("Orders", body + "<div class='info'>You need at least one product and one "
                    "customer before creating an order.</div>", "/orders")
    popts = "".join("<option value='%s'>%s</option>" % (p["id"], esc(p["product_name"]))
                    for p in products)
    copts = "".join("<option value='%s'>%s (%s)</option>"
                    % (c["id"], esc(c["customer_name"]), esc(c["contact"])) for c in customers)
    body += ("<div class='panel'><form method='post' action='/orders/add'><div class='grid2'><div>"
             "<label>Product</label><select name='product_id'>" + popts + "</select>"
             "<label>Customer</label><select name='customer_id'>" + copts + "</select>"
             "<label>Meesho order reference (optional)</label><input name='meesho_order_ref'>"
             "</div><div><label>Expected margin (Rs.)</label>"
             "<input name='margin_expected' type='number' step='1' min='0' required>"
             "<label>Extra cost (Rs.)</label><input name='extra_cost' type='number' step='1' min='0' value='0'>"
             "<label>Notes</label><textarea name='notes'></textarea>"
             "</div></div><button type='submit'>Create order record</button></form></div>")

    orders = db.list_orders()
    body += "<h3>Order board</h3>"
    if not orders:
        return page("Orders", body + "<div class='info'>No orders yet.</div>", "/orders")
    m = db.dashboard_metrics()
    body += ("<div class='muted' style='margin-bottom:9px'>Orders %s | delivered %s | lost %s | "
             "loss rate %s%%</div>" % (m["orders"], m["delivered"], m["lost"], m["rto_rate"]))
    for o in orders:
        st = o["order_status"]
        nxt = cm.next_statuses(st)
        if nxt:
            controls = ("<form method='post' action='/orders/status' style='margin-top:9px'>"
                        "<input type='hidden' name='order_id' value='%s'>"
                        "<label>Move to</label><select name='new_status'>%s</select>"
                        "<label>Actual payout received (Rs.) - only for Payout Received</label>"
                        "<input name='realized_payout' type='number' step='1' min='0' value='0'>"
                        "<button type='submit'>Update status</button></form>"
                        % (o["id"], "".join("<option value='%s'>%s</option>" % (esc(s), esc(s))
                                            for s in nxt)))
        else:
            controls = ("<div class='info' style='margin-top:9px'>%s is a final state - "
                        "no further changes.</div>" % esc(st))
        body += ("<div class='panel'><table><tr><td style='width:60%%'><strong>#%s %s</strong><br>"
                 "<span class='muted'>to %s | ordered %s | ref %s</span></td>"
                 "<td style='text-align:right'><span class='tag'>%s</span></td></tr></table>"
                 "<div class='muted' style='margin-top:7px'>Expected margin %s | extra cost %s | "
                 "realised payout %s | payout date %s</div>%s</div>"
                 % (o["id"], esc(o["product_name"] or "(deleted)"),
                    esc(o["customer_name"] or "(deleted)"), esc(o["order_date"]),
                    esc(o["meesho_order_ref"] or "-"), esc(st), money(o["margin_expected"]),
                    money(o["extra_cost"]), money(o["realized_payout"]),
                    esc(o["payout_date"] or "-"), controls))
    return page("Orders", body, "/orders")


def v_reports(query):
    days = int(num(query.get("days", [None])[0], 7) or 7)
    days = max(7, min(90, days))
    s = reports.weekly_summary(days)
    body = ("<h2>Reports</h2><p class='sub'>Everything here is derived from records you entered "
            "yourself. No estimate is ever presented as a realised number.</p>")
    body += "".join("<a class='btn alt' style='margin-right:7px' href='/reports?days=%s'>%s days</a>"
                    % (d, d) for d in (7, 30, 90)) + "<div style='height:14px'></div>"
    body += cards([("Orders", s["orders"]), ("Delivered", s["delivered"]),
                   ("Lost / RTO", s["lost"]), ("Realised profit", money(s["realized_profit"]))])
    body += "<h3>Weekly report</h3><div class='panel'><div class='mono'>%s</div></div>" % esc(
        reports.weekly_report_text(days))
    perf = reports.product_performance()
    body += "<h3>Product performance</h3>"
    if perf:
        body += ("<div class='panel'><table><tr><th>Product</th><th>Orders</th><th>Delivered</th>"
                 "<th>Lost</th><th>Realised</th></tr>"
                 + "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                           % (esc(r["product"]), esc(r["orders"]), esc(r["delivered"]),
                              esc(r["lost"]), money(r["realized_profit"])) for r in perf)
                 + "</table></div>")
    else:
        body += "<div class='info'>No orders recorded yet.</div>"
    body += ("<h3>Exports</h3><div class='panel'>"
             "<a class='btn' href='/export?type=products' style='margin-right:7px'>Export products CSV</a>"
             "<a class='btn' href='/export?type=orders'>Export orders CSV</a>"
             "<p class='muted' style='margin-bottom:0'>Files land in the exports/ folder.</p></div>")
    body += ("<h3>Back up the database</h3><div class='panel'>"
             "<div class='mono'>copy data\\meesho_agent.db data\\meesho_agent_backup.db</div>"
             "<p class='muted' style='margin-bottom:0'>Do this weekly. The whole business record "
             "lives in that one file.</p></div>")
    return page("Reports", body, "/reports")


def v_guide():
    body = """<h2>Guide and limits</h2><div class='panel'>
<h3 style='margin-top:0'>The 100-point score is a heuristic, not a prediction</h3>
<p>Weights: demand 20, rating 15, price 15, profit 25, risk 15, marketing 10. Above 80 means test
it with real orders. 65-79 means find the missing data first. Below 65 means leave it.</p>
<h3>Trend data is not sales data</h3><p>Google Trends interest shows curiosity, not purchases.</p>
<h3>Verify everything in the app before you share it</h3>
<p>Prices, margins and delivery promises change. Check the current app, then update the record.</p>
<h3>Estimated profit is not income</h3>
<p>Record actual profit only when the order is delivered and the margin is really in your bank
account. Cancelled and returned orders are not sales.</p>
<h3>Manual, consent-based messaging only</h3>
<p>No bulk WhatsApp sends, no unofficial automation, no scraping the app, no stored passwords or
OTPs.</p>
<h3>One human approval step stays in place</h3>
<p>Before publishing content, messaging a customer, choosing a product or placing an order.</p>
</div><h3>Realistic expectations</h3>
<div class='warn'>A Rs.150 margin with a 25-30% failure rate is roughly Rs.105 per order, before
your time. Ten successfully delivered orders is the first real milestone.</div>
<h3>Budget discipline (Rs.5,000)</h3><div class='panel'><table>
<tr><th>Use</th><th>Cap</th></tr>
<tr><td>Product sampling / small expenses</td><td>Rs.1,000</td></tr>
<tr><td>Creatives and organic tools</td><td>Rs.0-500</td></tr>
<tr><td>Paid promotion, only after validation</td><td>up to Rs.500</td></tr>
<tr><td>Order / return issue reserve</td><td>Rs.1,500</td></tr>
<tr><td>Emergency reserve</td><td>Rs.1,500-2,000</td></tr>
</table></div>"""
    return page("Guide", body, "/guide")


# ---------------------------------------------------------------- handler --
class Handler(BaseHTTPRequestHandler):
    server_version = "MeeshoAgent/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, body, status=200, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _go(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def _form(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8") if n else ""
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/":
                self._send(v_dashboard())
            elif u.path == "/products":
                self._send(v_products(self._ok(q)))
            elif u.path == "/profit":
                self._send(v_profit(q))
            elif u.path == "/marketing":
                self._send(v_marketing())
            elif u.path == "/customers":
                self._send(v_customers(self._ok(q)))
            elif u.path == "/orders":
                self._send(v_orders(self._ok(q)))
            elif u.path == "/reports":
                self._send(v_reports(q))
            elif u.path == "/guide":
                self._send(v_guide())
            elif u.path == "/export":
                self._export(q)
            else:
                self._send(page("Not found", "<h2>Page not found</h2>"
                                "<p><a href='/'>Back to the dashboard</a></p>"), 404)
        except Exception as exc:
            self._fail(exc)

    def _ok(self, q):
        return "<div class='ok'>%s</div>" % esc(q["ok"][0]) if "ok" in q else ""

    def _fail(self, exc):
        self._send(page("Error", "<h2>Something went wrong</h2><div class='err'>%s: %s</div>"
                        "<p><a href='/'>Back to the dashboard</a></p>"
                        % (esc(type(exc).__name__), esc(exc))), 500)

    def _export(self, q):
        kind = q.get("type", ["products"])[0]
        path = reports.export_orders() if kind == "orders" else reports.export_products()
        with open(path, "rb") as fh:
            self._send(fh.read(), 200, "text/csv; charset=utf-8")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        f = self._form()
        try:
            if u.path == "/products/add":
                self._product(f)
            elif u.path == "/products/delete":
                db.delete_product(int(f["product_id"]))
                self._go("/products?ok=" + urllib.parse.quote("Product deleted."))
            elif u.path == "/marketing/generate":
                self._marketing(f)
            elif u.path == "/customers/add":
                cid = cm.save_customer(f.get("customer_name", ""), f.get("contact", ""),
                                       f.get("channel", "WhatsApp"),
                                       f.get("consent_status", "No"), f.get("city", ""),
                                       f.get("pincode", ""), f.get("notes", ""))
                self._go("/customers?ok=" + urllib.parse.quote("Customer #%d saved." % cid))
            elif u.path == "/customers/delete":
                db.delete_customer(int(f["customer_id"]))
                self._go("/customers?ok=" + urllib.parse.quote("Record deleted."))
            elif u.path == "/orders/add":
                oid = cm.record_order(int(num(f.get("product_id"), 0) or 0) or None,
                                      int(num(f.get("customer_id"), 0) or 0) or None,
                                      f.get("meesho_order_ref", ""),
                                      num(f.get("margin_expected"), 0.0),
                                      num(f.get("extra_cost"), 0.0),
                                      f.get("notes", ""))
                self._go("/orders?ok=" + urllib.parse.quote("Order #%d recorded." % oid))
            elif u.path == "/orders/status":
                self._status(f)
            else:
                self._go("/")
        except (ValueError, KeyError) as exc:
            self._send(page("Not saved", "<h2>That did not save</h2><div class='err'>%s</div>"
                            "<p><a href='javascript:history.back()'>Go back and fix it</a></p>"
                            % esc(exc)), 400)
        except Exception as exc:
            self._fail(exc)

    def _product(self, f):
        if not f.get("product_name", "").strip():
            raise ValueError("Product name is required.")
        payload = {
            "product_name": f["product_name"].strip(),
            "product_link": f.get("product_link", ""),
            "category": f.get("category", "Other"),
            "app_price": num(f.get("app_price")),
            "target_selling_price": num(f.get("target_selling_price")),
            "rating": num(f.get("rating")),
            "review_count": int(num(f.get("review_count"), 0) or 0) or None,
            "reselling_margin": num(f.get("reselling_margin")),
            "delivery_estimate": f.get("delivery_estimate", ""),
            "return_risk": f.get("return_risk") or "Unknown",
            "trends_interest": num(f.get("trends_interest")),
            "image_reference": f.get("image_reference", ""),
            "notes": f.get("notes", ""),
        }
        r = pa.analyze(payload)
        payload["score"], payload["decision"] = r["score"], r["decision"]
        pid = db.add_product(payload)
        self._go("/products?ok=" + urllib.parse.quote(
            "Product #%d saved - score %s (%s)" % (pid, r["score"], r["decision"])))

    def _marketing(self, f):
        pid = f.get("product_id", "")
        product = db.get_product(int(pid)) if pid else None
        if not product:
            raise ValueError("Select a product first.")
        source = {"product_name": product.get("product_name"),
                  "selling_price": product.get("target_selling_price") or product.get("app_price"),
                  "verified_features": product.get("notes") or "",
                  "delivery_estimate": product.get("delivery_estimate") or "",
                  "cod_available": False}
        drafts = ai_content.generate_drafts(source)
        flash = ""
        if f.get("save") == "1":
            path = ai_content.save_drafts(source, drafts)
            flash = "<div class='ok'>Saved to %s</div>" % esc(os.path.relpath(path, BASE_DIR))
        self._send(v_marketing(flash=flash, drafts=drafts, product=product))

    def _status(self, f):
        oid = int(f["order_id"])
        current = next((o["order_status"] for o in db.list_orders() if o["id"] == oid), None)
        if current is None:
            raise ValueError("Order not found.")
        payout = num(f.get("realized_payout"), 0.0) or 0.0
        cm.change_status(oid, current, f["new_status"], payout or None)
        self._go("/orders?ok=" + urllib.parse.quote(
            "Order #%d moved to %s." % (oid, f["new_status"])))


def main():
    db.init_db()
    for folder in ("data", "generated_ads", "exports", "assets"):
        os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)

    server = None
    port = PORT
    for candidate in range(PORT, PORT + 12):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        print("Could not find a free port between %d and %d." % (PORT, PORT + 11))
        print("Close the other program using that range and try again.")
        return

    url = "http://localhost:%d" % port
    print("=" * 58)
    print(" Meesho AI Reselling Agent is running")
    print(" Open this in your browser:  %s" % url)
    print(" Stop it with Ctrl + C in this window")
    print("=" * 58)

    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()