#!/usr/bin/env python3
# intake_app.py — Meesho AI Reselling Agent (Standalone v3.0)
import os
import sys
import csv
import io
import json
import sqlite3
import html as html_module
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import database as db
import customer_manager as cm
import ai_content
import reports
import product_analyzer as pa
import profit_calculator as pc

DB_PATH = os.path.join(BASE_DIR, "data", "meesho_ai.db")
START_PORT = 8501

for folder in ("data", "generated_ads", "exports", "assets", "product_images"):
    os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_queue():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intake_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            category TEXT,
            app_price REAL,
            target_selling_price REAL,
            rating REAL,
            review_count INTEGER,
            reselling_margin REAL,
            delivery_estimate TEXT,
            return_risk TEXT,
            demand TEXT,
            notes TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def init_scheduler():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS post_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            platform TEXT,
            scheduled_at TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_all_products():
    return db.list_products()

def get_pending_intake():
    conn = get_db()
    rows = conn.execute("SELECT * FROM intake_queue WHERE status='pending' ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def get_product_by_id(pid):
    return db.get_product(int(pid)) if pid else None

def save_uploaded_images(product_id, file_items):
    saved = []
    for idx, (name, data) in enumerate(file_items[:3], 1):
        ext = os.path.splitext(name)[1].lower() or ".jpg"
        fname = f"product_{product_id}_{idx}{ext}"
        fpath = os.path.join(BASE_DIR, "product_images", fname)
        with open(fpath, "wb") as f:
            f.write(data)
        saved.append(fpath)
    return saved

def get_product_images(product_id):
    folder = os.path.join(BASE_DIR, "product_images")
    if not os.path.exists(folder):
        return []
    files = []
    for f in os.listdir(folder):
        if f.startswith(f"product_{product_id}_"):
            files.append(os.path.join(folder, f))
    return sorted(files)

def esc(s):
    return html_module.escape(str(s)) if s is not None else ""

def score_calc(p):
    return (
        (p.get("rating") or 0) * 10 +
        (p.get("reselling_margin") or 0) * 0.5 +
        (10 if (p.get("demand") or "").lower() == "high" else 5 if (p.get("demand") or "").lower() == "medium" else 0) -
        (10 if (p.get("return_risk") or "").lower() == "high" else 5 if (p.get("return_risk") or "").lower() == "medium" else 0)
    )

NAV = [
    ("/", "Dashboard"),
    ("/intake", "Intake"),
    ("/products", "Products"),
    ("/edit_products", "Edit Products"),
    ("/compare", "Compare"),
    ("/profit", "Profit"),
    ("/adstudio", "Ad Studio"),
    ("/scheduler", "Scheduler"),
    ("/marketing", "Marketing"),
    ("/customers", "Customers"),
    ("/orders", "Orders"),
    ("/reports", "Reports"),
    ("/guide", "Guide"),
]

CSS = """
body{margin:0;font-family:'Segoe UI',Arial,sans-serif;background:#f5f7fb;color:#1c2430;line-height:1.5}
header{background:linear-gradient(135deg,#0b2036,#1b3d63);color:#fff;padding:14px 20px}
header h1{margin:0;font-size:18px;font-weight:700}
header p{margin:3px 0 0;font-size:12px;color:#9fb3c8}
nav{background:#112c48;padding:0 10px;white-space:nowrap;overflow-x:auto;border-bottom:1px solid rgba(255,255,255,0.08)}
nav a{display:inline-block;color:#dfeaf8;text-decoration:none;padding:12px 14px;font-size:13px;border-bottom:3px solid transparent}
nav a:hover{color:#fff}
nav a.on{color:#fff;border-bottom-color:#f0a726;background:rgba(240,167,38,0.08)}
main{max-width:1000px;margin:0 auto;padding:20px 16px 50px}
h2{font-size:19px;margin:0 0 3px}
.sub{color:#5c6b7d;font-size:12.5px;margin:0 0 14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}
.card{background:#fff;padding:16px;border-radius:9px;box-shadow:0 2px 8px rgba(0,0,0,0.06);text-align:center}
.card .k{font-size:11px;color:#5c6b7d;text-transform:uppercase}
.card .v{font-size:24px;font-weight:700;margin-top:4px;color:#2c3e50}
.panel{background:#fff;border-radius:9px;padding:16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,0.06)}
label{display:block;font-size:12px;font-weight:600;color:#34465c;margin:0 0 4px}
input,select,textarea{width:100%;padding:8px 10px;border:1px solid #c8d3df;border-radius:5px;font-size:13px;box-sizing:border-box;margin-bottom:10px}
textarea{min-height:60px;resize:vertical}
button,.btn{background:#2c3e50;color:#fff;border:0;border-radius:5px;padding:8px 16px;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block}
button:hover,.btn:hover{background:#1a252f}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #e8eef4}
th{background:#f7f9fc;font-size:11px;text-transform:uppercase;color:#5c6b7d}
.ok{background:#d4edda;color:#155724;padding:10px 14px;border-radius:5px;margin-bottom:12px;font-size:13px;border-left:4px solid #28a745}
.err{background:#f8d7da;color:#721c24;padding:10px 14px;border-radius:5px;margin-bottom:12px;font-size:13px;border-left:4px solid #dc3545}
.warn{background:#fff3cd;color:#856404;padding:10px 14px;border-radius:5px;margin-bottom:12px;font-size:13px;border-left:4px solid #ffc107}
.info{background:#e7f3ff;color:#004085;padding:10px 14px;border-radius:5px;margin-bottom:12px;font-size:13px;border-left:4px solid #2b6cb0}
.muted{color:#5c6b7d;font-size:12px}
footer{text-align:center;color:#8595a8;font-size:11.5px;padding:18px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
@media(max-width:700px){.grid2{grid-template-columns:1fr}}
"""

def render_page(title, body, active="/"):
    links = "".join(
        '<a href="%s" class="%s">%s</a>' % (path, "on" if path == active else "", label)
        for path, label in NAV
    )
    return """<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>%s - Meesho AI Reselling Agent</title>
<style>%s</style>
</head>
<body>
<header><h1>Meesho AI Reselling Agent</h1><p>Local only. Manual verification. Human approval at every step.</p></header>
<nav>%s</nav>
<main>
<h2>%s</h2>
<div class="sub">%s</div>
%s
</main>
<footer>A practical build, not a guarantee of income.</footer>
</body>
</html>""" % (esc(title), CSS, links, esc(title), "Select a page from the menu above." if active == "/" else "", body)

# ============================================================
# PAGE HANDLERS
# ============================================================

def dashboard_page(query="", flash=""):
    products = get_all_products()
    total = len(products)
    pending = len(get_pending_intake())
    
    cats = {}
    margins = []
    for p in products:
        c = p.get("category") or "Uncategorized"
        cats[c] = cats.get(c, 0) + 1
        if p.get("reselling_margin"):
            margins.append(p["reselling_margin"])
    avg_margin = sum(margins) / len(margins) if margins else 0
    
    top = sorted([p for p in products if p.get("reselling_margin")], key=lambda x: x.get("reselling_margin") or 0, reverse=True)[:5]
    
    conn = get_db()
    scheduled = conn.execute("SELECT * FROM post_schedule WHERE status='scheduled' ORDER BY scheduled_at LIMIT 5").fetchall()
    conn.close()
    
    orders = db.list_orders()
    pending_orders = [o for o in orders if o.get("order_status") in ("Inquiry", "Order Placed", "Dispatched")]
    
    cards_html = '<div class="cards">'
    cards_html += '<div class="card"><div class="k">Total Products</div><div class="v">%d</div></div>' % total
    cards_html += '<div class="card"><div class="k">Pending Intake</div><div class="v">%d</div></div>' % pending
    cards_html += '<div class="card"><div class="k">Avg Margin</div><div class="v">Rs.%.0f</div></div>' % avg_margin
    cards_html += '<div class="card"><div class="k">Scheduled Posts</div><div class="v">%d</div></div>' % len(scheduled)
    cards_html += '</div>'
    
    cat_html = ""
    for c, count in sorted(cats.items(), key=lambda x: -x[1])[:6]:
        cat_html += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eee;"><span>%s</span><span style="font-weight:600;">%d</span></div>' % (esc(c), count)
    
    top_html = ""
    for p in top:
        top_html += '<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee;"><span>%s</span><span style="color:#27ae60;font-weight:600;">Rs.%s</span></div>' % (esc(p.get("product_name","")[:35]), p.get("reselling_margin") or 0)
    
    sched_html = ""
    for s in scheduled:
        prod = get_product_by_id(s["product_id"])
        pname = prod.get("product_name","")[:30] if prod else "Product #%s" % s["product_id"]
        sched_html += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eee;"><span>%s</span><span style="color:#666;font-size:12px;">%s</span></div>' % (esc(pname), esc(s["scheduled_at"]))
    if not sched_html:
        sched_html = '<p class="muted">No upcoming posts.</p>'
    
    order_html = ""
    for o in pending_orders[:5]:
        order_html += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #eee;"><span>%s</span><span style="color:#e74c3c;font-size:12px;">%s</span></div>' % (esc(o.get("customer_name","Unknown")), esc(o.get("order_status","pending")))
    if not order_html:
        order_html = '<p class="muted">No pending orders.</p>'
    
    body = flash + cards_html + """
    <div class="grid2">
        <div class="panel"><h4 style="margin-top:0;">Category Breakdown</h4>%s</div>
        <div class="panel"><h4 style="margin-top:0;">Top 5 by Margin</h4>%s</div>
        <div class="panel"><h4 style="margin-top:0;">Upcoming Posts</h4>%s</div>
        <div class="panel"><h4 style="margin-top:0;">Pending Orders</h4>%s</div>
    </div>
    """ % (cat_html, top_html, sched_html, order_html)
    
    return render_page("Dashboard", body, "/")

def intake_page(query="", flash=""):
    if query:
        # Parse form data from query string for GET redirects
        pass
    
    pending = get_pending_intake()
    
    rows = ""
    for row in pending:
        rows += """<tr>
            <td>%s</td>
            <td>%s</td>
            <td>Rs.%s</td>
            <td>Rs.%s</td>
            <td>%s</td>
            <td>
                <form method="POST" action="/intake" style="display:inline;">
                    <input type="hidden" name="action" value="approve">
                    <input type="hidden" name="id" value="%s">
                    <button type="submit" style="background:#27ae60;font-size:12px;padding:6px 12px;">Approve</button>
                </form>
                <form method="POST" action="/intake" style="display:inline;margin-left:6px;">
                    <input type="hidden" name="action" value="reject">
                    <input type="hidden" name="id" value="%s">
                    <button type="submit" style="background:#e74c3c;font-size:12px;padding:6px 12px;">Reject</button>
                </form>
            </td>
        </tr>""" % (esc(row["product_name"][:40]), esc(row["category"] or "-"), row["app_price"] or 0, row["reselling_margin"] or 0, esc(row["demand"] or "-"), row["id"], row["id"])
    
    if not rows:
        rows = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#999;">No pending intake items.</td></tr>'
    
    body = flash + """
    <div class="panel">
        <h4 style="margin-top:0;">Add Single Product</h4>
        <form method="POST" action="/intake">
            <input type="hidden" name="action" value="add">
            <div class="grid2">
                <input type="text" name="product_name" placeholder="Product Name *" required>
                <input type="text" name="category" placeholder="Category">
                <input type="number" name="app_price" placeholder="App Price (Rs.)" step="0.01">
                <input type="number" name="target_selling_price" placeholder="Target Selling Price (Rs.)" step="0.01">
                <input type="number" name="rating" placeholder="Rating (0-5)" step="0.1" min="0" max="5">
                <input type="number" name="review_count" placeholder="Review Count">
                <input type="number" name="reselling_margin" placeholder="Margin (Rs.)" step="0.01">
                <input type="text" name="delivery_estimate" placeholder="Delivery (e.g. 3-5 days)">
                <select name="return_risk"><option value="">Return Risk</option><option value="Low">Low</option><option value="Medium">Medium</option><option value="High">High</option></select>
                <select name="demand"><option value="">Demand</option><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option></select>
            </div>
            <textarea name="notes" placeholder="Notes / Features"></textarea>
            <button type="submit">Add to Intake</button>
        </form>
    </div>
    
    <div class="panel">
        <h4 style="margin-top:0;">Bulk CSV Import</h4>
        <p class="muted">Paste CSV with columns: product_name, category, app_price, target_selling_price (or target_rate), rating, review_count, reselling_margin (or margin), delivery_estimate (or delivery), return_risk (or risk), demand, notes (or features)</p>
        <form method="POST" action="/intake">
            <input type="hidden" name="action" value="bulk_csv">
            <textarea name="csv_text" placeholder="product_name,category,app_price,target_selling_price,rating,review_count,reselling_margin,delivery_estimate,return_risk,demand,notes" style="height:100px;font-family:monospace;font-size:12px;"></textarea>
            <button type="submit" style="background:#8e44ad;">Import CSV</button>
        </form>
    </div>
    
    <div class="panel">
        <h4 style="margin-top:0;">Pending Review (%d items)</h4>
        <table>
            <tr><th>Product</th><th>Category</th><th>App Price</th><th>Margin</th><th>Demand</th><th>Action</th></tr>
            %s
        </table>
    </div>
    """ % (len(pending), rows)
    
    return render_page("Intake Queue", body, "/intake")

def products_page(flash=""):
    products = get_all_products()
    
    rows = ""
    for p in products:
        imgs = get_product_images(p.get("id"))
        img_tags = ""
        for img_path in imgs[:3]:
            rel_path = os.path.relpath(img_path, BASE_DIR).replace("\\", "/")
            img_tags += '<img src="/product_images/%s" style="width:50px;height:50px;object-fit:cover;border-radius:4px;margin-right:4px;border:1px solid #ddd;">' % esc(os.path.basename(img_path))
        
        score = score_calc(p)
        rows += """<tr>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>Rs.%s</td>
            <td>Rs.%s</td>
            <td>%s</td>
            <td>%.1f</td>
        </tr>""" % (img_tags, esc(p.get("product_name","")[:40]), esc(p.get("category") or "-"), p.get("app_price") or 0, p.get("reselling_margin") or 0, esc(p.get("demand") or "-"), score)
    
    if not rows:
        rows = '<tr><td colspan="7" style="padding:20px;text-align:center;color:#999;">No products yet. Add from Intake.</td></tr>'
    
    body = flash + """
    <div class="panel">
        <table>
            <tr><th>Photos</th><th>Product</th><th>Category</th><th>App Price</th><th>Margin</th><th>Demand</th><th>Score</th></tr>
            %s
        </table>
    </div>
    """ % rows
    
    return render_page("Products", body, "/products")

def edit_products_page(query="", flash=""):
    products = get_all_products()
    selected_pid = query.get("pid", [""])[0] if isinstance(query, dict) else ""
    if not selected_pid and isinstance(query, list):
        for item in query:
            if item.startswith("pid="):
                selected_pid = item.split("=")[1]
                break
    
    edit_form = ""
    if selected_pid:
        p = get_product_by_id(selected_pid)
        if p:
            imgs = get_product_images(p.get("id"))
            img_preview = ""
            for img_path in imgs[:3]:
                img_preview += '<img src="/product_images/%s" style="width:80px;height:80px;object-fit:cover;border-radius:6px;margin-right:8px;border:1px solid #ddd;">' % esc(os.path.basename(img_path))
            if not img_preview:
                img_preview = '<p class="muted">No photos yet.</p>'
            
            edit_form = """
            <div class="panel" style="background:#f8f9fa;">
                <h4 style="margin-top:0;">Edit: %s</h4>
                <div style="margin-bottom:16px;">
                    <label style="font-size:13px;color:#666;">Current Photos</label>
                    <div style="margin-top:8px;">%s</div>
                </div>
                <form method="POST" action="/edit_products">
                    <input type="hidden" name="action" value="update">
                    <input type="hidden" name="product_id" value="%s">
                    <div class="grid2">
                        <input type="text" name="product_name" value="%s" placeholder="Product Name">
                        <input type="text" name="category" value="%s" placeholder="Category">
                        <input type="number" name="app_price" value="%s" placeholder="App Price" step="0.01">
                        <input type="number" name="target_selling_price" value="%s" placeholder="Target Price" step="0.01">
                        <input type="number" name="rating" value="%s" placeholder="Rating" step="0.1" min="0" max="5">
                        <input type="number" name="review_count" value="%s" placeholder="Review Count">
                        <input type="number" name="reselling_margin" value="%s" placeholder="Margin" step="0.01">
                        <input type="text" name="delivery_estimate" value="%s" placeholder="Delivery">
                        <select name="return_risk">
                            <option value="">Risk</option>
                            <option value="Low" %s>Low</option>
                            <option value="Medium" %s>Medium</option>
                            <option value="High" %s>High</option>
                        </select>
                        <select name="demand">
                            <option value="">Demand</option>
                            <option value="High" %s>High</option>
                            <option value="Medium" %s>Medium</option>
                            <option value="Low" %s>Low</option>
                        </select>
                    </div>
                    <textarea name="notes" placeholder="Notes">%s</textarea>
                    <button type="submit" style="background:#27ae60;">Update Product</button>
                    <a href="/edit_products" style="background:#6c757d;color:#fff;text-decoration:none;padding:8px 16px;border-radius:5px;font-size:13px;margin-left:8px;display:inline-block;">Cancel</a>
                </form>
                
                <hr style="border:none;border-top:1px solid #dee2e6;margin:20px 0;">
                
                <h4>Upload Photos (up to 3)</h4>
                <form method="POST" action="/edit_products" enctype="multipart/form-data">
                    <input type="hidden" name="action" value="upload_photo">
                    <input type="hidden" name="product_id" value="%s">
                    <input type="file" name="photo_1" accept="image/*" style="display:block;margin-bottom:8px;">
                    <input type="file" name="photo_2" accept="image/*" style="display:block;margin-bottom:8px;">
                    <input type="file" name="photo_3" accept="image/*" style="display:block;margin-bottom:12px;">
                    <button type="submit" style="background:#8e44ad;font-size:13px;">Upload Photos</button>
                </form>
                
                <hr style="border:none;border-top:1px solid #dee2e6;margin:20px 0;">
                
                <form method="POST" action="/edit_products" onsubmit="return confirm('Delete this product?');">
                    <input type="hidden" name="action" value="delete">
                    <input type="hidden" name="product_id" value="%s">
                    <button type="submit" style="background:#e74c3c;font-size:13px;">Delete Product</button>
                </form>
            </div>
            """ % (
                esc(p.get("product_name","")[:40]), img_preview, p.get("id"),
                esc(p.get("product_name") or ""), esc(p.get("category") or ""), p.get("app_price") or 0,
                p.get("target_selling_price") or 0, p.get("rating") or 0, p.get("review_count") or 0,
                p.get("reselling_margin") or 0, esc(p.get("delivery_estimate") or ""),
                'selected' if (p.get("return_risk") or "").lower() == "low" else "",
                'selected' if (p.get("return_risk") or "").lower() == "medium" else "",
                'selected' if (p.get("return_risk") or "").lower() == "high" else "",
                'selected' if (p.get("demand") or "").lower() == "high" else "",
                'selected' if (p.get("demand") or "").lower() == "medium" else "",
                'selected' if (p.get("demand") or "").lower() == "low" else "",
                esc(p.get("notes") or ""), p.get("id"), p.get("id")
            )
    
    options = '<option value="">Select a product to edit</option>'
    for p in products:
        options += '<option value="%s" %s>%s</option>' % (p.get("id"), 'selected' if str(p.get("id")) == str(selected_pid) else "", esc(p.get("product_name","")[:50]))
    
    body = flash + """
    <div class="panel">
        <form method="GET" action="/edit_products">
            <select name="pid" onchange="this.form.submit()" style="max-width:400px;">
                %s
            </select>
        </form>
        %s
    </div>
    """ % (options, edit_form)
    
    return render_page("Edit Products", body, "/edit_products")

def compare_page(flash=""):
    products = get_all_products()
    compare_html = flash
    
    options = ""
    for p in products:
        name = esc(p.get("product_name","")[:60])
        cat = esc(p.get("category") or "Uncategorized")
        score = score_calc(p)
        options += """
        <label style="display:block;padding:8px 0;cursor:pointer;border-bottom:1px solid #eee;">
            <input type="checkbox" name="pid_%s" value="%s" style="margin-right:10px;transform:scale(1.2);">
            <span>%s (%s) - Score %.1f</span>
        </label>
        """ % (p.get("id"), p.get("id"), name, cat, score)
    
    body = compare_html + """
    <div class="panel">
        <h4 style="margin-top:0;">Select 2-3 products</h4>
        <form method="POST" action="/compare">
            <div style="max-height:300px;overflow-y:auto;border:1px solid #ddd;border-radius:6px;padding:10px;margin-bottom:15px;">
                %s
            </div>
            <button type="submit">Compare</button>
        </form>
    </div>
    """ % options
    
    return render_page("Compare Products", body, "/compare")

def compare_result_page(form_data, flash=""):
    selected_pids = []
    for key in form_data:
        if key.startswith("pid_"):
            pid_val = form_data.get(key)
            if pid_val and str(pid_val).isdigit():
                selected_pids.append(str(int(pid_val)))
    
    if len(selected_pids) < 2:
        return compare_page('<div class="warn"><strong>Select at least 2 products.</strong></div>')
    
    rows = [db.get_product(int(pid)) for pid in selected_pids]
    rows = [product for product in rows if product is not None]
    
    if len(rows) < 2:
        return compare_page('<div class="warn"><strong>Could not load selected products.</strong></div>')
    
    best = None
    best_score = -1
    for r in rows:
        score = score_calc(r)
        if score > best_score:
            best_score = score
            best = r
    
    headers = ["Attribute"] + [esc(r.get("product_name","")[:25]) for r in rows]
    attrs = [
        ("Category", lambda r: r.get("category") or "-"),
        ("App Price", lambda r: "Rs.%s" % r.get("app_price") if r.get("app_price") else "-"),
        ("Target Price", lambda r: "Rs.%s" % r.get("target_selling_price") if r.get("target_selling_price") else "-"),
        ("Margin", lambda r: "Rs.%s" % r.get("reselling_margin") if r.get("reselling_margin") else "-"),
        ("Rating", lambda r: "⭐ %s" % r.get("rating") if r.get("rating") else "-"),
        ("Reviews", lambda r: str(r.get("review_count") or 0)),
        ("Demand", lambda r: r.get("demand") or "-"),
        ("Return Risk", lambda r: r.get("return_risk") or "-"),
        ("Delivery", lambda r: r.get("delivery_estimate") or "-"),
    ]
    
    table_html = '<div style="overflow-x:auto;"><table style="border-collapse:collapse;font-size:14px;">'
    table_html += "<tr>"
    for h in headers:
        is_winner = best and h == esc(best.get("product_name","")[:25])
        bg = "#27ae60" if is_winner else "#34495e"
        table_html += '<th style="background:%s;color:#fff;padding:10px;border:1px solid #ddd;text-align:left;">%s</th>' % (bg, h)
    table_html += "</tr>"
    
    for label, fn in attrs:
        table_html += "<tr>"
        table_html += '<td style="padding:8px;border:1px solid #ddd;background:#f8f9fa;font-weight:600;">%s</td>' % label
        for r in rows:
            is_winner = best and r.get("id") == best.get("id")
            bg = "#d4edda" if is_winner else "#fff"
            table_html += '<td style="padding:8px;border:1px solid #ddd;background:%s;">%s</td>' % (bg, fn(r))
        table_html += "</tr>"
    
    table_html += "<tr>"
    table_html += '<td style="padding:8px;border:1px solid #ddd;background:#f8f9fa;font-weight:600;">AI Score</td>'
    for r in rows:
        is_winner = best and r.get("id") == best.get("id")
        bg = "#d4edda" if is_winner else "#fff"
        score = score_calc(r)
        crown = " 👑" if is_winner else ""
        table_html += '<td style="padding:8px;border:1px solid #ddd;background:%s;font-weight:700;color:#27ae60;">%.1f%s</td>' % (bg, score, crown)
    table_html += "</tr>"
    table_html += "</table></div>"
    
    winner_html = ""
    if best:
        winner_html = """
        <div class="ok" style="margin-top:20px;">
            <h4 style="margin:0 0 8px 0;">🏆 Winner: %s</h4>
            <p style="margin:0;font-size:14px;">Score: %.1f | Margin: Rs.%s | Rating: %s</p>
        </div>
        """ % (esc(best.get("product_name","")[:40]), best_score, best.get("reselling_margin") or 0, best.get("rating") or 0)
    
    body = table_html + winner_html + '<p><a href="/compare" class="btn">Compare Again</a></p>'
    return render_page("Compare Results", body, "/compare")

def profit_page(flash=""):
    products = get_all_products()
    
    options = '<option value="">Select Product</option>'
    for p in products:
        options += '<option value="%s">%s</option>' % (p.get("id"), esc(p.get("product_name","")[:50]))
    
    body = flash + """
    <div class="panel" style="max-width:500px;">
        <form method="POST" action="/profit">
            <select name="product_id">%s</select>
            <input type="number" name="app_price" placeholder="App Price (Rs.)" step="0.01">
            <input type="number" name="selling_price" placeholder="Selling Price (Rs.)" step="0.01">
            <input type="number" name="shipping" placeholder="Shipping Cost (Rs.)" step="0.01">
            <input type="number" name="packaging" placeholder="Packaging Cost (Rs.)" step="0.01">
            <input type="number" name="other_costs" placeholder="Other Costs (Rs.)" step="0.01">
            <button type="submit">Calculate</button>
        </form>
    </div>
    """ % options
    
    return render_page("Profit Calculator", body, "/profit")

def profit_result_page(form_data, flash=""):
    pid = form_data.get("product_id", "")
    product = get_product_by_id(pid) if pid else None
    
    app_price = float(form_data.get("app_price", product.get("app_price") if product else 0) or 0)
    selling_price = float(form_data.get("selling_price", product.get("target_selling_price") if product else 0) or 0)
    shipping = float(form_data.get("shipping", 0) or 0)
    packaging = float(form_data.get("packaging", 0) or 0)
    other = float(form_data.get("other_costs", 0) or 0)
    
    total_cost = app_price + shipping + packaging + other
    profit = selling_price - total_cost
    margin_pct = (profit / selling_price * 100) if selling_price > 0 else 0
    
    result = """
    <div class="ok">
        <h4 style="margin:0 0 12px 0;">Profit Calculation: %s</h4>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:14px;">
            <div>App Price:</div><div style="text-align:right;">Rs.%.2f</div>
            <div>Shipping:</div><div style="text-align:right;">Rs.%.2f</div>
            <div>Packaging:</div><div style="text-align:right;">Rs.%.2f</div>
            <div>Other Costs:</div><div style="text-align:right;">Rs.%.2f</div>
            <div style="border-top:1px solid #155724;padding-top:8px;font-weight:600;">Total Cost:</div>
            <div style="border-top:1px solid #155724;padding-top:8px;text-align:right;font-weight:600;">Rs.%.2f</div>
            <div>Selling Price:</div><div style="text-align:right;">Rs.%.2f</div>
            <div style="border-top:2px solid #155724;padding-top:8px;font-weight:700;">Net Profit:</div>
            <div style="border-top:2px solid #155724;padding-top:8px;text-align:right;font-weight:700;">Rs.%.2f</div>
            <div>Margin %%:</div><div style="text-align:right;font-weight:700;">%.1f%%</div>
        </div>
    </div>
    """ % (esc(product.get("product_name","")[:40]) if product else "Manual Entry", app_price, shipping, packaging, other, total_cost, selling_price, profit, margin_pct)
    
    body = result + '<p><a href="/profit" class="btn">Calculate Again</a></p>'
    return render_page("Profit Result", body, "/profit")

def adstudio_page(flash=""):
    products = get_all_products()
    
    options = '<option value="">Select Product</option>'
    for p in products:
        options += '<option value="%s">%s</option>' % (p.get("id"), esc(p.get("product_name","")[:50]))
    
    body = flash + """
    <div class="panel" style="max-width:600px;">
        <form method="POST" action="/adstudio">
            <select name="product_id">%s</select>
            <div style="margin-bottom:12px;">
                <label style="font-weight:400;"><input type="checkbox" name="save" value="1" style="width:auto;margin-right:6px;"> Save to file</label>
            </div>
            <button type="submit" name="generate" value="1" style="background:#8e44ad;">Generate Ad</button>
        </form>
    </div>
    """ % options
    
    return render_page("Ad Studio", body, "/adstudio")

def adstudio_result_page(form_data, flash=""):
    pid = form_data.get("product_id", "")
    product = get_product_by_id(pid) if pid else None
    
    if not product or not form_data.get("generate"):
        return adstudio_page('<div class="warn">Select a product and generate.</div>')
    
    source = {
        "product_name": product.get("product_name"),
        "selling_price": product.get("target_selling_price") or product.get("app_price"),
        "verified_features": product.get("notes") or "",
        "delivery_estimate": product.get("delivery_estimate") or "",
        "cod_available": False
    }
    drafts = ai_content.generate_drafts(source)
    
    flash_html = """
    <div class="ok">
        <h4 style="margin:0 0 8px 0;">Ad Generated for %s</h4>
        <div style="background:#fff;padding:12px;border-radius:6px;margin-bottom:10px;">
            <strong>WhatsApp Status:</strong><br>
            <pre style="white-space:pre-wrap;font-family:inherit;margin:8px 0;">%s</pre>
        </div>
        <div style="background:#fff;padding:12px;border-radius:6px;margin-bottom:10px;">
            <strong>Social Caption:</strong><br>
            <pre style="white-space:pre-wrap;font-family:inherit;margin:8px 0;">%s</pre>
        </div>
        <div style="background:#fff;padding:12px;border-radius:6px;">
            <strong>Customer Reply:</strong><br>
            <pre style="white-space:pre-wrap;font-family:inherit;margin:8px 0;">%s</pre>
        </div>
    </div>
    """ % (esc(product.get("product_name","")[:40]), esc(drafts.get("whatsapp_status","")), esc(drafts.get("social_caption","")), esc(drafts.get("customer_reply","")))
    
    if form_data.get("save") == "1":
        saved_path = ai_content.save_drafts(source, drafts)
        fname = os.path.basename(saved_path)
        flash_html += '<div class="info" style="margin-top:12px;">Saved: %s</div>' % esc(fname)
    
    body = flash_html + '<p><a href="/adstudio" class="btn">Generate Another</a></p>'
    return render_page("Ad Generated", body, "/adstudio")

def scheduler_page(flash=""):
    products = get_all_products()
    
    conn = get_db()
    scheduled = conn.execute("SELECT * FROM post_schedule ORDER BY scheduled_at DESC").fetchall()
    conn.close()
    
    rows = ""
    for s in scheduled:
        prod = get_product_by_id(s["product_id"])
        pname = prod.get("product_name","")[:30] if prod else "Product #%s" % s["product_id"]
        rows += """<tr>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>
                <form method="POST" action="/scheduler" style="display:inline;">
                    <input type="hidden" name="action" value="delete">
                    <input type="hidden" name="id" value="%s">
                    <button type="submit" style="background:#e74c3c;font-size:12px;padding:6px 12px;">Delete</button>
                </form>
            </td>
        </tr>""" % (esc(pname), esc(s["platform"] or "-"), esc(s["scheduled_at"]), esc(s["status"]), s["id"])
    if not rows:
        rows = '<tr><td colspan="5" style="padding:20px;text-align:center;color:#999;">No scheduled posts.</td></tr>'
    
    options = '<option value="">Select Product</option>'
    for p in products:
        options += '<option value="%s">%s</option>' % (p.get("id"), esc(p.get("product_name","")[:50]))
    
    body = flash + """
    <div class="panel" style="max-width:500px;">
        <form method="POST" action="/scheduler">
            <input type="hidden" name="action" value="schedule">
            <select name="product_id">%s</select>
            <select name="platform">
                <option value="">Select Platform</option>
                <option value="WhatsApp">WhatsApp</option>
                <option value="Facebook">Facebook</option>
                <option value="Instagram">Instagram</option>
                <option value="Telegram">Telegram</option>
            </select>
            <input type="datetime-local" name="scheduled_at">
            <button type="submit">Schedule Post</button>
        </form>
    </div>
    
    <div class="panel">
        <h4 style="margin-top:0;">Scheduled Posts</h4>
        <table>
            <tr><th>Product</th><th>Platform</th><th>Date/Time</th><th>Status</th><th>Action</th></tr>
            %s
        </table>
    </div>
    """ % (options, rows)
    
    return render_page("Post Scheduler", body, "/scheduler")

def marketing_page(flash=""):
    products = get_all_products()
    
    top = sorted([p for p in products if p.get("reselling_margin")], key=lambda x: score_calc(x), reverse=True)[:5]
    
    top_cards = ""
    for p in top:
        top_cards += """
        <div style="background:#fff;padding:16px;border-radius:8px;border:1px solid #e9ecef;margin-bottom:10px;">
            <div style="font-weight:600;">%s</div>
            <div style="font-size:13px;color:#666;margin-top:4px;">Margin: Rs.%s | Score: %.1f</div>
        </div>
        """ % (esc(p.get("product_name","")[:40]), p.get("reselling_margin") or 0, score_calc(p))
    
    if not top_cards:
        top_cards = '<p class="muted">No products yet.</p>'
    
    body = flash + """
    <div class="panel">
        <h4 style="margin-top:0;">🔥 Top 5 Products to Promote</h4>
        %s
    </div>
    
    <div class="warn">
        <h4 style="margin:0 0 8px 0;">Marketing Tips</h4>
        <ul style="margin:0;font-size:14px;padding-left:18px;">
            <li>Post between 7-9 PM for maximum engagement</li>
            <li>Use product photos with white background</li>
            <li>Add price and "Free Delivery" in every post</li>
            <li>Reply to comments within 30 minutes</li>
            <li>Post 3-5 products per day consistently</li>
        </ul>
    </div>
    """ % top_cards
    
    return render_page("Marketing", body, "/marketing")

def customers_page(flash=""):
    body = flash + """
    <div class="panel" style="max-width:500px;">
        <form method="POST" action="/customers">
            <input type="hidden" name="action" value="add">
            <input type="text" name="name" placeholder="Customer Name *" required>
            <input type="text" name="phone" placeholder="Phone">
            <input type="email" name="email" placeholder="Email">
            <textarea name="address" placeholder="Address" style="height:60px;"></textarea>
            <input type="text" name="source" placeholder="Source (e.g. WhatsApp, Facebook)">
            <button type="submit">Add Customer</button>
        </form>
    </div>
    """
    
    customers = db.list_customers()
    rows = ""
    for c in customers:
        rows += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            esc(c.get("customer_name","")), esc(c.get("contact","")), esc(c.get("email","") or "-"), esc(c.get("channel","") or "-")
        )
    if not rows:
        rows = '<tr><td colspan="4" style="padding:20px;text-align:center;color:#999;">No customers yet.</td></tr>'
    
    body += """
    <div class="panel">
        <h4 style="margin-top:0;">Customer List</h4>
        <table>
            <tr><th>Name</th><th>Contact</th><th>Email</th><th>Source</th></tr>
            %s
        </table>
    </div>
    """ % rows
    
    return render_page("Customers", body, "/customers")

