"""
Database connection and initialization utilities.

This module centralizes SQLite database access for the inventory system.
It provides:
- A connection helper (`get_conn`) that enables foreign key constraints
  and uses Row objects for dict-like access.
- A schema initialization helper (`init_db`) for setting up the schema
  from an SQL file.
"""

import os
import sqlite3

# Base directory of the project (one level above this file’s folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Paths to the database and schema (relative to BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "data", "inventory.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "data", "schema.sql")


def get_conn() -> sqlite3.Connection:
    """
    Return a SQLite3 connection with sensible defaults.

    - Enables foreign key enforcement (PRAGMA foreign_keys = ON).
    - Sets `row_factory` to sqlite3.Row for dict-like row access.
    - The connection is intended to be used as a context manager:
        with get_conn() as conn:
            conn.execute("...")
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """
    Initialize the database using the SQL schema file.

    Reads the contents of `schema.sql` and executes it in a single
    transaction. This should be run only during first-time setup
    or when resetting the database.

    Example:
        from db import init_db
        init_db()
    """
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    with get_conn() as conn:
        conn.executescript(schema)
        conn.commit()
