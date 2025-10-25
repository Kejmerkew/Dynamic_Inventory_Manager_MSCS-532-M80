import csv
from datastructures import CustomList, Dictionary
from typing import Any, Tuple
import heapq
from ..db.db import get_conn
from .rules import sales_velocity


# -----------------------------------------------------------
# Data access
# -----------------------------------------------------------
def _fetch_products() -> CustomList[Dictionary]:
    """Return all *active* products as a ``CustomList`` of dictionaries.

    The query selects only products with ``is_active = 1``. Wrapping the result
    in ``CustomList`` (rather than returning a bare list) keeps the API
    consistent with other parts of the codebase that expect this container.
    """
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM products WHERE is_active = 1")
        # Convert DB rows (e.g., sqlite3.Row) to plain dicts for portability.
        return CustomList([dict(r) for r in cur.fetchall()])


# -----------------------------------------------------------
# Scoring helpers
# -----------------------------------------------------------

def _min_max(values: list[float | int]) -> tuple[float, float]:
    """Return (min, max) for a sequence, or (0.0, 0.0) if empty.

    This is useful when normalizing metrics; an empty input should not raise.
    """
    if not values:
        return 0.0, 0.0
    return float(min(values)), float(max(values))


def _normalize(value: float | int, lo: float, hi: float) -> float:
    """Normalize ``value`` to [0, 1] given a [lo, hi] range.

    When ``hi <= lo`` (e.g., all inputs are equal), returns 0.0 to avoid
    division by zero. Casting to ``float`` ensures stable FP math.
    """
    if hi - lo <= 0:
        return 0.0
    return (float(value) - lo) / float(hi - lo)


# -----------------------------------------------------------
# Priority queues (heaps)
# -----------------------------------------------------------

def build_popularity_priority_queue(
    w_reviews: float, w_sold: float, w_discount: float
) -> CustomList[Tuple[float, Dictionary]]:
    """Build a max-priority queue of products by *popularity* score.

    Popularity score is a weighted blend of three normalized metrics:
        score = w_reviews * norm(reviews_count)
              + w_sold   * norm(items_sold_count)
              + w_discount * norm(discount_rate)

    Because Python's ``heapq`` implements a *min*-heap, we push ``-score`` so
    that larger scores pop first. Returns a ``CustomList`` of
    ``(-score, product_dict)`` pairs representing the heap array.
    """
    items = _fetch_products()

    # Collect raw metric vectors for normalization bounds.
    revs = [float(p.get("reviews_count", 0)) for p in items]
    solds = [float(p.get("items_sold_count", 0)) for p in items]
    discs = [float(p.get("discount_rate", 0.0)) for p in items]
    rmin, rmax = _min_max(revs)
    smin, smax = _min_max(solds)
    dmin, dmax = _min_max(discs)

    heap: list[Tuple[float, Dictionary]] = []
    for p in items:
        # Normalize each component to [0, 1] within cohort.
        nr = _normalize(float(p.get("reviews_count", 0)), rmin, rmax)
        ns = _normalize(float(p.get("items_sold_count", 0)), smin, smax)
        nd = _normalize(float(p.get("discount_rate", 0.0)), dmin, dmax)

        # Weighted linear combination.
        score = w_reviews * nr + w_sold * ns + w_discount * nd

        # ``heapq`` is min-heap; negate the score for max-priority behavior.
        heapq.heappush(heap, (-score, p))

    # Return the heap array; callers can copy it before destructive pops.
    return CustomList(heap)


def build_discount_max_heap() -> CustomList[Tuple[float, Dictionary]]:
    """Build a max-heap of products keyed by ``discount_rate``.

    Each entry is ``(-discount_rate, product_dict)`` so that the largest
    discount appears at the top (i.e., at index 0 of the heap array).
    """
    items = _fetch_products()
    heap: list[Tuple[float, Dictionary]] = []
    for p in items:
        disc = float(p.get("discount_rate", 0.0))
        heapq.heappush(heap, (-disc, p))  # negate to simulate max-heap
    return CustomList(heap)