def orders_page(flash=""):
    products = get_all_products()
    customers = db.list_customers()
    
    cust_options = '<option value="">Select Customer</option>'
    for c in customers:
        cust_options += '<option value="%s">%s</option>' % (c.get("id"), esc(c.get("customer_name","")))
    
    prod_options = '<option value="">Select Product</option>'
    for p in products:
        prod_options += '<option value="%s">%s</option>' % (p.get("id"), esc(p.get("product_name","")[:40]))
    
    body = flash + """
    <div class="panel" style="max-width:500px;">
        <form method="POST" action="/orders">
            <input type="hidden" name="action" value="add">
            <select name="customer_id">%s</select>
            <select name="product_id">%s</select>
            <input type="number" name="quantity" placeholder="Quantity" value="1" min="1">
            <input type="number" name="selling_price" placeholder="Selling Price (Rs.)" step="0.01">
            <select name="status">
                <option value="pending">Pending</option>
                <option value="confirmed">Confirmed</option>
                <option value="shipped">Shipped</option>
                <option value="delivered">Delivered</option>
            </select>
            <button type="submit">Add Order</button>
        </form>
    </div>
    """ % (cust_options, prod_options)
    
    orders = db.list_orders()
    rows = ""
    for o in orders:
        rows += "<tr><td>%s</td><td>%s</td><td>%s</td><td>Rs.%s</td><td>%s</td></tr>" % (
            esc(o.get("customer_name","Unknown")), esc(o.get("product_name","Unknown")), o.get("quantity",1),
            o.get("selling_price",0), esc(o.get("order_status","pending"))
        )
    if not rows:
        rows = '<tr><td colspan="5" style="padding:20px;text-align:center;color:#999;">No orders yet.</td></tr>'
    
    body += """
    <div class="panel">
        <h4 style="margin-top:0;">Order List</h4>
        <table>
            <tr><th>Customer</th><th>Product</th><th>Qty</th><th>Price</th><th>Status</th></tr>
            %s
        </table>
    </div>
    """ % rows
    
    return render_page("Orders", body, "/orders")

