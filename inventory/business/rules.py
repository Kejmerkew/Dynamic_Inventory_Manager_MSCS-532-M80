import datetime
from ..db.db import get_conn
from ..dao.data_access_layer import now_str, log, has_open_po, create_po

def sales_velocity(product_id: int, days: int = 7) -> float:
    """
    Compute average daily sales velocity for a product over the past `days`.

    The velocity is defined as:
        (total quantity sold in the last `days`) / days

    Notes:
    - Uses UTC timestamps and assumes `sales.created_at` is an RFC3339-like string.
    - Returns 0.0 when no sales are found in the window.
    - Consider validating `days > 0` at the callsite if user input is involved.
    """
    # Cutoff timestamp: include sales from this instant backwards `days` days.
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat(timespec="seconds") + "Z"

    # Sum quantities sold for the product since the cutoff time.
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS qty "
            "FROM sales WHERE product_id = ? AND created_at >= ?",
            (product_id, cutoff),
        )
        total = cur.fetchone()["qty"]

    # Average per day (float division). Casting `days` guards against int division in older code.
    return total / float(days)


def calculate_order_quantity(current_qty: int, reorder_level: int, velocity: float, target_days: int = 14) -> int:
    """
    Decide how many units to order to cover `target_days` of sales, subject to `reorder_level`.

    Heuristic:
        needed = velocity * target_days            # projected demand window
        shortfall = needed - current_qty           # how many we’re short
        target = round(max(shortfall, reorder_level))
        return max(target, reorder_level)

    Notes:
    - The final `max(..., reorder_level)` duplicates the earlier constraint but preserves
      the original behavior (i.e., never order below `reorder_level`).
    - `velocity` is assumed to be non-negative.
    """
    target = int(round(max(velocity * target_days - current_qty, reorder_level)))
    return max(target, reorder_level)


def run_reorder_rule(actor: str):
    """
    Scan active products and create purchase orders when stock is at/below the reorder level.

    Rule:
    - Consider only active products.
    - If `quantity <= reorder_level` and there is no open PO (draft/submitted),
      compute 7-day sales velocity and create a PO to cover 14 days of demand.
    - Log each triggered reorder.

    Returns:
        List of tuples: (sku, po_id, qty_created)
    """
    created = []  # type: list[tuple[str, int, int]]

    # Fetch products once; use read-only connection context.
    with get_conn() as conn:
        products = conn.execute("SELECT * FROM products WHERE is_active = 1").fetchall()

    for p in products:
        # Only consider items with a positive reorder threshold and at/below threshold.
        if p["reorder_level"] > 0 and p["quantity"] <= p["reorder_level"]:
            # Skip if there is already a pending PO to avoid duplicates.
            if not has_open_po(p["id"]):
                # Simple 7-day moving average of sales.
                v = sales_velocity(p["id"], days=7)

                # Aim to stock enough for the next 14 days given current velocity.
                qty = calculate_order_quantity(p["quantity"], p["reorder_level"], v, target_days=14)

                # Create the PO and audit the action.
                po_id = create_po(actor, p["id"], qty)
                log(
                    actor,
                    "rule",
                    "product",
                    p["id"],
                    f"reorder triggered, velocity={v:.2f}, po_id={po_id}, qty={qty}",
                )

                created.append((p["sku"], po_id, qty))

    return created


def clamp(value: float, lo: float, hi: float) -> float:
    """
    Clamp `value` into the inclusive range [lo, hi].

    Example:
        clamp(1.2, 0.0, 1.0) -> 1.0
    """
    return max(lo, min(hi, value))


def run_dynamic_pricing_rule(
    actor: str,
    days: int,
    increase: float,
    decrease: float,
    high_velocity: float,
    low_velocity: float,
    high_stock_multiplier: float,
):
    """
    Adjust prices based on recent sales velocity and stock position while avoiding promo conflicts.

    Parameters:
        actor: Who runs the rule (for audit log).
        days: Window for computing sales velocity (e.g., 7 or 14).
        increase: Fractional markup (e.g., 0.10 for +10%) when demand is high and stock is low.
        decrease: Fractional markdown (e.g., 0.10 for −10%) when demand is low and stock is high.
        high_velocity: If velocity > high_velocity AND quantity < reorder_level, consider increasing price.
        low_velocity: If velocity < low_velocity AND quantity > high_stock, consider decreasing price.
        high_stock_multiplier: Multiplier for defining “high stock” as reorder_level * multiplier.

    Behavior:
        - Ignores products currently under promotions (`is_promo_active = 0` required).
        - New price is clamped between `min_price` and `max_price`.
        - Only persists changes ≥ $0.01 to avoid churn.
        - Each change is audited.

    Returns:
        List of tuples: (sku, old_price, new_price, reason)
    """
    changes = []  # type: list[tuple[str, float, float, str]]

    # Load active catalog snapshot.
    with get_conn() as conn:
        products = conn.execute("SELECT * FROM products WHERE is_active = 1").fetchall()

    for p in products:
        # Compute recent velocity per product.
        v = sales_velocity(p["id"], days=days)

        # Compute a “high stock” threshold. If reorder_level is 0, treat as 0.
        high_stock = p["reorder_level"] * high_stock_multiplier if p["reorder_level"] > 0 else 0

        new_price = None
        reason = None

        # Case 1: High demand + low stock (and not in promo) -> increase price within bounds.
        if p["reorder_level"] > 0 and p["quantity"] < p["reorder_level"] and v > high_velocity and not p["is_promo_active"]:
            new_price = clamp(round(p["price"] * (1.0 + increase), 2), p["min_price"], p["max_price"])
            reason = "High demand and low stock"

        # Case 2: Low demand + high stock (and not in promo) -> decrease price within bounds.
        elif p["quantity"] > high_stock and v < low_velocity and not p["is_promo_active"]:
            new_price = clamp(round(p["price"] * (1.0 - decrease), 2), p["min_price"], p["max_price"])
            reason = "Low demand and high stock"

        # Persist only meaningful changes (≥ $0.01 difference) to reduce noise.
        if new_price is not None and abs(new_price - p["price"]) >= 0.01:
            with get_conn() as conn:
                conn.execute(
                    "UPDATE products SET price = ?, updated_at = ? WHERE id = ?",
                    (new_price, now_str(), p["id"]),
                )

            # Audit and collect change for reporting.
            log(
                actor,
                "rule",
                "product",
                p["id"],
                f"dynamic price change from {p['price']} to {new_price} due to {reason}; v={v:.2f}",
            )
            changes.append((p["sku"], float(p["price"]), float(new_price), reason))

    return changes
