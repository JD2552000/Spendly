# Spec: Login and Logout

## Overview

This feature turns Spendly's authentication on. Registration (Step 2) can create accounts, but there is no way to sign in or out yet: `GET /login` only renders a form, and `/logout` is a raw-string stub. This step adds `POST /login` to verify credentials against the stored werkzeug hash and establish a server-side session, converts `/logout` into a real handler that clears the session, and makes the navbar reflect logged-in vs logged-out state (surfacing a "Sign out" link). It is the gateway for every logged-in feature that follows — profile (Step 4) and the expense CRUD steps all depend on a working session established here.

## Depends on

- **Step 1 — Database setup** (`.claude/specs/01-database-setup.md`): `get_db()`, the `users` table, and the seeded demo account (`demo@spendly.com` / `demo123`) used to exercise login.
- **Step 2 — Registration** (`.claude/specs/02-registration.md`): provides `get_user_by_email()` in `db.py`, and the session/flash infrastructure this step reuses — `app.secret_key`, the `get_flashed_messages()` block in `base.html`, `.flash` CSS, and the `request/redirect/url_for/flash` imports. Login authenticates the accounts registration creates.

## Routes

- `GET /login` — render the login form. **Access: public.** (Already implemented; the decorator is extended to also accept POST.)
- `POST /login` — authenticate: normalize the email, verify the password against the stored hash, and on success set the session and redirect to `/profile`; on failure re-render `login.html` with a generic error (HTTP 200, no redirect). **Access: public.**
- `GET /logout` — clear the session and redirect to `/login` with a confirmation flash. **Access: public** (a no-op clear when not logged in). Replaces the current raw-string stub.

Additionally, an already-logged-in user who visits `GET /login` or `GET /register` is redirected to `/profile` (auth pages are for logged-out users only). `/profile` stays a Step 4 stub (login only *redirects* to it — it is not implemented here).

## Database changes

**No schema changes** — the `users` table already stores `password_hash` (`database/db.py:48-54`).

One new **auth helper** is added to `database/db.py` (keeps credential logic out of the route, per the "no DB logic in routes" rule) and `check_password_hash` is added to the existing werkzeug import:

- `verify_user(email, password)` — call `get_user_by_email(email)`; if a row exists and `check_password_hash(row["password_hash"], password)` is true, return the row; otherwise return `None`. Uses the existing parameterised lookup; no new query.

## Templates

**Create:**
- None. The login page and all auth styles already exist.

**Modify:**
- `templates/login.html` — (1) change the hardcoded `action="/login"` to `action="{{ url_for('login') }}"`; (2) add `value="{{ email or '' }}"` to the email input so a failed attempt preserves it. The `{% if error %}` block already works.
- `templates/base.html` — make the navbar conditional on `session.user_id` (Flask exposes `session` to Jinja automatically): when logged in, show the user's name and a "Sign out" link to `url_for('logout')`; when logged out, show the existing "Sign in" / "Get started" links. This surfaces the logout entry point and makes login state visible.

## Files to change

- `app.py` — add `session` to the flask import; extend `login` to `methods=["GET", "POST"]` with POST handling; replace the `/logout` raw-string stub with `session.clear()` + flash + redirect.
- `database/db.py` — add `verify_user()`; extend the werkzeug import to include `check_password_hash`.
- `templates/login.html` — `url_for` action + preserve email.
- `templates/base.html` — session-conditional navbar with a logout link.
- `CLAUDE.md` — update the route table: `/login` → "GET, POST — GET renders form, POST authenticates"; `/logout` → "Implemented — clears session, redirects".

## Files to create

- `tests/test_login.py` — pytest coverage for the login/logout flow and `verify_user`, mirroring the temp-DB isolation pattern in `tests/test_db.py` / `tests/test_register.py`.

## New dependencies

**No new dependencies.** `session` (Flask) and `check_password_hash` (werkzeug) are already available; `werkzeug` is an existing dependency.

## Rules for implementation

- **No SQLAlchemy or ORMs** — raw `sqlite3` via `get_db()` only.
- **Parameterised queries only** — reuse the existing `?`-placeholder lookup; never interpolate SQL.
- **Passwords hashed with werkzeug** — never compare plaintext; verify only via `check_password_hash`. The raw password is never stored or logged.
- **Use CSS variables — never hardcode hex values** — any navbar tweak reuses existing classes/variables (no new hex).
- **All templates extend `base.html`.**
- **No DB/credential logic in routes** — the route calls `verify_user()`; the hash check lives in `database/db.py`.
- **Never hardcode URLs in templates** — use `url_for()` (this step fixes the existing `action="/login"` violation).
- **Use `abort()` for HTTP errors**, not raw string returns — the `/logout` stub must become a real redirect, never a bare string.
- **Generic auth error** — on any failure (unknown email *or* wrong password) show the same message, e.g. "Invalid email or password." Do not reveal whether an email is registered.
- **Normalize the email** (`strip().lower()`) before lookup, so login is case-insensitive and consistent with registration.
- **Minimal session** — store only `session["user_id"]` (and `session["user_name"]` for display); log out with `session.clear()`. Successful login uses Post/Redirect/Get (`redirect()` to `/profile`).

## Definition of done

Each item is verifiable by running the app (`python app.py`, port 5001) or `pytest`:

1. `GET /login` still renders the form with no errors.
2. `POST /login` with the seeded demo credentials (`demo@spendly.com` / `demo123`) sets `session["user_id"]`, flashes a welcome message, and redirects (302) to `/profile`.
3. `POST /login` with a correct email but wrong password re-renders `login.html` with "Invalid email or password" and sets **no** session.
4. `POST /login` with an unknown email shows the **same** generic error and sets no session.
5. Login is case-insensitive: `DEMO@Spendly.com` + `demo123` authenticates successfully.
6. While logged in, the navbar shows a "Sign out" link (and the user's name) and hides "Sign in"/"Get started"; while logged out, it shows "Sign in"/"Get started" and no logout link.
7. `GET /logout` clears the session and redirects (302) to `/login` with a "logged out" flash; afterward the navbar shows the logged-out state.
8. On a failed login the entered email remains populated, and `login.html`'s form uses `url_for('login')` — no hardcoded URL remains.
9. Visiting `GET /login` or `GET /register` while already logged in redirects (302) to `/profile` instead of rendering the form.
10. `pytest tests/test_login.py` passes, covering: `verify_user` (valid, wrong password, unknown email, case-insensitive), login success sets session + redirects, both failure cases, logout clears the session, and the logged-in redirect away from auth pages. Full `pytest` stays green.