# -----------------------------------------------------------
# Reporting
# -----------------------------------------------------------

def generate_report_csv(path: str, days: int, w_reviews: float, w_sold: float, w_discount: float) -> None:
    """Generate a CSV report with pricing, inventory, and popularity metrics.

    Columns include:
    - identifiers (sku, name, category)
    - pricing and discount bounds (price, min_price, max_price, discount_rate)
    - social proof / traction (reviews_count, items_sold_count)
    - inventory signals (quantity, reorder_level, low_stock flag)
    - performance metrics (sales_velocity_per_day)
    - ranks for popularity and discount magnitude

    Parameters
    ----------
    path : str
        Output file path for the CSV.
    days : int
        Window length for computing sales velocity (passed to ``sales_velocity``).
    w_reviews, w_sold, w_discount : float
        Weights for the popularity score blend.
    """
    products = _fetch_products()

    # ------------------------------
    # Precompute popularity ranks
    # ------------------------------
    pop_heap = build_popularity_priority_queue(w_reviews, w_sold, w_discount)
    pop_ranks: dict[str, Tuple[int, float]] = {}

    # Copy the heap array before popping; ``heappop`` mutates in-place.
    tmp = list(pop_heap)
    rank = 1
    while tmp:
        score_neg, p = heapq.heappop(tmp)
        pop_ranks[p["sku"]] = (rank, -score_neg)  # store 1-based rank and positive score
        rank += 1

    # ------------------------------
    # Precompute discount ranks
    # ------------------------------
    disc_heap = build_discount_max_heap()
    disc_ranks: dict[str, Tuple[int, float]] = {}

    tmp = list(disc_heap)
    rank = 1
    while tmp:
        disc_neg, p = heapq.heappop(tmp)
        disc_ranks[p["sku"]] = (rank, -disc_neg)  # larger discount -> higher rank
        rank += 1

    # ------------------------------
    # Assemble report rows
    # ------------------------------
    rows: list[dict[str, Any]] = []
    for p in products:
        sku = p["sku"]

        # Velocity is average daily units sold over the last `days`.
        v = sales_velocity(p["id"], days=days)

        # Flag low stock when at/below the reorder level (positive threshold).
        low_stock = int(p["quantity"] <= p["reorder_level"] and p["reorder_level"] > 0)

        # Lookup precomputed ranks/scores; default to (None, 0.0) when absent.
        pop_rank, pop_score = pop_ranks.get(sku, (None, None))
        disc_rank, disc_value = disc_ranks.get(sku, (None, None))

        rows.append(
            {
                "sku": sku,
                "name": p["name"],
                "category": p["category"],
                "price": p["price"],
                "min_price": p["min_price"],
                "max_price": p["max_price"],
                "discount_rate": p.get("discount_rate", 0.0),
                "reviews_count": p.get("reviews_count", 0),
                "items_sold_count": p.get("items_sold_count", 0),
                "quantity": p["quantity"],
                "reorder_level": p["reorder_level"],
                "low_stock": low_stock,
                "sales_velocity_per_day": round(v, 4),
                "popularity_rank": pop_rank,
                "popularity_score": round(pop_score if pop_score is not None else 0.0, 6),
                "discount_rank": disc_rank,
                "discount_value": round(disc_value if disc_value is not None else 0.0, 6),
            }
        )

    # ------------------------------
    # Write CSV
    # ------------------------------
    if not rows:
        # Emit a header-only file to signal "no data" cleanly to downstream tools.
        headers = [
            "sku",
            "name",
            "category",
            "price",
            "min_price",
            "max_price",
            "discount_rate",
            "reviews_count",
            "items_sold_count",
            "quantity",
            "reorder_level",
            "low_stock",
            "sales_velocity_per_day",
            "popularity_rank",
            "popularity_score",
            "discount_rank",
            "discount_value",
        ]
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        return

    # DictWriter accepts any iterable of fieldnames; using keys() preserves order.
    headers = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)
