"""Tests for the registration flow (POST /register in app.py).

Each test runs against a throwaway DB file (tmp_path) by monkeypatching
db.DB_PATH before any route touches the database, so the real
expense_tracker.db is never modified. Mirrors tests/test_db.py.
"""

import os

import pytest
from werkzeug.security import check_password_hash

from database import db
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A Flask test client backed by a fresh, seeded temporary database."""
    test_db_path = tmp_path / "test_register.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()
    db.seed_db()  # seeds demo@spendly.com — used by the duplicate-email test

    app_module.app.config["TESTING"] = True
    app_module.app.secret_key = "test-secret"
    return app_module.app.test_client()


def _user_count():
    """Row count in the (temporary) users table."""
    conn = db.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def test_get_register_renders(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"Create your account" in resp.data


def test_register_success_creates_user(client):
    resp = client.post(
        "/register",
        data={
            "name": "Rahul Sharma",
            "email": "rahul.sharma@example.com",
            "password": "supersecret",
        },
    )
    # Post/Redirect/Get: a successful registration redirects to /login.
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # The same client keeps the session cookie, so the flashed success
    # message is rendered (and consumed) on the next request to /login.
    followed = client.get("/login")
    assert b"Account created" in followed.data

    row = db.get_user_by_email("rahul.sharma@example.com")
    assert row is not None
    assert row["name"] == "Rahul Sharma"
    # Password is hashed, never stored as plaintext.
    assert row["password_hash"] != "supersecret"
    assert check_password_hash(row["password_hash"], "supersecret")
    assert _user_count() == 2  # demo user + the new one


def test_register_duplicate_email_rejected(client):
    resp = client.post(
        "/register",
        data={
            "name": "Impostor",
            "email": "demo@spendly.com",  # already seeded
            "password": "supersecret",
        },
    )
    assert resp.status_code == 200  # re-render, not a redirect
    assert b"already registered" in resp.data
    assert _user_count() == 1  # no new row


def test_register_duplicate_email_is_case_insensitive(client):
    resp = client.post(
        "/register",
        data={
            "name": "Impostor",
            "email": "DEMO@Spendly.com",  # same account, different case
            "password": "supersecret",
        },
    )
    assert resp.status_code == 200
    assert b"already registered" in resp.data
    assert _user_count() == 1


def test_register_empty_name_rejected(client):
    resp = client.post(
        "/register",
        data={
            "name": "   ",  # whitespace only
            "email": "someone@example.com",
            "password": "supersecret",
        },
    )
    assert resp.status_code == 200
    assert b"Please enter your name." in resp.data
    assert _user_count() == 1


def test_register_malformed_email_rejected(client):
    resp = client.post(
        "/register",
        data={
            "name": "Priya Nair",
            "email": "not-an-email",
            "password": "supersecret",
        },
    )
    assert resp.status_code == 200
    assert b"valid email" in resp.data
    assert _user_count() == 1


def test_register_short_password_rejected(client):
    resp = client.post(
        "/register",
        data={
            "name": "Priya Nair",
            "email": "priya.nair@example.com",
            "password": "short",  # < 8 chars
        },
    )
    assert resp.status_code == 200
    assert b"at least 8 characters" in resp.data
    assert _user_count() == 1


def test_register_preserves_form_values_on_error(client):
    resp = client.post(
        "/register",
        data={
            "name": "Alice",
            "email": "Alice@Example.com",
            "password": "short",  # forces a validation error
        },
    )
    assert resp.status_code == 200
    # Entered name is preserved and email is preserved lowercased/normalized.
    assert b'value="Alice"' in resp.data
    assert b'value="alice@example.com"' in resp.data


def test_register_form_uses_url_for():
    """The template source must use url_for(), not a hardcoded action URL."""
    template_path = os.path.join(
        db.BASE_DIR, "templates", "register.html"
    )
    with open(template_path, encoding="utf-8") as f:
        source = f.read()
    assert "url_for('register')" in source
    assert 'action="/register"' not in source