def reports_page(flash=""):
    body = flash + """
    <div class="panel" style="max-width:400px;">
        <form method="POST" action="/reports">
            <input type="hidden" name="action" value="export">
            <button type="submit">Export CSV Report</button>
        </form>
    </div>
    """
    return render_page("Reports", body, "/reports")

def guide_page():
    body = """
    <div class="panel">
        <h3>How to Use Meesho AI Reselling Agent</h3>
        <h4>1. Intake</h4><p>Add products from Meesho manually or paste CSV data. Approve good products to add them to your catalog.</p>
        <h4>2. Products</h4><p>View all approved products with photos, margins, and AI scores.</p>
        <h4>3. Edit Products</h4><p>Update product details, upload up to 3 photos per product.</p>
        <h4>4. Compare</h4><p>Select 2-3 products to compare side-by-side. The winner is auto-highlighted based on rating, margin, demand, and return risk.</p>
        <h4>5. Profit Calculator</h4><p>Calculate net profit after app price, shipping, packaging, and other costs.</p>
        <h4>6. Ad Studio</h4><p>Generate ad copy for any product. Save to file for manual posting.</p>
        <h4>7. Scheduler</h4><p>Plan your posts for WhatsApp, Facebook, Instagram, or Telegram. This is a reminder planner only.</p>
        <h4>8. Marketing</h4><p>See top 5 recommended products to promote based on AI score.</p>
        <h4>9. Customers & Orders</h4><p>Track who bought what and order status.</p>
        <h4>10. Reports</h4><p>Export all data to CSV for Excel analysis.</p>
    </div>
    """
    return render_page("Guide", body, "/guide")

