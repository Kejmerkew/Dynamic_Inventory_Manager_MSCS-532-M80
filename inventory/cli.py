"""
Inventory Management Command-Line Interface (CLI)

This script exposes administrative operations for the inventory system
via subcommands. It ties together:
- Data access layer (CRUD operations)
- Business rules (reorder + dynamic pricing)
- Analytics/report generation

Usage examples:
    python -m inventory.cli init-db
    python -m inventory.cli add-product --sku P001 --name "Widget" --category Tools \
        --price 10 --min-price 8 --max-price 12 --quantity 50 --reorder-level 10
    python -m inventory.cli run-rules
    python -m inventory.cli export-csv --path report.csv
"""

import argparse
import os
import sys
import csv
import heapq

# Import modules from the project package
from .db.db import init_db
from .dao import data_access_layer
from .business import rules, analytics

# Default actor label for audit logging
ACTOR = "cli"


# -------------------------------------------------------------------
# Utility: pretty-print product rows
# -------------------------------------------------------------------
def print_products(rows):
    """Display product rows in a simple tabular layout."""
    if not rows:
        print("No products found.")
        return

    headers = [
        "id", "sku", "name", "category", "price", "min_price", "max_price",
        "quantity", "reorder_level", "is_active", "is_promo_active", "updated_at"
    ]
    print("  ".join(headers))
    for r in rows:
        print("  ".join(str(r.get(h, "")) for h in headers))


# -------------------------------------------------------------------
# Core command handlers
# -------------------------------------------------------------------

def cmd_init_db(args):
    """Initialize the SQLite database schema from schema.sql."""
    init_db()
    print("Database initialized.")


def cmd_add_product(args):
    """Add a new product record using user-provided details."""
    data_access_layer.create_product(
        ACTOR, args.sku, args.name, args.category,
        args.price, args.min_price, args.max_price,
        args.quantity, args.reorder_level
    )
    print("Product created.")


def cmd_list_products(args):
    """List all active products."""
    rows = data_access_layer.list_products()
    print_products(rows)


def cmd_set_qty(args):
    """Set absolute quantity for a given SKU."""
    data_access_layer.set_quantity(ACTOR, args.sku, args.qty)
    print("Quantity set.")


def cmd_sale(args):
    """Record a product sale event."""
    data_access_layer.record_sale(ACTOR, args.sku, args.qty)
    print("Sale recorded.")


def cmd_return(args):
    """Record a product return event."""
    data_access_layer.record_return(ACTOR, args.sku, args.qty)
    print("Return recorded.")


def cmd_set_price(args):
    """Update a product's current price."""
    data_access_layer.update_product_field(ACTOR, args.sku, "price", args.price)
    print("Price updated.")


def cmd_set_category(args):
    """Update a product's category."""
    data_access_layer.update_product_field(ACTOR, args.sku, "category", args.category)
    print("Category updated.")


# -------------------------------------------------------------------
# Business rule execution (reorder + dynamic pricing)
# -------------------------------------------------------------------
def cmd_run_rules(args):
    """Run reorder and dynamic pricing rules, showing summary of actions."""
    created = rules.run_reorder_rule(ACTOR)
    changes = rules.run_dynamic_pricing_rule(
        ACTOR,
        days=args.days,
        increase=args.increase,
        decrease=args.decrease,
        high_velocity=args.high_velocity,
        low_velocity=args.low_velocity,
        high_stock_multiplier=args.high_stock_mult
    )

    if created:
        print("Reorder POs created:")
        for sku, po_id, qty in created:
            print(f"  {sku}: PO {po_id} for qty {qty}")
    else:
        print("No reorder POs created.")

    if changes:
        print("Price changes:")
        for sku, old, new, reason in changes:
            print(f"  {sku}: {old} -> {new} ({reason})")
    else:
        print("No price changes.")


