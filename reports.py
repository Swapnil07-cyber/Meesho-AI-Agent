"""
reports.py - weekly report and CSV export, standard library only.

Everything here is derived from records you entered yourself.
No estimate is ever presented as a realised number.
"""
import csv
import os
from datetime import datetime, timedelta

import database as db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")


def weekly_summary(days=7):
    """Counts and profit for orders created in the last N days."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    orders = [o for o in db.list_orders() if (o.get("order_date") or "") >= cutoff]

    delivered = [o for o in orders
                 if o["order_status"] in ("Delivered", "Payout Received")]
    lost = [o for o in orders
            if o["order_status"] in ("RTO In Transit", "RTO Delivered",
                                     "Customer Returned", "Cancelled")]
    open_orders = [o for o in orders
                   if o["order_status"] in ("Inquiry", "Order Placed", "Dispatched")]

    realized = sum((o.get("realized_payout") or 0) - (o.get("extra_cost") or 0)
                   for o in orders if o["order_status"] == "Payout Received")
    pending = sum((o.get("margin_expected") or 0) - (o.get("extra_cost") or 0)
                  for o in open_orders)

    return {
        "period_days": days,
        "orders": len(orders),
        "delivered": len(delivered),
        "lost": len(lost),
        "open": len(open_orders),
        "realized_profit": round(realized, 2),
        "pending_profit": round(pending, 2),
        "rto_rate": round(len(lost) / len(orders) * 100, 1) if orders else 0.0,
    }


def product_performance():
    """Per-product delivered / lost counts and realised profit."""
    orders = db.list_orders()
    table = {}
    for o in orders:
        name = o.get("product_name") or "(deleted product)"
        row = table.setdefault(name, {"product": name, "orders": 0, "delivered": 0,
                                      "lost": 0, "realized_profit": 0.0})
        row["orders"] += 1
        if o["order_status"] in ("Delivered", "Payout Received"):
            row["delivered"] += 1
        if o["order_status"] in ("RTO In Transit", "RTO Delivered",
                                 "Customer Returned", "Cancelled"):
            row["lost"] += 1
        if o["order_status"] == "Payout Received":
            row["realized_profit"] += ((o.get("realized_payout") or 0)
                                       - (o.get("extra_cost") or 0))
    out = []
    for row in table.values():
        row["realized_profit"] = round(row["realized_profit"], 2)
        out.append(row)
    return sorted(out, key=lambda r: (-r["delivered"], -r["realized_profit"]))


def _write_csv(rows, columns, filename):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def export_products():
    return _write_csv(
        db.list_products(),
        ["id", "product_name", "category", "app_price", "target_selling_price",
         "reselling_margin", "rating", "review_count", "return_risk", "score",
         "decision", "date_added"],
        "products_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M%S"))


def export_orders():
    return _write_csv(
        db.list_orders(),
        ["id", "order_date", "product_name", "customer_name", "meesho_order_ref",
         "order_status", "margin_expected", "extra_cost", "realized_payout",
         "payout_date", "notes"],
        "orders_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M%S"))


def weekly_report_text(days=7):
    """Plain-text report, safe to paste into WhatsApp or a notes app."""
    s = weekly_summary(days)
    perf = product_performance()
    lines = [
        "MEESHO RESELLING - WEEKLY REPORT (%d days)" % s["period_days"],
        "Generated: %s" % datetime.now().strftime("%d %b %Y %H:%M"),
        "",
        "Orders this period : %s" % s["orders"],
        "Delivered          : %s" % s["delivered"],
        "Cancelled / RTO    : %s" % s["lost"],
        "Still open         : %s" % s["open"],
        "Realised profit    : Rs.%.2f" % s["realized_profit"],
        "Pending (not final): Rs.%.2f" % s["pending_profit"],
        "Loss rate          : %.1f%%" % s["rto_rate"],
        "",
        "TOP PRODUCTS",
    ]
    for row in perf[:5]:
        lines.append("  %s: %d delivered, %d lost, Rs.%.2f"
                     % (row["product"], row["delivered"], row["lost"],
                        row["realized_profit"]))
    if not perf:
        lines.append("  (no orders recorded yet)")
    return "\n".join(lines)


def generate_csv_report(db_path, export_dir):
    """Wrapper for intake_app.py compatibility. Exports products and orders CSV."""
    product_path = export_products()
    export_orders()
    return product_path


if __name__ == "__main__":
    print(weekly_report_text())