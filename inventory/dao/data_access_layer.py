"""Inventory & POS service layer.

This module wraps common product and purchase-order operations with
simple database calls. It adds:

- Clear docstrings and inline comments
- Safer SQL (field whitelist for dynamic updates)
- Stricter typing hints
- More consistent return shapes (dicts instead of raw DB rows)
- Business-rule validations (e.g., non-negative quantities)
- Audit logging on write operations
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from datastructures import CustomList  # Thin wrapper over list (provided elsewhere)
from ..db.db import get_conn

# -----------------------------
# Utilities & audit logging
# -----------------------------

def now_str() -> str:
    """Return current UTC time as an RFC3339-like string with seconds precision.

    Example: ``2025-10-25T09:14:03Z``
    """
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def log(actor: str, action: str, entity_type: str, entity_id: Optional[int], details: str) -> None:
    """Insert an audit trail record.

    Parameters
    ----------
    actor: str
        Who performed the action (e.g., username or service name).
    action: str
        What happened (e.g., "create", "update", "sale").
    entity_type: str
        Domain entity type (e.g., "product", "purchase_order").
    entity_id: Optional[int]
        Identifier of the affected entity (if known at logging time).
    details: str
        Free-form description for debugging/trace.
    """
    with get_conn() as conn:
        conn.execute(
            (
                "INSERT INTO audit_log (actor, action, entity_type, entity_id, details, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            ),
            (actor, action, entity_type, entity_id, details, now_str()),
        )


# -----------------------------
# Products
# -----------------------------

# Whitelist of product fields that may be updated via the generic field setter.
# This prevents SQL injection on the dynamic column name.
_ALLOWED_PRODUCT_UPDATE_FIELDS = {
    "name",
    "category",
    "price",
    "min_price",
    "max_price",
    "quantity",
    "reorder_level",
    "is_active",
    "is_promo_active",
    "items_sold_count",
    "reviews_count",
    "discount_rate",
}


def create_product(
    actor: str,
    sku: str,
    name: str,
    category: str,
    price: float,
    min_price: float,
    max_price: float,
    quantity: int,
    reorder_level: int,
) -> int:
    """Create a new product row and return its primary key (``id``).

    Also logs an audit entry.
    """
    ts = now_str()
    with get_conn() as conn:
        cur = conn.execute(
            (
                """
                INSERT INTO products (
                    sku, name, category, price, min_price, max_price,
                    quantity, reorder_level, is_active, is_promo_active,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
                """
            ),
            (sku, name, category, price, min_price, max_price, quantity, reorder_level, ts, ts),
        )
        pid = int(cur.lastrowid)
    log(actor, "create", "product", pid, f"sku={sku}, name={name}, category={category}, quantity={quantity}, price={price}")
    return pid


def get_product_by_sku(sku: str) -> Optional[dict[str, Any]]:
    """Fetch a product by SKU, returning a plain ``dict`` or ``None`` if missing."""
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,))
        row = cur.fetchone()
        return dict(row) if row is not None else None


def update_product_field(actor: str, sku: str, field: str, value: Any) -> None:
    """Update a single product *field* to *value* for the product with *sku*.

    **Security:** ``field`` is validated against a strict whitelist to avoid
    SQL injection in the dynamic column position.
    """
    if field not in _ALLOWED_PRODUCT_UPDATE_FIELDS:
        raise ValueError(f"Unsupported or unsafe field: {field!r}")

    with get_conn() as conn:
        # Safe because *field* is validated; values are still parameterized.
        conn.execute(
            f"UPDATE products SET {field} = ?, updated_at = ? WHERE sku = ?",
            (value, now_str(), sku),
        )
    log(actor, "update", "product", None, f"sku={sku}, set {field}={value}")


def set_quantity(actor: str, sku: str, qty: int) -> None:
    """Set product quantity to an explicit non-negative number."""
    if qty < 0:
        raise ValueError("Quantity cannot be negative")
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET quantity = ?, updated_at = ? WHERE sku = ?",
            (qty, now_str(), sku),
        )
    log(actor, "set-qty", "product", None, f"sku={sku}, qty={qty}")


def adjust_quantity(actor: str, sku: str, delta: int) -> None:
    """Adjust product quantity by *delta* (positive or negative)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET quantity = quantity + ?, updated_at = ? WHERE sku = ?",
            (delta, now_str(), sku),
        )
    log(actor, "adjust-qty", "product", None, f"sku={sku}, delta={delta}")


def record_sale(actor: str, sku: str, qty: int) -> None:
    """Record a sale for *qty* units of the product *sku*.

    Decrements stock, increments ``items_sold_count``, and inserts into ``sales``.
    Validates: product exists, ``qty > 0``, and sufficient stock.
    """
    with get_conn() as conn:
        cur = conn.execute("SELECT id, price, quantity FROM products WHERE sku = ?", (sku,))
        row = cur.fetchone()
        if row is None:
            raise ValueError("Product not found")
        if qty <= 0:
            raise ValueError("Quantity must be positive")
        if row["quantity"] < qty:
            raise ValueError("Insufficient stock")

        new_qty = int(row["quantity"]) - qty
        now = now_str()

        conn.execute(
            "UPDATE products SET quantity = ?, items_sold_count = items_sold_count + ?, updated_at = ? WHERE id = ?",
            (new_qty, qty, now, row["id"]),
        )
        conn.execute(
            "INSERT INTO sales (product_id, quantity, price_at_sale, created_at) VALUES (?, ?, ?, ?)",
            (row["id"], qty, row["price"], now),
        )
    log(actor, "sale", "product", row["id"], f"sku={sku}, qty={qty}, new_qty={new_qty}")


