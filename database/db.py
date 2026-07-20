"""SQLite data layer for Spendly.

Contains the only database logic in the app:
    get_db()   — connection with row_factory and foreign keys enabled
    init_db()  — create tables (idempotent)
    seed_db()  — insert demo data once (idempotent)
"""

import os
import calendar
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

# Resolve the DB path relative to the project root, not the current working
# directory. This module lives in <root>/database/db.py, so two dirname() calls
# climb from the file up to the project root.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "expense_tracker.db")

# Fixed category list — single source of truth for seed data and future steps.
CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)


def get_db():
    """Return a SQLite connection with dict-like rows and FK enforcement on."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create both tables if they do not exist. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _build_seed_expenses(user_id):
    """Return 8 sample expense rows spread across the current month.

    Each row is (user_id, amount, category, date, description). Dates are
    clamped to the number of days in the current month so February works too.
    """
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    day_slots = [1, 5, 9, 13, 17, 21, 25, 29]

    # (category, amount as REAL, description) — every category covered.
    samples = [
        ("Food", 12.50, "Groceries at local market"),
        ("Transport", 30.00, "Monthly metro top-up"),
        ("Bills", 65.75, "Electricity bill"),
        ("Health", 45.00, "Pharmacy - prescription"),
        ("Entertainment", 15.99, "Movie ticket"),
        ("Shopping", 89.90, "New running shoes"),
        ("Other", 20.00, "Gift for a friend"),
        ("Food", 8.25, None),  # NULL description exercises the nullable column
    ]

    rows = []
    for (category, amount, description), slot in zip(samples, day_slots):
        day = min(slot, days_in_month)
        expense_date = date(today.year, today.month, day).isoformat()
        rows.append((user_id, amount, category, expense_date, description))
    return rows


def seed_db():
    """Insert one demo user and 8 sample expenses, only if the DB is empty."""
    conn = get_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            return  # already seeded — do nothing

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            _build_seed_expenses(user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the users row matching email, or None if no such user exists.

    The email is queried verbatim — callers are responsible for normalizing
    (strip + lowercase) before lookup.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password):
    """Insert a new user with a hashed password; return the new row id.

    The raw password is never stored — only its werkzeug hash. created_at
    falls back to the table's datetime('now') default.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
