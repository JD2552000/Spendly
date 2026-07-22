"""Tests for the profile page (Step 4 — design only, hardcoded data).

Each test runs against a throwaway DB file (tmp_path) by monkeypatching
db.DB_PATH before any route touches the database, so the real
expense_tracker.db is never modified. Mirrors tests/test_login.py.

The profile route serves static design data this step (real queries land in
Step 5), so these tests assert the auth guard, the rendered layout, and that
the template obeys the CLAUDE.md styling rules (url_for + no hex colours).
"""

import os
import re

import pytest

from database import db
import app as app_module

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A Flask test client backed by a fresh, seeded temporary database."""
    test_db_path = tmp_path / "test_profile.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()
    db.seed_db()  # seeds the demo account: demo@spendly.com / demo123

    app_module.app.config["TESTING"] = True
    app_module.app.secret_key = "test-secret"
    return app_module.app.test_client()


def _login(client):
    return client.post(
        "/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
    )


# --- auth guard ----------------------------------------------------------

def test_profile_redirects_when_logged_out(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# --- rendered page -------------------------------------------------------

def test_profile_ok_when_logged_in(client):
    _login(client)
    resp = client.get("/profile")
    assert resp.status_code == 200
    # User info card: name + email.
    assert b"Demo User" in resp.data
    assert b"demo@spendly.com" in resp.data
    # Renders inside the shared layout (footer from base.html).
    assert b"Track every rupee" in resp.data


def test_profile_shows_stats_and_table(client):
    _login(client)
    resp = client.get("/profile")
    body = resp.data
    # Summary stats: total + top category.
    assert b"287.39" in body
    assert b"Shopping" in body
    # Transaction table: at least three distinct hardcoded rows.
    assert b"Weekly groceries" in body
    assert b"Electricity bill" in body
    assert b"New headphones" in body


def test_profile_navbar_links_to_profile(client):
    _login(client)
    resp = client.get("/profile")
    # Logged-in navbar links the username to /profile and offers Sign out.
    assert b'href="/profile"' in resp.data
    assert b"Sign out" in resp.data


# --- template obeys styling rules ----------------------------------------

def test_profile_template_uses_url_for_and_no_hex():
    """profile.html must use url_for for assets and contain no hex colours."""
    template_path = os.path.join(db.BASE_DIR, "templates", "profile.html")
    with open(template_path, encoding="utf-8") as f:
        source = f.read()
    # Static asset referenced via url_for, not a hardcoded path.
    assert "url_for('static'" in source
    assert 'href="/static' not in source
    # No hardcoded internal links.
    assert 'href="/' not in source
    # No hex colour literals — colours come from :root CSS variables only.
    assert re.search(r"#[0-9a-fA-F]{3,6}", source) is None