# ============================================================
# HTTP HANDLER
# ============================================================

class Handler(BaseHTTPRequestHandler):
    server_version = "MeeshoAgent/3.0"
    
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
        return urllib.parse.parse_qs(raw, keep_blank_values=True)
    
    def _parse_form_single(self):
        """Return dict with single values (not lists)"""
        d = self._form()
        return {k: v[0] if len(v) == 1 else v for k, v in d.items()}
    
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        
        try:
            if u.path == "/":
                self._send(dashboard_page())
            elif u.path == "/intake":
                self._send(intake_page())
            elif u.path == "/products":
                self._send(products_page())
            elif u.path == "/edit_products":
                self._send(edit_products_page(q))
            elif u.path == "/compare":
                self._send(compare_page())
            elif u.path == "/profit":
                self._send(profit_page())
            elif u.path == "/adstudio":
                self._send(adstudio_page())
            elif u.path == "/scheduler":
                self._send(scheduler_page())
            elif u.path == "/marketing":
                self._send(marketing_page())
            elif u.path == "/customers":
                self._send(customers_page())
            elif u.path == "/orders":
                self._send(orders_page())
            elif u.path == "/reports":
                self._send(reports_page())
            elif u.path == "/guide":
                self._send(guide_page())
            elif u.path.startswith("/product_images/"):
                self._serve_file(u.path[1:])
            else:
                self._send(render_page("Not Found", '<div class="err">Page not found. <a href="/">Go to Dashboard</a></div>', ""), 404)
        except Exception as exc:
            self._send(render_page("Error", '<div class="err">%s: %s</div><p><a href="/">Back to Dashboard</a></p>' % (esc(type(exc).__name__), esc(exc))), 500)
    
    def _serve_file(self, rel_path):
        fpath = os.path.join(BASE_DIR, rel_path)
        if os.path.exists(fpath) and os.path.isfile(fpath):
            ext = os.path.splitext(fpath)[1].lower()
            ctype = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/gif" if ext == ".gif" else "application/octet-stream"
            with open(fpath, "rb") as f:
                self._send(f.read(), 200, ctype)
        else:
            self._send("Not found", 404)
    
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        f = self._parse_form_single()
        
        try:
            if u.path == "/intake":
                self._handle_intake(f)
            elif u.path == "/edit_products":
                self._handle_edit_products(f)
            elif u.path == "/compare":
                self._send(compare_result_page(f))
            elif u.path == "/profit":
                self._send(profit_result_page(f))
            elif u.path == "/adstudio":
                self._send(adstudio_result_page(f))
            elif u.path == "/scheduler":
                self._handle_scheduler(f)
            elif u.path == "/customers":
                self._handle_customers(f)
            elif u.path == "/orders":
                self._handle_orders(f)
            elif u.path == "/reports":
                self._handle_reports(f)
            else:
                self._go("/")
        except Exception as exc:
            self._send(render_page("Error", '<div class="err">%s: %s</div><p><a href="javascript:history.back()">Go Back</a></p>' % (esc(type(exc).__name__), esc(exc))), 500)
    
    def _handle_intake(self, f):
        action = f.get("action", "")
        
        if action == "add":
            conn = get_db()
            conn.execute("""
                INSERT INTO intake_queue 
                (product_name, category, app_price, target_selling_price, rating, review_count, reselling_margin, delivery_estimate, return_risk, demand, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f.get("product_name", ""),
                f.get("category", ""),
                float(f.get("app_price", 0) or 0),
                float(f.get("target_selling_price", 0) or 0),
                float(f.get("rating", 0) or 0),
                int(f.get("review_count", 0) or 0),
                float(f.get("reselling_margin", 0) or 0),
                f.get("delivery_estimate", ""),
                f.get("return_risk", ""),
                f.get("demand", ""),
                f.get("notes", ""),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            self._send(intake_page(flash='<div class="ok">Product added to intake queue.</div>'))
        
        elif action == "approve":
            pid = f.get("id", "")
            if pid:
                row = get_db().execute("SELECT * FROM intake_queue WHERE id = ?", (pid,)).fetchone()
                if row:
                    conn = get_db()
                    conn.execute("""
                        INSERT INTO products 
                        (product_name, category, app_price, target_selling_price, rating, review_count, reselling_margin, delivery_estimate, return_risk, demand, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row["product_name"], row["category"], row["app_price"], row["target_selling_price"],
                        row["rating"], row["review_count"], row["reselling_margin"], row["delivery_estimate"],
                        row["return_risk"], row["demand"], row["notes"], datetime.now().isoformat()
                    ))
                    conn.execute("UPDATE intake_queue SET status='approved' WHERE id = ?", (pid,))
                    conn.commit()
                    conn.close()
                    self._send(intake_page(flash='<div class="ok">Product approved and moved to Products.</div>'))
        
        elif action == "reject":
            pid = f.get("id", "")
            if pid:
                conn = get_db()
                conn.execute("UPDATE intake_queue SET status='rejected' WHERE id = ?", (pid,))
                conn.commit()
                conn.close()
                self._send(intake_page(flash='<div class="err">Product rejected.</div>'))
        
        elif action == "bulk_csv":
            csv_text = f.get("csv_text", "").strip()
            if csv_text:
                imported = 0
                reader = csv.DictReader(io.StringIO(csv_text))
                conn = get_db()
                for row in reader:
                    name = row.get("product_name", "")
                    cat = row.get("category", "")
                    app_price = float(row.get("app_price", 0) or 0)
                    tsp = row.get("target_selling_price", "") or row.get("target_rate", "") or row.get("selling_price", "") or "0"
                    rating = float(row.get("rating", 0) or 0)
                    rc = row.get("review_count", "") or "0"
                    margin = row.get("reselling_margin", "") or row.get("margin", "") or "0"
                    delivery = row.get("delivery_estimate", "") or row.get("delivery", "") or ""
                    risk = row.get("return_risk", "") or row.get("risk", "") or ""
                    demand = row.get("demand", "") or ""
                    notes = row.get("notes", "") or row.get("features", "") or ""
                    
                    if name:
                        conn.execute("""
                            INSERT INTO intake_queue 
                            (product_name, category, app_price, target_selling_price, rating, review_count, reselling_margin, delivery_estimate, return_risk, demand, notes, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            name, cat, app_price, float(tsp or 0), rating, int(float(rc or 0)),
                            float(margin or 0), delivery, risk, demand, notes, datetime.now().isoformat()
                        ))
                        imported += 1
                conn.commit()
                conn.close()
                self._send(intake_page(flash='<div class="ok">%d products imported from CSV.</div>' % imported))
        
        else:
            self._send(intake_page())
    
    def _handle_edit_products(self, f):
        action = f.get("action", "")
        pid = f.get("product_id", "")
        
        if action == "update" and pid:
            conn = get_db()
            conn.execute("""
                UPDATE products SET 
                    product_name = ?, category = ?, app_price = ?, target_selling_price = ?,
                    rating = ?, review_count = ?, reselling_margin = ?, delivery_estimate = ?,
                    return_risk = ?, demand = ?, notes = ?
                WHERE id = ?
            """, (
                f.get("product_name", ""),
                f.get("category", ""),
                float(f.get("app_price", 0) or 0),
                float(f.get("target_selling_price", 0) or 0),
                float(f.get("rating", 0) or 0),
                int(f.get("review_count", 0) or 0),
                float(f.get("reselling_margin", 0) or 0),
                f.get("delivery_estimate", ""),
                f.get("return_risk", ""),
                f.get("demand", ""),
                f.get("notes", ""),
                pid
            ))
            conn.commit()
            conn.close()
            self._send(edit_products_page(flash='<div class="ok">Product updated successfully.</div>'))
        
        elif action == "delete" and pid:
            conn = get_db()
            conn.execute("DELETE FROM products WHERE id = ?", (pid,))
            conn.commit()
            conn.close()
            self._send(edit_products_page(flash='<div class="err">Product deleted.</div>'))
        
        elif action == "upload_photo" and pid:
            self._send(edit_products_page(flash='<div class="warn">Photo upload requires multipart parsing. Copy photos to product_images/ folder manually with name: product_%s_1.jpg</div>' % pid))
        
        else:
            self._send(edit_products_page())
    
    def _handle_scheduler(self, f):
        action = f.get("action", "")
        
        if action == "schedule":
            conn = get_db()
            conn.execute("""
                INSERT INTO post_schedule (product_id, platform, scheduled_at, status, created_at)
                VALUES (?, ?, ?, 'scheduled', ?)
            """, (
                f.get("product_id", ""),
                f.get("platform", ""),
                f.get("scheduled_at", ""),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            self._send(scheduler_page(flash='<div class="ok">Post scheduled successfully.</div>'))
        
        elif action == "delete":
            conn = get_db()
            conn.execute("DELETE FROM post_schedule WHERE id = ?", (f.get("id", ""),))
            conn.commit()
            conn.close()
            self._send(scheduler_page(flash='<div class="err">Schedule deleted.</div>'))
        
        else:
            self._send(scheduler_page())
    
    def _handle_customers(self, f):
        if f.get("action") == "add":
            try:
                cm.save_customer(
                    f.get("name", ""),
                    f.get("phone", ""),
                    f.get("source", "WhatsApp"),
                    "No",
                    "",
                    "",
                    f.get("address", "")
                )
                self._send(customers_page(flash='<div class="ok">Customer added.</div>'))
            except ValueError as e:
                self._send(customers_page(flash='<div class="err">%s</div>' % esc(str(e))))
        else:
            self._send(customers_page())
    
    def _handle_orders(self, f):
        if f.get("action") == "add":
            try:
                db.create_order({
                    "customer_id": f.get("customer_id", ""),
                    "product_id": f.get("product_id", ""),
                    "quantity": int(f.get("quantity", 1) or 1),
                    "selling_price": float(f.get("selling_price", 0) or 0),
                    "order_status": f.get("status", "pending"),
                    "notes": ""
                })
                self._send(orders_page(flash='<div class="ok">Order added.</div>'))
            except Exception as e:
                self._send(orders_page(flash='<div class="err">%s</div>' % esc(str(e))))
        else:
            self._send(orders_page())
    
    def _handle_reports(self, f):
        if f.get("action") == "export":
            try:
                path = reports.export_products()
                fname = os.path.basename(path)
                self._send(reports_page(flash='<div class="ok">Report exported: <code>%s</code></div>' % esc(fname)))
            except Exception as e:
                self._send(reports_page(flash='<div class="err">%s</div>' % esc(str(e))))
        else:
            self._send(reports_page())

# ============================================================
# MAIN
# ============================================================

def main():
    db.init_db()
    init_queue()
    init_scheduler()
    for folder in ("data", "generated_ads", "exports", "assets", "product_images"):
        os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)
    
    server = None
    port = START_PORT
    for candidate in range(START_PORT, START_PORT + 12):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    
    if server is None:
        print("No free port found between %d and %d." % (START_PORT, START_PORT + 11))
        return
    
    print("=" * 50)
    print(" Meesho AI Reselling Agent v3.0")
    print(" Open: http://localhost:%d" % port)
    print(" Stop: Ctrl + C")
    print("=" * 50)
    
    try:
        import webbrowser
        webbrowser.open("http://localhost:%d" % port)
    except Exception:
        pass
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()

if __name__ == "__main__":
    main()