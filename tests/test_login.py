"""Tests for the login/logout flow (app.py) and verify_user (database/db.py).

Each test runs against a throwaway DB file (tmp_path) by monkeypatching
db.DB_PATH before any route touches the database, so the real
expense_tracker.db is never modified. Mirrors tests/test_register.py.
"""

import os

import pytest

from database import db
import app as app_module

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"
GENERIC_ERROR = b"Invalid email or password"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A Flask test client backed by a fresh, seeded temporary database."""
    test_db_path = tmp_path / "test_login.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()
    db.seed_db()  # seeds the demo account: demo@spendly.com / demo123

    app_module.app.config["TESTING"] = True
    app_module.app.secret_key = "test-secret"
    return app_module.app.test_client()


# --- verify_user (direct db helper) --------------------------------------

def test_verify_user_valid_returns_row(client):
    user = db.verify_user(DEMO_EMAIL, DEMO_PASSWORD)
    assert user is not None
    assert user["email"] == DEMO_EMAIL
    assert user["name"] == "Demo User"


def test_verify_user_wrong_password_returns_none(client):
    assert db.verify_user(DEMO_EMAIL, "wrong-password") is None


def test_verify_user_unknown_email_returns_none(client):
    assert db.verify_user("nobody@spendly.com", DEMO_PASSWORD) is None


# --- GET /login ----------------------------------------------------------

def test_get_login_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in to your Spendly account" in resp.data


# --- POST /login success -------------------------------------------------

def test_login_success_sets_session_and_redirects(client):
    resp = client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]

    demo_id = db.get_user_by_email(DEMO_EMAIL)["id"]
    with client.session_transaction() as sess:
        assert sess["user_id"] == demo_id
        assert sess["user_name"] == "Demo User"


def test_login_case_insensitive(client):
    resp = client.post(
        "/login",
        data={"email": "DEMO@Spendly.com", "password": DEMO_PASSWORD},
    )
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" in sess


# --- POST /login failure -------------------------------------------------

def test_login_wrong_password_generic_error_no_session(client):
    resp = client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": "wrong-password"},
    )
    assert resp.status_code == 200
    assert GENERIC_ERROR in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_unknown_email_same_generic_error_no_session(client):
    resp = client.post(
        "/login",
        data={"email": "nobody@spendly.com", "password": "whatever"},
    )
    assert resp.status_code == 200
    # Same message as the wrong-password case — prevents user enumeration.
    assert GENERIC_ERROR in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_preserves_email_on_failure(client):
    resp = client.post(
        "/login",
        data={"email": "Demo@Spendly.com", "password": "wrong"},
    )
    assert resp.status_code == 200
    # Email is preserved and normalized (lowercased) in the re-rendered form.
    assert b'value="demo@spendly.com"' in resp.data


# --- logout --------------------------------------------------------------

def test_logout_clears_session_and_redirects(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" not in sess

    # The flash is rendered/consumed on the next request to a base page.
    followed = client.get("/login")
    assert b"logged out" in followed.data


def test_logout_when_not_logged_in_is_noop(client):
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# --- navbar reflects login state -----------------------------------------

def test_navbar_reflects_login_state(client):
    # Logged out: navbar shows "Get started", not "Sign out".
    resp = client.get("/login")
    assert b"Get started" in resp.data
    assert b"Sign out" not in resp.data

    # Logged in: navbar shows the user's name and a "Sign out" link. Checked on
    # the landing page, since /login now redirects logged-in users away.
    client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    resp = client.get("/")
    assert b"Sign out" in resp.data
    assert b"Demo User" in resp.data


# --- logged-in users are redirected away from auth pages -----------------

def test_login_page_redirects_when_already_logged_in(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    resp = client.get("/login")
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]


def test_register_page_redirects_when_already_logged_in(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    resp = client.get("/register")
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]


# --- template uses url_for -----------------------------------------------

def test_login_template_uses_url_for():
    """The template source must use url_for(), not a hardcoded action URL."""
    template_path = os.path.join(db.BASE_DIR, "templates", "login.html")
    with open(template_path, encoding="utf-8") as f:
        source = f.read()
    assert "url_for('login')" in source
    assert 'action="/login"' not in source
