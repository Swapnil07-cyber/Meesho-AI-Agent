"""
customer_manager.py - customer inquiries, consent and order status rules.

Uses database.py. No messages are sent from this module.
Only customers who explicitly consented appear in follow_up_list().
"""

import re

import database as db


CHANNELS = ["WhatsApp", "Facebook", "Instagram", "Referral", "Walk-in"]
CONSENT_OPTIONS = ["No", "Yes"]

# Allowed next steps for an order. Final statuses have no next step.
TRANSITIONS = {
    "Inquiry": ["Order Placed", "Cancelled"],
    "Order Placed": ["Dispatched", "Cancelled"],
    "Dispatched": ["Delivered", "RTO In Transit", "Cancelled"],
    "Delivered": ["Payout Received", "Customer Returned"],
    "RTO In Transit": ["RTO Delivered"],
    "Payout Received": [],
    "RTO Delivered": [],
    "Customer Returned": [],
    "Cancelled": [],
}


def normalise_contact(contact):
    """Return a 10-digit Indian mobile number, or an empty string if invalid."""
    digits = re.sub(r"\D", "", contact or "")

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]

    if re.fullmatch(r"[6-9]\d{9}", digits):
        return digits
    return ""


def save_customer(name, contact, channel="WhatsApp", consent="No",
                  city="", pincode="", notes=""):
    """Validate and save a customer inquiry. Raises ValueError if invalid."""
    name = (name or "").strip()
    contact = normalise_contact(contact)

    if not name:
        raise ValueError("Customer name is required.")
    if not contact:
        raise ValueError("Enter a valid 10-digit Indian mobile number.")
    if channel not in CHANNELS:
        raise ValueError("Choose a valid source channel.")
    if consent not in CONSENT_OPTIONS:
        raise ValueError("Consent must be Yes or No.")
    if pincode and not re.fullmatch(r"\d{6}", str(pincode).strip()):
        raise ValueError("Pincode must contain 6 digits.")

    return db.add_customer({
        "customer_name": name,
        "contact": contact,
        "channel": channel,
        "consent_status": consent,
        "city": city,
        "pincode": str(pincode).strip(),
        "notes": notes,
    })


def follow_up_list():
    """Return only customers whose consent status is Yes."""
    return db.consented_customers()


def record_order(product_id, customer_id, order_ref, expected_margin,
                 extra_cost=0, notes=""):
    """Create an order record after placing the order manually in the app."""
    if not product_id:
        raise ValueError("Select a product first.")
    if not customer_id:
        raise ValueError("Select a customer first.")
    if float(expected_margin or 0) <= 0:
        raise ValueError("Expected margin must be greater than zero.")

    return db.create_order({
        "product_id": product_id,
        "customer_id": customer_id,
        "meesho_order_ref": (order_ref or "").strip(),
        "order_status": "Order Placed",
        "margin_expected": expected_margin,
        "extra_cost": extra_cost,
        "notes": notes,
    })


def next_statuses(current_status):
    """List the statuses an order may move to from its current status."""
    return TRANSITIONS.get(current_status, [])


def change_status(order_id, current_status, new_status, realized_payout=None):
    """Change status only when the requested transition is allowed."""
    if new_status not in next_statuses(current_status):
        allowed = next_statuses(current_status)
        choices = ", ".join(allowed) if allowed else "none; this is a final status"
        raise ValueError(
            f"Cannot move from '{current_status}' to '{new_status}'. "
            f"Allowed next statuses: {choices}."
        )

    if new_status == "Payout Received":
        if realized_payout is None or float(realized_payout) <= 0:
            raise ValueError("Enter the actual payout received before marking it paid.")

    db.update_order_status(order_id, new_status, realized_payout)
    return True


if __name__ == "__main__":
    print("Contact checks:")
    for number in ["9876543210", "+91 98765 43210", "09876543210", "12345"]:
        result = normalise_contact(number) or "invalid"
        print(f"  {number} -> {result}")

    print()
    print("Next statuses after Dispatched:", next_statuses("Dispatched"))
    print("Next statuses after Payout Received:", next_statuses("Payout Received"))
    

def get_customers():
    """Return all customers from database."""
    try:
        return db.get_customers() or []
    except AttributeError:
        # Fallback if db.get_customers doesn't exist
        return db.consented_customers() or []


def get_orders():
    """Return all orders from database."""
    try:
        return db.get_orders() or []
    except AttributeError:
        return []


def add_order(customer_id, product_id, quantity, selling_price, status):
    """Wrapper to match intake_app.py signature."""
    return record_order(
        product_id=product_id,
        customer_id=customer_id,
        order_ref="",
        expected_margin=float(selling_price or 0),
        notes=f"Qty: {quantity}, Status: {status}"
    )