# Spec: Registration

## Overview

This feature makes the existing `/register` page functional. Today `GET /register` only renders the form; there is no way to actually create an account. This step adds `POST /register` handling that validates the submitted name, email, and password, rejects duplicates and bad input, hashes the password with werkzeug, and inserts a new row into the `users` table. On success the user is redirected to the login page with a confirmation message. This is the first write-path in Spendly and the prerequisite for every logged-in feature (login, profile, expenses) that follows.

## Depends on

- **Step 1 — Database setup** (`.claude/specs/01-database-setup.md`), which provides `get_db()`, `init_db()`, `seed_db()`, and the `users` table with columns `id, name, email (UNIQUE), password_hash, created_at`. Registration reuses `get_db()` and the `generate_password_hash` import already present in `database/db.py`.

## Routes

- `GET /register` — render the registration form. **Access: public.** (Already implemented; the route decorator is extended to also accept POST.)
- `POST /register` — process a submitted registration: validate input, ensure the email is unique, create the user, then redirect to `/login`. On validation failure, re-render `register.html` with an `error` message and the previously entered `name`/`email` preserved. **Access: public.**

No other routes change. `/login` remains GET-only in this step (its POST handler is a later step).

## Database changes

**No schema changes** — the `users` table already has every required column and the `email UNIQUE` constraint (verified against `database/db.py:48-54`).

Two new **query helper functions** are added to `database/db.py` (this is not a schema change, but is required because DB logic must never live in routes):

- `get_user_by_email(email)` — return the matching `users` row (`sqlite3.Row`) or `None`, using a parameterised query.
- `create_user(name, email, password)` — hash `password` with `generate_password_hash`, insert a new row with a parameterised query, and return the new `id` (`cursor.lastrowid`).

## Templates

**Create:**
- None. The registration page and its auth styles (`auth-card`, `auth-error`, `form-group`, `btn-submit`, etc.) already exist in `templates/register.html` and `static/css/style.css`.

**Modify:**
- `templates/register.html` — (1) change the hardcoded `action="/register"` to `action="{{ url_for('register') }}"`; (2) repopulate the `name` and `email` fields from template variables (e.g. `value="{{ name or '' }}"`) so a failed submission does not clear the form. The existing `{% if error %}` block already renders `error`.
- `templates/base.html` — add a flashed-messages block (`{% for message in get_flashed_messages() %}`) so the post-redirect success message shows on the login page. Style it with a new `.flash` class in `style.css` using existing CSS variables.
- `static/css/style.css` — add a `.flash` (success) style block using CSS variables only.

## Files to change

- `app.py` — extend the `register` route to `methods=["GET", "POST"]`, add POST handling, and add imports `request, redirect, url_for, flash`. Configure `app.secret_key` from `os.environ.get("SECRET_KEY", ...)` so `flash()` works (Flask stdlib feature — no new package).
- `database/db.py` — add `get_user_by_email()` and `create_user()`.
- `templates/register.html` — fix `action`, preserve entered values.
- `templates/base.html` — add flashed-messages rendering block.
- `static/css/style.css` — add `.flash` styling.
- `CLAUDE.md` — update the route table: `/register` becomes "Implemented — GET renders form, POST creates user".

## Files to create

- `tests/test_register.py` — pytest coverage for the new behavior (mirrors the existing `tests/test_db.py` style, using a temporary DB).

## New dependencies

**No new dependencies.** `flask` (with `request`, `redirect`, `url_for`, `flash`, `session`) and `werkzeug.security.generate_password_hash` are already available. `os` is stdlib.

## Rules for implementation

- **No SQLAlchemy or ORMs** — raw `sqlite3` via `get_db()` only.
- **Parameterised queries only** — use `?` placeholders; never build SQL with f-strings or string concatenation.
- **Passwords hashed with werkzeug** — store only `generate_password_hash(password)`; the raw password must never be written to the database.
- **Use CSS variables — never hardcode hex values** — the new `.flash` style must reference existing variables in `:root`.
- **All templates extend `base.html`** — do not add standalone pages.
- **No DB logic in routes** — all queries live in `database/db.py`; the route calls `get_user_by_email()` / `create_user()`.
- **Never hardcode URLs in templates** — use `url_for()` (this step fixes the existing `action="/register"` violation).
- **Use `abort()` for HTTP errors**, not raw string returns.
- **Normalize the email** (strip + lowercase) before uniqueness check and insert, so casing can't create duplicates.
- **Validation rules:** `name` non-empty after strip; `email` non-empty and contains a plausible `@`/domain; `password` at least 8 characters. On any failure, re-render `register.html` with a specific `error` and HTTP 200 (do not redirect).
- **Post/Redirect/Get:** a successful POST must `redirect()` to `/login` (never render directly), flashing a success message.

## Definition of done

Each item is verifiable by running the app (`python app.py`, port 5001) or `pytest`:

1. `GET /register` still renders the form with no errors.
2. Submitting a valid, unused email creates exactly one new row in `users`; verify in the DB that `password_hash` is a werkzeug hash, **not** the plaintext password.
3. After a successful registration the browser is redirected to `/login` and a success flash message is visible on that page.
4. Submitting an email that already exists (e.g. the seeded `demo@spendly.com`) re-renders `register.html` with a clear "email already registered" error and creates **no** new row.
5. Submitting an empty name, a malformed email, or a password shorter than 8 characters re-renders with a specific error and creates no row.
6. On any validation error, the previously entered `name` and `email` remain populated in the form.
7. `register.html`'s form uses `url_for('register')` — no hardcoded URL remains.
8. `pytest tests/test_register.py` passes, covering: successful creation, duplicate-email rejection, and each validation failure.
