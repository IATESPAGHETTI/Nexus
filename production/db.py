"""Seeded in-memory SQLite database for the simulated production service.

Real SQLite queries with real timing — the data is synthetic seed data (this is a
simulated environment, see production/CLAUDE.md), but query execution and the
recorded diagnostics are not faked.
"""

from __future__ import annotations

import sqlite3
import time

from observability import query_store

_connection: sqlite3.Connection | None = None

SEED_ORDERS = [
    ("alice", 42.50, "completed"),
    ("bob", 19.99, "completed"),
    ("carol", 103.20, "pending"),
    ("dave", 7.00, "completed"),
    ("erin", 250.00, "failed"),
    ("frank", 15.75, "completed"),
    ("grace", 88.10, "pending"),
    ("heidi", 33.33, "completed"),
    ("ivan", 5.00, "completed"),
    ("judy", 199.99, "pending"),
]


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(":memory:", check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _init_schema(_connection)
    return _connection


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.executemany(
        "INSERT INTO orders (customer, amount, status, created_at) VALUES (?, ?, ?, ?)",
        [(customer, amount, status, now) for customer, amount, status in SEED_ORDERS],
    )
    conn.commit()


def run_query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    start = time.perf_counter()
    cursor = conn.execute(sql, params)
    rows = cursor.fetchall()
    duration_ms = (time.perf_counter() - start) * 1000
    query_store.add(
        {
            "sql": sql,
            "duration_ms": round(duration_ms, 3),
            "row_count": len(rows),
        }
    )
    return rows


def diagnostics() -> dict:
    conn = get_connection()
    total_orders = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
    by_status = conn.execute(
        "SELECT status, COUNT(*) AS c FROM orders GROUP BY status"
    ).fetchall()
    return {
        "engine": "sqlite3 (in-memory, simulated)",
        "table_row_counts": {"orders": total_orders},
        "orders_by_status": {row["status"]: row["c"] for row in by_status},
        "recent_queries": query_store.recent(limit=10),
        "query_summary": query_store.summary(),
    }
