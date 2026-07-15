"""Tests for the SQLite data layer (database/db.py).

Each test runs against a throwaway DB file (tmp_path) by monkeypatching
db.DB_PATH, so the real expense_tracker.db is never touched.
"""

import re
import sqlite3
from datetime import date

import pytest
from werkzeug.security import check_password_hash

from database import db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point db.DB_PATH at a temporary file and create the schema."""
    test_db_path = tmp_path / "test_expense_tracker.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()
    return test_db_path


def test_init_db_creates_both_tables(temp_db):
    conn = db.get_db()
    try:
        user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
        expense_cols = {r["name"] for r in conn.execute("PRAGMA table_info(expenses)")}
    finally:
        conn.close()

    assert {"id", "name", "email", "password_hash", "created_at"} <= user_cols
    assert {
        "id",
        "user_id",
        "amount",
        "category",
        "date",
        "description",
        "created_at",
    } <= expense_cols


def test_init_db_is_idempotent(temp_db):
    # Calling init_db again must not raise (CREATE TABLE IF NOT EXISTS).
    db.init_db()
    db.init_db()


def test_get_db_enables_foreign_keys(temp_db):
    conn = db.get_db()
    try:
        fk_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        conn.close()
    assert fk_on == 1


def test_seed_db_inserts_demo_user_and_expenses(temp_db):
    db.seed_db()
    conn = db.get_db()
    try:
        users = conn.execute("SELECT * FROM users").fetchall()
        expenses = conn.execute("SELECT * FROM expenses").fetchall()
    finally:
        conn.close()

    assert len(users) == 1
    assert users[0]["name"] == "Demo User"
    assert users[0]["email"] == "demo@spendly.com"
    # Password is hashed, never stored as plaintext.
    assert users[0]["password_hash"] != "demo123"
    assert check_password_hash(users[0]["password_hash"], "demo123")

    assert len(expenses) == 8
    categories = {e["category"] for e in expenses}
    assert categories == set(db.CATEGORIES)
    # amount is stored as REAL (float).
    assert all(isinstance(e["amount"], float) for e in expenses)


def test_seed_db_dates_are_current_month_and_valid(temp_db):
    db.seed_db()
    conn = db.get_db()
    try:
        dates = [e["date"] for e in conn.execute("SELECT date FROM expenses")]
    finally:
        conn.close()

    prefix = date.today().strftime("%Y-%m")
    for value in dates:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
        assert value.startswith(prefix)


def test_seed_db_is_idempotent(temp_db):
    db.seed_db()
    db.seed_db()  # second call must not duplicate anything
    conn = db.get_db()
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        expense_count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()

    assert user_count == 1
    assert expense_count == 8


def test_unique_email_constraint(temp_db):
    db.seed_db()
    conn = db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Another User", "demo@spendly.com", "hash"),
            )
            conn.commit()
    finally:
        conn.close()


def test_foreign_key_constraint(temp_db):
    conn = db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (9999, 10.0, "Food", "2026-07-01", None),
            )
            conn.commit()
    finally:
        conn.close()
