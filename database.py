"""
database.py - SQLite storage layer for the Meesho AI Reselling Agent.

Standard library only (sqlite3 / os / datetime).
Never store passwords, OTPs, or payment credentials in this database.
"""
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "meesho_agent.db")

ORDER_STATUSES = [
    "Inquiry",
    "Order Placed",
    "Dispatched",
    "Delivered",
    "Payout Received",
    "RTO In Transit",
    "RTO Delivered",
    "Customer Returned",
    "Cancelled",
]

PAID_STATUSES = ["Payout Received"]


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create every table if it does not exist yet. Safe to call repeatedly."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            product_link TEXT,
            category TEXT,
            app_price REAL,
            target_selling_price REAL,
            rating REAL,
            review_count INTEGER,
            reselling_margin REAL,
            delivery_estimate TEXT,
            return_risk TEXT DEFAULT 'Unknown',
            trends_interest REAL,
            image_reference TEXT,
            score REAL DEFAULT 0,
            decision TEXT DEFAULT '',
            notes TEXT,
            date_added TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            contact TEXT UNIQUE NOT NULL,
            channel TEXT DEFAULT 'WhatsApp',
            consent_status TEXT DEFAULT 'No',
            city TEXT,
            pincode TEXT,
            inquiry_date TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            customer_id INTEGER,
            meesho_order_ref TEXT,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            order_status TEXT DEFAULT 'Order Placed',
            margin_expected REAL DEFAULT 0,
            extra_cost REAL DEFAULT 0,
            realized_payout REAL DEFAULT 0,
            payout_date TEXT,
            notes TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            record_id INTEGER,
            event_time TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );
        """)
        conn.commit()


def log_event(conn, event_type, record_id=None, notes=""):
    conn.execute(
        "INSERT INTO activity_log (event_type, record_id, event_time, notes) "
        "VALUES (?,?,?,?)",
        (event_type, record_id, datetime.now().isoformat(timespec="seconds"), notes),
    )
    conn.commit()


# ------------------------------- products -------------------------------
def add_product(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO products (product_name, product_link, category, app_price,
                target_selling_price, rating, review_count, reselling_margin,
                delivery_estimate, return_risk, trends_interest, image_reference,
                score, decision, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            (data.get("product_name") or "").strip(),
            (data.get("product_link") or "").strip(),
            (data.get("category") or "").strip(),
            data.get("app_price") or 0,
            data.get("target_selling_price") or 0,
            data.get("rating"),
            data.get("review_count"),
            data.get("reselling_margin") or 0,
            data.get("delivery_estimate") or "",
            data.get("return_risk") or "Unknown",
            data.get("trends_interest"),
            data.get("image_reference") or "",
            data.get("score") or 0,
            data.get("decision") or "",
            data.get("notes") or "",
        ))
        pid = cur.lastrowid
        log_event(conn, "product_added", pid, data.get("product_name") or "")
        return pid


def list_products():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY score DESC, id DESC").fetchall()
        return [dict(r) for r in rows]


def get_product(product_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        return dict(row) if row else None


def update_product_score(product_id, score, decision):
    with get_connection() as conn:
        conn.execute("UPDATE products SET score=?, decision=? WHERE id=?",
                     (score, decision, product_id))
        log_event(conn, "product_scored", product_id, str(score))
        conn.commit()


def delete_product(product_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM orders WHERE product_id=?", (product_id,))
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        log_event(conn, "product_deleted", product_id)
        conn.commit()


# ------------------------------- customers ------------------------------
def add_customer(data: dict) -> int:
    """Insert or update customer, keyed on contact number."""
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO customers
            (customer_name, contact, channel, consent_status, city, pincode, notes)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(contact) DO UPDATE SET
                customer_name=excluded.customer_name,
                channel=excluded.channel,
                consent_status=excluded.consent_status,
                city=excluded.city,
                pincode=excluded.pincode,
                notes=excluded.notes
        """, (
            (data.get("customer_name") or "").strip(),
            str(data.get("contact") or "").strip(),
            data.get("channel") or "WhatsApp",
            data.get("consent_status") or "No",
            data.get("city") or "",
            data.get("pincode") or "",
            data.get("notes") or "",
        ))
        cid = cur.lastrowid
        log_event(conn, "customer_saved", cid, data.get("customer_name") or "")
        return cid