# -------------------------------------------------------------------
# Export and reporting
# -------------------------------------------------------------------
def cmd_export_csv(args):
    """Export the full product table to a CSV file."""
    rows = data_access_layer.list_products()
    with open(args.path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        if rows:
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    print(f"Exported {len(rows)} products to {args.path}")


def cmd_report(args):
    """Generate an insights report (CSV) using analytics metrics."""
    analytics.generate_report_csv(
        args.path,
        days=args.days,
        w_reviews=args.w_reviews,
        w_sold=args.w_sold,
        w_discount=args.w_discount
    )
    print(f"Report written to {args.path}")


# -------------------------------------------------------------------
# Data modification commands for counts and discounts
# -------------------------------------------------------------------
def cmd_set_reviews(args):
    """Manually set the reviews_count for a product."""
    data_access_layer.set_reviews_count(ACTOR, args.sku, args.count)
    print("reviews_count updated.")


def cmd_set_sold(args):
    """Manually set the items_sold_count for a product."""
    data_access_layer.set_items_sold_count(ACTOR, args.sku, args.count)
    print("items_sold_count updated.")


def cmd_set_discount(args):
    """Manually set the discount_rate (0.0–1.0) for a product."""
    data_access_layer.set_discount_rate(ACTOR, args.sku, args.rate)
    print("discount_rate updated.")


# -------------------------------------------------------------------
# Visualization helpers (heaps/queues)
# -------------------------------------------------------------------
def cmd_queues(args):
    """Display popularity and discount priority queues for debugging."""
    pop_heap = analytics.build_popularity_priority_queue(args.w_reviews, args.w_sold, args.w_discount)
    print("Popularity priority order (highest score first):")
    rank = 1
    tmp = pop_heap[:]
    while tmp:
        score_neg, p = heapq.heappop(tmp)
        print(
            f"  {rank}. {p['sku']} | {p['name']} | score={-score_neg:.4f} | "
            f"reviews={p.get('reviews_count',0)} | sold={p.get('items_sold_count',0)} | "
            f"discount={p.get('discount_rate',0.0):.2f}"
        )
        rank += 1

    disc_heap = analytics.build_discount_max_heap()
    print("Max heap by discount_rate (highest discount first):")
    rank = 1
    tmp = disc_heap[:]
    while tmp:
        disc_neg, p = heapq.heappop(tmp)
        print(f"  {rank}. {p['sku']} | {p['name']} | discount={-disc_neg:.2f}")
        rank += 1


# -------------------------------------------------------------------
# CLI parser setup
# -------------------------------------------------------------------
def build_parser():
    """Build the argparse command-line parser with subcommands."""
    p = argparse.ArgumentParser(prog="python -m inventory.cli", description="Inventory Management CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- database setup ---
    s = sub.add_parser("init-db", help="Initialize database schema")
    s.set_defaults(func=cmd_init_db)

    # --- product management ---
    s = sub.add_parser("add-product", help="Add a new product")
    s.add_argument("--sku", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--category", required=True)
    s.add_argument("--price", type=float, required=True)
    s.add_argument("--min-price", type=float, required=True)
    s.add_argument("--max-price", type=float, required=True)
    s.add_argument("--quantity", type=int, default=0)
    s.add_argument("--reorder-level", type=int, default=0)
    s.set_defaults(func=cmd_add_product)

    s = sub.add_parser("list-products", help="List products")
    s.set_defaults(func=cmd_list_products)

    # --- inventory adjustments ---
    s = sub.add_parser("set-qty", help="Set product quantity")
    s.add_argument("--sku", required=True)
    s.add_argument("--qty", type=int, required=True)
    s.set_defaults(func=cmd_set_qty)

    s = sub.add_parser("sale", help="Record a sale")
    s.add_argument("--sku", required=True)
    s.add_argument("--qty", type=int, required=True)
    s.set_defaults(func=cmd_sale)

    s = sub.add_parser("return", help="Record a return")
    s.add_argument("--sku", required=True)
    s.add_argument("--qty", type=int, required=True)
    s.set_defaults(func=cmd_return)

    # --- product updates ---
    s = sub.add_parser("set-price", help="Set product price")
    s.add_argument("--sku", required=True)
    s.add_argument("--price", type=float, required=True)
    s.set_defaults(func=cmd_set_price)

    s = sub.add_parser("set-category", help="Set product category")
    s.add_argument("--sku", required=True)
    s.add_argument("--category", required=True)
    s.set_defaults(func=cmd_set_category)

    # --- business rules ---
    s = sub.add_parser("run-rules", help="Run reorder & dynamic pricing rules")
    s.add_argument("--days", type=int, default=7)
    s.add_argument("--increase", type=float, default=0.05)
    s.add_argument("--decrease", type=float, default=0.05)
    s.add_argument("--high-velocity", type=float, default=5.0)
    s.add_argument("--low-velocity", type=float, default=1.0)
    s.add_argument("--high-stock-mult", type=float, default=2.0)
    s.set_defaults(func=cmd_run_rules)

    # --- exports & reports ---
    s = sub.add_parser("export-csv", help="Export product list to CSV")
    s.add_argument("--path", required=True)
    s.set_defaults(func=cmd_export_csv)

    s = sub.add_parser("report", help="Generate analytics report CSV")
    s.add_argument("--path", required=True)
    s.add_argument("--days", type=int, default=7)
    s.add_argument("--w-reviews", type=float, default=0.5)
    s.add_argument("--w-sold", type=float, default=0.4)
    s.add_argument("--w-discount", type=float, default=0.1)
    s.set_defaults(func=cmd_report)

    # --- data corrections ---
    s = sub.add_parser("set-sold", help="Set items_sold_count")
    s.add_argument("--sku", required=True)
    s.add_argument("--count", type=int, required=True)
    s.set_defaults(func=cmd_set_sold)

    s = sub.add_parser("set-reviews", help="Set reviews_count")
    s.add_argument("--sku", required=True)
    s.add_argument("--count", type=int, required=True)
    s.set_defaults(func=cmd_set_reviews)

    s = sub.add_parser("set-discount", help="Set discount_rate (0–1)")
    s.add_argument("--sku", required=True)
    s.add_argument("--rate", type=float, required=True)
    s.set_defaults(func=cmd_set_discount)

    # --- analytics queues ---
    s = sub.add_parser("queues", help="Display ranking queues")
    s.add_argument("--w-reviews", type=float, default=0.5)
    s.add_argument("--w-sold", type=float, default=0.4)
    s.add_argument("--w-discount", type=float, default=0.1)
    s.set_defaults(func=cmd_queues)

    return p


# -------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------
def main(argv=None):
    """CLI entry point when invoked via `python -m inventory.cli`."""
    argv = argv or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
