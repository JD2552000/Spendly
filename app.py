import os
import re

from flask import Flask, render_template, request, redirect, url_for, flash, session

from database.db import (
    get_db,
    init_db,
    seed_db,
    create_user,
    get_user_by_email,
    verify_user,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Ensure the database exists and is seeded before any route is served.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name:
            error = "Please enter your name."
        elif not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif get_user_by_email(email):
            error = "That email is already registered."
        else:
            create_user(name, email, password)
            flash("Account created — please sign in.")
            return redirect(url_for("login"))

        return render_template(
            "register.html", error=error, name=name, email=email
        )

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = verify_user(email, password)
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!")
            return redirect(url_for("profile"))

        return render_template(
            "login.html", error="Invalid email or password.", email=email
        )

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Static design data — real queries arrive in Step 5.
    user = {
        "name": session.get("user_name", "Demo User"),
        "email": "demo@spendly.com",
        "member_since": "July 2026",
    }
    summary = {"total": 287.39, "count": 8, "top_category": "Shopping"}
    transactions = [
        {"date": "2026-07-18", "description": "Weekly groceries", "category": "Food", "amount": 42.75},
        {"date": "2026-07-15", "description": "Metro card top-up", "category": "Transport", "amount": 30.00},
        {"date": "2026-07-12", "description": "Electricity bill", "category": "Bills", "amount": 68.40},
        {"date": "2026-07-09", "description": "New headphones", "category": "Shopping", "amount": 89.99},
        {"date": "2026-07-05", "description": "Movie night", "category": "Entertainment", "amount": 24.00},
    ]
    categories = [
        {"name": "Shopping", "total": 89.99, "pct": 31},
        {"name": "Bills", "total": 68.40, "pct": 24},
        {"name": "Food", "total": 42.75, "pct": 15},
        {"name": "Transport", "total": 30.00, "pct": 10},
        {"name": "Entertainment", "total": 24.00, "pct": 8},
    ]
    return render_template(
        "profile.html", user=user, summary=summary,
        transactions=transactions, categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
