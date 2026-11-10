"""
profit_calculator.py - margin, expected value and break-even maths.

Two numbers are kept strictly separate, as the project guide requires:

  estimated net profit = expected margin - extra costs        (a hope)
  actual net profit    = realised payout - actual extra costs  (a fact)

Realised profit is only recognised after the order status and any return or
cancellation outcome are final. Cancelled and returned orders are never
counted as a sale.
"""

# Typical planning assumption. This is an input you control, not a fact.
DEFAULT_RTO_RATE = 0.22


def estimated_net_profit(expected_margin, extra_cost=0.0):
    return round(float(expected_margin or 0) - float(extra_cost or 0), 2)


def actual_net_profit(realized_payout, actual_extra_cost=0.0):
    return round(float(realized_payout or 0) - float(actual_extra_cost or 0), 2)


def margin_percent(app_price, selling_price):
    """Margin as a share of the price the customer actually pays."""
    if not selling_price:
        return 0.0
    return round((float(selling_price) - float(app_price)) / float(selling_price) * 100, 1)


def expected_value(expected_margin, extra_cost=0.0, rto_rate=DEFAULT_RTO_RATE):
    """Margin weighted by delivery success. Shows what an RTO really costs."""
    m = float(expected_margin or 0)
    c = float(extra_cost or 0)
    r = max(0.0, min(1.0, float(rto_rate)))
    return round(m * (1 - r) - c, 2)


def break_even_orders(fixed_cost, per_order_net):
    """How many delivered orders are needed to cover a fixed cost."""
    if per_order_net <= 0:
        return None
    return int(-(-float(fixed_cost) // float(per_order_net)))


def required_margin(app_price, target_net_profit, extra_cost=0.0):
    """Margin you must add on top of the app price to net a target profit."""
    return round(float(target_net_profit or 0) + float(extra_cost or 0), 2)


def suggest_selling_price(app_price, target_margin, extra_cost=0.0):
    """Selling price that delivers target_margin after extra costs."""
    return round(float(app_price) + required_margin(app_price, target_margin, extra_cost), 0)


def full_breakdown(app_price, selling_price, extra_cost=0.0,
                   rto_rate=DEFAULT_RTO_RATE, actual_payout=None):
    """One dictionary the dashboard and the CLI both use."""
    app_price = float(app_price or 0)
    selling_price = float(selling_price or 0)
    margin = round(selling_price - app_price, 2)
    out = {
        "app_price": app_price,
        "selling_price": selling_price,
        "margin": margin,
        "margin_percent": margin_percent(app_price, selling_price),
        "extra_cost": float(extra_cost or 0),
        "estimated_net_profit": estimated_net_profit(margin, extra_cost),
        "expected_value": expected_value(margin, extra_cost, rto_rate),
        "rto_rate_used": rto_rate,
    }
    if actual_payout is not None:
        out["actual_net_profit"] = actual_net_profit(actual_payout, extra_cost)
    return out


if __name__ == "__main__":
    example = full_breakdown(app_price=349, selling_price=499, extra_cost=20,
                             rto_rate=0.22)
    for key, value in example.items():
        print(f"{key}: {value}")
    print("Break-even orders for Rs.500 ad spend:",
          break_even_orders(500, example["expected_value"]))