"""Tests for Step 5 — backend connection.

Covers the pure query helpers in database/queries.py and the /profile route
that consumes them. Each test runs against a throwaway DB file (tmp_path) by
monkeypatching db.DB_PATH, so the real expense_tracker.db is never touched.
Mirrors the fixture pattern in tests/test_db.py and tests/test_profile.py.

Expected values follow the REAL seed data (total 287.39, 8 rows, top category
"Shopping", 7 categories) — not the stale figures in the spec.
"""

import re

import pytest

from database import db
from database import queries
import app as app_module

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point db.DB_PATH at a fresh temporary file with the schema created."""
    test_db_path = tmp_path / "test_backend.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()
    return test_db_path


@pytest.fixture
def seeded_user_id(temp_db):
    """Seed the demo data and return the demo user's id."""
    db.seed_db()
    return db.get_user_by_email(DEMO_EMAIL)["id"]


# --------------------------------------------------------------------------- #
# get_user_by_id                                                              #
# --------------------------------------------------------------------------- #

def test_get_user_by_id_returns_profile(seeded_user_id):
    user = queries.get_user_by_id(seeded_user_id)
    assert user["name"] == "Demo User"
    assert user["email"] == DEMO_EMAIL
    # member_since derived from created_at, formatted "Month YYYY".
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", user["member_since"])


def test_get_user_by_id_unknown_returns_none(temp_db):
    assert queries.get_user_by_id(9999) is None


# --------------------------------------------------------------------------- #
# get_summary_stats                                                           #
# --------------------------------------------------------------------------- #

def test_summary_stats_for_seeded_user(seeded_user_id):
    assert queries.get_summary_stats(seeded_user_id) == {
        "total_spent": 287.39,
        "transaction_count": 8,
        "top_category": "Shopping",
    }


def test_summary_stats_for_user_with_no_expenses(temp_db):
    uid = db.create_user("Empty", "empty@spendly.com", "password123")
    assert queries.get_summary_stats(uid) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


# --------------------------------------------------------------------------- #
# get_recent_transactions                                                     #
# --------------------------------------------------------------------------- #

def test_recent_transactions_shape_and_order(seeded_user_id):
    txns = queries.get_recent_transactions(seeded_user_id)
    assert len(txns) == 8
    for t in txns:
        assert set(t.keys()) == {"date", "description", "category", "amount"}
    dates = [t["date"] for t in txns]
    assert dates == sorted(dates, reverse=True)  # newest-first
    # Newest row (day 29) is the Food 8.25 expense seeded with a NULL description.
    assert txns[0]["category"] == "Food"
    assert txns[0]["amount"] == 8.25
    assert txns[0]["description"] == ""  # NULL normalized, never "None"


def test_recent_transactions_respects_limit(seeded_user_id):
    assert len(queries.get_recent_transactions(seeded_user_id, limit=3)) == 3


def test_recent_transactions_empty_for_user_with_no_expenses(temp_db):
    uid = db.create_user("Empty", "empty@spendly.com", "password123")
    assert queries.get_recent_transactions(uid) == []


# --------------------------------------------------------------------------- #
# get_category_breakdown                                                      #
# --------------------------------------------------------------------------- #

def test_category_breakdown_for_seeded_user(seeded_user_id):
    rows = queries.get_category_breakdown(seeded_user_id)
    assert len(rows) == 7
    for row in rows:
        assert set(row.keys()) == {"name", "amount", "pct"}
        assert isinstance(row["pct"], int)
    # Ordered by amount descending, largest first.
    amounts = [row["amount"] for row in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert rows[0]["name"] == "Shopping"
    # Percentages are whole numbers summing to exactly 100.
    assert sum(row["pct"] for row in rows) == 100


def test_category_breakdown_empty_for_user_with_no_expenses(temp_db):
    uid = db.create_user("Empty", "empty@spendly.com", "password123")
    assert queries.get_category_breakdown(uid) == []


# --------------------------------------------------------------------------- #
# /profile route                                                              #
# --------------------------------------------------------------------------- #

@pytest.fixture
def client(tmp_path, monkeypatch):
    """A Flask test client backed by a fresh, seeded temporary database."""
    test_db_path = tmp_path / "test_backend_route.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()
    db.seed_db()
    app_module.app.config["TESTING"] = True
    app_module.app.secret_key = "test-secret"
    return app_module.app.test_client()


def _login(client, email=DEMO_EMAIL, password=DEMO_PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def test_profile_redirects_when_logged_out(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_shows_real_seed_data(client):
    _login(client)
    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.data
    assert b"Demo User" in body
    assert DEMO_EMAIL.encode() in body
    assert "₹".encode() in body
    assert b"287.39" in body
    assert b"Shopping" in body
    # A real seed transaction description (proves live data, not the old stubs).
    assert b"New running shoes" in body


def test_profile_new_user_shows_zeros(client):
    """A freshly registered user with no expenses sees zeros, no errors."""
    db.create_user("New Person", "new@spendly.com", "password123")
    _login(client, email="new@spendly.com", password="password123")
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert "₹0.00".encode() in resp.data
