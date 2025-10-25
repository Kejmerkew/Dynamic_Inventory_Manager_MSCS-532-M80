# Inventory (v0.1.0)

> A inventory management that showcases **manually implemented data structures** (singly linked list, hash map, dict wrapper, and a binary min-heap) used inside a realistic, SQLite-backed application.

---

## Contents

- [What this project does](#what-this-project-does)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Quickstart](#quickstart)
- [Command‑line usage](#command-line-usage)
- [Python API](#python-api)
- [How custom data structures are used](#how-custom-data-structures-are-used)
- [Database schema](#database-schema)
- [License](#license)

---

## What this project does

- Tracks **products** (SKU, name, category, price bounds, quantity, reorder level, promo flags).
- Records **sales**, **returns**, and **purchase orders (POs)** with simple audit logging.
- Applies **business rules**:
  - _Reorder_: create/flag POs when inventory falls below thresholds using recent **sales velocity**.
  - _Dynamic pricing_: gently move price toward `min_price`/`max_price` depending on demand signals.
- Generates **analytics** and CSV reports, and demonstrates **priority queues / heaps**.
- Uses your **own data structures** for practice and clarity.

---

## Project structure

```
inventory_project/
├─ inventory/                 # Python package
│  ├─ datastructures/         # Custom DS used by the app
│  │  ├─ custom_list.py       # CustomList[T] wrapper
│  │  ├─ linked_list.py       # Singly Linked List (for HashMap buckets)
│  │  ├─ hash_map.py          # Separate‑chaining HashMap[K,V]
│  │  ├─ dictionary.py        # Dict‑like facade backed by HashMap
│  │  └─ heap.py              # Binary MinHeap[T]
│  ├─ business/
│  │  ├─ rules.py             # reorder + dynamic pricing rules
│  │  └─ analytics.py         # reporting helpers, priority queues, CSV export
│  ├─ dao/
│  │  └─ data_access_layer.py # CRUD helpers + audit log
│  ├─ db/
│  │  └─ db.py                # SQLite connection + schema initialization
│  ├─ cli.py                  # CLI entrypoint (subcommands)
│  └─ main.py                 # `python -m inventory.main` delegates to CLI
├─ data/
│  └─ schema.sql              # Database schema (SQLite)
└─ tests/
   └─ ds_test.py              # Unit tests for custom DS
```

---

## Requirements

- **Python 3.9+**
- **SQLite 3** (bundled with Python on most platforms)

> Packaging is configured via **PEP 621** in `pyproject.toml` and the package name is `inventory`.

---

## Quickstart

```bash
# 1) Create and activate a virtual environment
python -m venv .venv
# macOS/Linux
source .venv/bin/activate

# 2) Install in editable mode (from the project root that contains pyproject.toml)
pip install -U pip
pip install -e .

# 3) Initialize the SQLite database (creates tables from data/schema.sql)
python -m inventory.cli init-db

# 4) Add a sample product
python -m inventory.cli add-product  --sku P001 --name "Widget" --category Tools  --price 10 --min-price 8 --max-price 12 --quantity 50 --reorder-level 10

# 5) Run business rules (reorder + dynamic pricing)
python -m inventory.cli run-rules

# 6) Export a CSV report
python -m inventory.cli export-csv --path report.csv
```

> Alternative entry: `python -m inventory.main ...` (it forwards to the CLI).

---

## Command-line usage

The CLI is organized as subcommands. The file `inventory/cli.py` contains usage examples like:

```text
python -m inventory.cli init-db
python -m inventory.cli add-product --sku P001 --name "Widget" --category Tools     --price 10 --min-price 8 --max-price 12 --quantity 50 --reorder-level 10
python -m inventory.cli run-rules
python -m inventory.cli export-csv --path report.csv
```

Based on the available service functions, the intended commands are:

- `init-db` — Initialize the database from `data/schema.sql`.
- `add-product` — Insert a new product (SKU, name, category, price/min/max, quantity, reorder level).
- `set-qty` — Set absolute quantity for a SKU.
- `adjust-qty` — Add or subtract quantity for a SKU.
- `record-sale` — Record a sale for a SKU (decrements stock).
- `record-return` — Record a return for a SKU (increments stock).
- `list-products` — Show products (useful for quick verification).
- `create-po` — Create a purchase order for a SKU.
- `receive-po` — Receive/close a purchase order and increment stock.
- `run-rules` — Execute reorder and dynamic pricing rules.
- `export-csv` — Write a CSV report to `--path`.

---

## Python API

Below are the key functions discovered in the codebase that back the CLI. You can import and call them directly:

### Database helpers (`inventory.db.db`)

- `get_conn, init_db`

### Data access layer (`inventory.dao.data_access_layer`)

- `now_str, log, create_product, get_product_by_sku, update_product_field, set_quantity, adjust_quantity, record_sale, record_return, list_products, list_pos, has_open_po, create_po, receive_po, set_reviews_count, set_items_sold_count, set_discount_rate`

Typical examples:

```python
from inventory.db.db import init_db, get_conn
from inventory.dao.data_access_layer import (
    create_product, set_quantity, adjust_quantity, record_sale,
    list_products, create_po, receive_po,
)

init_db()

create_product(
    sku="P001", name="Widget", category="Tools",
    price=10.0, min_price=8.0, max_price=12.0,
    quantity=50, reorder_level=10,
    actor="admin",
)

adjust_quantity(actor="admin", sku="P001", delta=-5)    # sold 5
record_sale(actor="pos1", sku="P001", quantity=1)       # one sale

for p in list_products():
    print(p)

po_id = create_po(actor="buyer", sku="P001", quantity=100)
receive_po(actor="receiver", po_id=po_id, quantity=100)
```

### Business rules (`inventory.business.rules`)

- `sales_velocity, calculate_order_quantity, run_reorder_rule, clamp, run_dynamic_pricing_rule`

```python
from inventory.business.rules import run_reorder_rule, run_dynamic_pricing_rule

run_reorder_rule(actor="system", days=7)
run_dynamic_pricing_rule(actor="system")
```

### Analytics (`inventory.business.analytics`)

- `_fetch_products, _min_max, _normalize, build_popularity_priority_queue, build_discount_max_heap, generate_report_csv`

```python
from inventory.business.analytics import generate_report_csv

generate_report_csv("report.csv")
```

---

## How custom data structures are used

The project intentionally implements several core data structures and **uses them in the application logic**, not just as standalone exercises.

- **`LinkedList`** (`datastructures/linked_list.py`): a singly linked list with push/pop and `items()` iteration.  
  Used inside the hash table buckets for separate chaining.

- **`HashMap[K,V]`** (`datastructures/hash_map.py`): a separate‑chaining hash table that stores collisions in per‑bucket linked lists.  
  Exposes familiar operations (`set`, `get`, `delete`, `keys`, `values`, `items`), resizing on load‑factor, and iteration helpers.  
  The higher‑level `Dictionary` wrapper below delegates to this.

- **`Dictionary[K,V]`** (`datastructures/dictionary.py`): a dict‑like facade backed by `HashMap`.  
  Provides a friendlier surface (`get`, `set`, `delete`, `keys`, `values`, `items`, `to_py`), returning native Python types when needed.

- **`CustomList[T]`** (`datastructures/custom_list.py`): a thin typed wrapper around Python’s list with conveniences and `to_py`.  
  Used by analytics to return list‑like results while keeping the “custom DS” requirement explicit.

- **`MinHeap[T]`** (`datastructures/heap.py`): a binary min‑heap with `push`, `pop`, and `peek`.  
  Demonstrates heap behavior; analytics also shows a _max‑heap by negating keys_ for discount prioritization.

### Where they appear in the app

- **Analytics** functions return `CustomList` and `Dictionary` instances for product collections, and build **priority queues / heaps** for tasks like “most discounted first” or “most popular first”.
- The **HashMap** uses the **LinkedList** internally; unit tests exercise these structures (`tests/ds_test.py`).

---

## Database schema

SQLite schema lives in **`data/schema.sql`**. It includes (at minimum):

- `products` — core product catalog and inventory state (SKU, name, category, price/min/max, quantity, reorder level, flags, timestamps).
- `purchase_orders` — open and received POs to replenish stock.
- `sales` — recorded sales events (used for **sales velocity** and analytics).
- `product_metrics` — derived counters such as `reviews_count`, `items_sold_count`, `discount_rate`.
- `audit_log` — append‑only record of writes (actor, action, entity, details, timestamp).

Initialize all tables via:

```bash
python -m inventory.cli init-db
```

> The default SQLite file path is defined in `inventory/db/db.py`. Inspect that module if you want to change where the DB file is stored.

---

## License

MIT — see `pyproject.toml`.