def list_customers():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM customers ORDER BY id DESC").fetchall()]


def consented_customers():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM customers WHERE consent_status='Yes' ORDER BY id DESC").fetchall()]


def delete_customer(customer_id):
    """Right to erasure - remove data no longer needed."""
    with get_connection() as conn:
        conn.execute("UPDATE orders SET customer_id=NULL WHERE customer_id=?",
                     (customer_id,))
        conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        log_event(conn, "customer_deleted", customer_id)
        conn.commit()


# -------------------------------- orders --------------------------------
def create_order(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO orders (product_id, customer_id, meesho_order_ref,
                order_status, margin_expected, extra_cost, realized_payout, notes)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            data.get("product_id"),
            data.get("customer_id"),
            data.get("meesho_order_ref") or "",
            data.get("order_status") or "Order Placed",
            data.get("margin_expected") or 0,
            data.get("extra_cost") or 0,
            data.get("realized_payout") or 0,
            data.get("notes") or "",
        ))
        oid = cur.lastrowid
        log_event(conn, "order_created", oid, data.get("meesho_order_ref") or "")
        return oid


def update_order_status(order_id, status, realized_payout=None):
    with get_connection() as conn:
        if realized_payout is None:
            conn.execute("UPDATE orders SET order_status=? WHERE id=?",
                         (status, order_id))
        else:
            stamp = (datetime.now().isoformat(timespec="seconds")
                     if status in PAID_STATUSES else None)
            conn.execute(
                "UPDATE orders SET order_status=?, realized_payout=?, payout_date=? "
                "WHERE id=?", (status, realized_payout, stamp, order_id))
        log_event(conn, "order_status_changed", order_id, status)
        conn.commit()


def list_orders():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT o.*, p.product_name, p.category, c.customer_name, c.contact
            FROM orders o
            LEFT JOIN products p ON p.id = o.product_id
            LEFT JOIN customers c ON c.id = o.customer_id
            ORDER BY o.id DESC
        """).fetchall()
        return [dict(r) for r in rows]


# -------------------------------- metrics -------------------------------
def dashboard_metrics() -> dict:
    with get_connection() as conn:
        products = conn.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]
        customers = conn.execute("SELECT COUNT(*) c FROM customers").fetchone()["c"]
        orders = conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]

        realized = conn.execute("""
            SELECT COALESCE(SUM(realized_payout - extra_cost), 0) s
            FROM orders WHERE order_status='Payout Received'
        """).fetchone()["s"]

        expected = conn.execute("""
            SELECT COALESCE(SUM(margin_expected - extra_cost), 0) s
            FROM orders WHERE order_status IN ('Order Placed','Dispatched','Delivered')
        """).fetchone()["s"]

        delivered = conn.execute("""
            SELECT COUNT(*) c FROM orders
            WHERE order_status IN ('Delivered','Payout Received')
        """).fetchone()["c"]

        lost = conn.execute("""
            SELECT COUNT(*) c FROM orders
            WHERE order_status IN ('RTO In Transit','RTO Delivered',
                                   'Customer Returned','Cancelled')
        """).fetchone()["c"]

        return {
            "products": products,
            "customers": customers,
            "orders": orders,
            "delivered": delivered,
            "lost": lost,
            "realized_profit": round(realized, 2),
            "expected_profit": round(expected, 2),
            "conversion_pct": round(orders / customers * 100, 1) if customers else 0.0,
            "rto_rate": round(lost / orders * 100, 1) if orders else 0.0,
        }


if __name__ == "__main__":
    init_db()
    print("Database ready at:", DB_PATH)
    print("Initial metrics:", dashboard_metrics())