def record_return(actor: str, sku: str, qty: int) -> None:
    """Record a return for *qty* units of the product *sku*.

    Increments stock and **decrements** ``items_sold_count`` (capped at 0).  A
    sale return should not increase the sold counter.
    """
    if qty <= 0:
        raise ValueError("Quantity must be positive")

    with get_conn() as conn:
        cur = conn.execute("SELECT id, quantity FROM products WHERE sku = ?", (sku,))
        row = cur.fetchone()
        if row is None:
            raise ValueError("Product not found")

        new_qty = int(row["quantity"]) + qty
        now = now_str()

        # Use MAX(..., 0) to avoid negative sold count on aggressive returns.
        conn.execute(
            """
            UPDATE products
            SET quantity = ?,
                items_sold_count = MAX(items_sold_count - ?, 0),
                updated_at = ?
            WHERE id = ?
            """,
            (new_qty, qty, now, row["id"]),
        )
    log(actor, "return", "product", row["id"], f"sku={sku}, qty={qty}, new_qty={new_qty}")


def list_products() -> CustomList[dict[str, Any]]:
    """Return all products as a ``CustomList`` of dicts, ordered by SKU."""
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM products ORDER BY sku")
        return CustomList([dict(r) for r in cur.fetchall()])


# -----------------------------
# Purchase Orders (POs)
# -----------------------------

def list_pos(status: Optional[str] = None) -> CustomList[dict[str, Any]]:
    """List purchase orders, optionally filtered by status.

    Returns a ``CustomList`` of PO dicts with ``sku`` joined in.
    """
    with get_conn() as conn:
        if status is not None:
            cur = conn.execute(
                (
                    "SELECT po.*, p.sku AS sku "
                    "FROM purchase_orders po JOIN products p ON p.id = po.product_id "
                    "WHERE status = ? ORDER BY po.id"
                ),
                (status,),
            )
        else:
            cur = conn.execute(
                (
                    "SELECT po.*, p.sku AS sku "
                    "FROM purchase_orders po JOIN products p ON p.id = po.product_id "
                    "ORDER BY po.id"
                )
            )
        return CustomList([dict(r) for r in cur.fetchall()])


def has_open_po(product_id: int) -> bool:
    """Return True if there is a draft/submitted PO for *product_id*."""
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM purchase_orders WHERE product_id = ? AND status IN ('draft','submitted')",
            (product_id,),
        )
        return cur.fetchone() is not None


def create_po(actor: str, product_id: int, qty: int) -> int:
    """Create a draft purchase order and return its id."""
    if qty <= 0:
        raise ValueError("Quantity must be positive")

    ts = now_str()
    with get_conn() as conn:
        cur = conn.execute(
            (
                "INSERT INTO purchase_orders (product_id, quantity, status, created_at, updated_at) "
                "VALUES (?, ?, 'draft', ?, ?)"
            ),
            (product_id, qty, ts, ts),
        )
        po_id = int(cur.lastrowid)
    log(actor, "create", "purchase_order", po_id, f"product_id={product_id}, qty={qty}")
    return po_id


def receive_po(actor: str, po_id: int, qty_received: Optional[int] = None) -> None:
    """Receive a PO, increasing product quantity and marking PO as received.

    If ``qty_received`` is ``None``, the full PO quantity is received.
    Validates existence, status, and positive received quantity.
    """
    with get_conn() as conn:
        po = conn.execute("SELECT * FROM purchase_orders WHERE id = ?", (po_id,)).fetchone()
        if po is None:
            raise ValueError("PO not found")
        if po["status"] == "received":
            raise ValueError("PO already received")

        product_id = int(po["product_id"])
        qty = int(po["quantity"]) if qty_received is None else int(qty_received)
        if qty <= 0:
            raise ValueError("Quantity must be positive")

        now = now_str()
        conn.execute(
            "UPDATE products SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
            (qty, now, product_id),
        )
        conn.execute(
            "UPDATE purchase_orders SET status = 'received', updated_at = ? WHERE id = ?",
            (now, po_id),
        )
    log(actor, "receive", "purchase_order", po_id, f"qty_received={qty}")


# -----------------------------
# Bulk setters
# -----------------------------

def set_reviews_count(actor: str, sku: str, count: int) -> None:
    """Set the absolute reviews count for a product by SKU."""
    if count < 0:
        raise ValueError("reviews_count cannot be negative")
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET reviews_count = ?, updated_at = ? WHERE sku = ?",
            (count, now_str(), sku),
        )
    log(actor, "set-reviews", "product", None, f"sku={sku}, reviews_count={count}")


def set_items_sold_count(actor: str, sku: str, count: int) -> None:
    """Set the absolute items_sold_count for a product by SKU."""
    if count < 0:
        raise ValueError("items_sold_count cannot be negative")
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET items_sold_count = ?, updated_at = ? WHERE sku = ?",
            (count, now_str(), sku),
        )
    log(actor, "set-sold", "product", None, f"sku={sku}, items_sold_count={count}")


def set_discount_rate(actor: str, sku: str, rate: float) -> None:
    """Set a discount rate in the [0.0, 1.0] range for a product by SKU."""
    if not (0.0 <= rate <= 1.0):
        raise ValueError("discount_rate must be between 0.0 and 1.0")
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET discount_rate = ?, updated_at = ? WHERE sku = ?",
            (rate, now_str(), sku),
        )
    log(actor, "set-discount", "product", None, f"sku={sku}, discount_rate={rate}")
