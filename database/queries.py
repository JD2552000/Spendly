"""Pure, read-only query helpers for Spendly's profile page.

No Flask (or any web-framework) imports belong here — these functions are
plain Python built on top of the SQLite data layer in ``database.db`` so they
stay unit-testable in isolation and reusable outside the web app. Every helper
opens its own connection via ``get_db()`` and closes it (try/finally) before
returning, and every query is parameterized with ``?`` placeholders.
"""

from datetime import datetime

from database.db import get_db


def _format_member_since(created_at):
    """Format a users.created_at value as "Month YYYY" (e.g. "July 2026").

    SQLite's ``datetime('now')`` stores the timestamp as ``YYYY-MM-DD HH:MM:SS``.
    Falls back gracefully if the value is missing or cannot be parsed.
    """
    if not created_at:
        return "—"
    try:
        return datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    except (ValueError, TypeError):
        return str(created_at)


def get_user_by_id(user_id):
    """Return ``{name, email, member_since}`` for a user, or ``None``.

    ``member_since`` is derived from ``users.created_at`` and formatted as
    "Month YYYY".
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": _format_member_since(row["created_at"]),
    }


def get_summary_stats(user_id):
    """Return spending summary statistics for a single user.

    Shape::

        {
            "total_spent": <float rounded to 2dp, 0 if no expenses>,
            "transaction_count": <int>,
            "top_category": <highest-spend category, or "—" if none>,
        }
    """
    conn = get_db()
    try:
        total_spent = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

        transaction_count = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

        top_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": round(total_spent, 2),
        "transaction_count": transaction_count,
        "top_category": top_row[0] if top_row is not None else "—",
    }


def get_recent_transactions(user_id, limit=10):
    """Return a user's most recent expenses, newest-first.

    Each item is ``{date, description, category, amount}``. A NULL description
    is normalized to an empty string. A user with no expenses yields ``[]``.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount "
            "FROM expenses "
            "WHERE user_id = ? "
            "ORDER BY date DESC, id DESC "
            "LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": row["date"],
            "description": row["description"] if row["description"] is not None else "",
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


def get_category_breakdown(user_id):
    """Return per-category spend for a user, ordered by amount descending.

    Each item is ``{name, amount, pct}`` where ``pct`` is a whole-number share
    of the grand total. The ``pct`` values always sum to exactly 100 — any
    rounding leftover is folded into the first (largest) entry. Returns ``[]``
    when the user has no expenses, and never divides by zero.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total "
            "FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY total DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    grand_total = sum(row["total"] for row in rows)
    if not rows or grand_total <= 0:
        return []

    breakdown = [
        {
            "name": row["category"],
            "amount": round(row["total"], 2),
            "pct": round(row["total"] / grand_total * 100),
        }
        for row in rows
    ]

    # Force the integer percentages to total exactly 100 by pushing any
    # rounding leftover onto the first (largest) entry.
    breakdown[0]["pct"] += 100 - sum(item["pct"] for item in breakdown)

    return breakdown
