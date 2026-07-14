Spendly Application - Database Specification Document

1. Overview
Replace the stub in database/db.py with a working SQLite implementation. This step establishes the data layer foundation for the Spendly application. All future features (authentication, profile, expense tracking) depend on this being correctly implemented.

2. Depends On
Nothing — this is the first step.

3. Routes
* No new routes.
* Existing placeholder routes in app.py remain unchanged.

4. Database Schema

A. Users Table
* id: INTEGER (Primary key, autoincrement)
* name: TEXT (Not null)
* email: TEXT (Unique, not null)
* password_hash: TEXT (Not null)
* created_at: TEXT (Default datetime('now'))

B. Expenses Table
* id: INTEGER (Primary key, autoincrement)
* user_id: INTEGER (Foreign key -> users.id, not null)
* amount: REAL (Not null)
* category: TEXT (Not null)
* date: TEXT (Not null (YYYY-MM-DD format))
* description: TEXT (Nullable)
* created_at: TEXT (Default datetime('now'))

5. Functions to Implement (database/db.py)

A. get_db()
* Opens a connection to spendly.db (or expense_tracker.db) in the project root.
* Sets row_factory = sqlite3.Row.
* Sets PRAGMA foreign_keys = ON.
* Returns the connection.

B. init_db()
* Creates both tables using CREATE TABLE IF NOT EXISTS.
* Safe to call multiple times without failing.
* Ensures the schema is ready before application usage.

C. seed_db()
* Checks if the users table already contains data. Returns early if data exists to prevent duplication.
* Inserts one demo user (Name: Demo User, Email: demo@spendly.com, Password: demo123 hashed using werkzeug).
* Inserts 8 sample expenses linked to the demo user.
* Spreads sample expense dates across the current month.
* Covers multiple categories with at least one expense per category.

6. Changes to app.py
* Import get_db, init_db, and seed_db.
* Call init_db() and seed_db() inside app.app_context() on startup.
* Ensure the database is ready before routes are used.

7. Files to Change
* database/db.py — implement all functions.
* app.py — add imports and startup calls.

8. Files to Create
None.

9. Dependencies
* No new pip packages.
* Use sqlite3 (Python standard library).
* Use werkzeug.security (already installed).

10. Categories (Fixed List)
Use exactly these values:
* Food
* Transport
* Bills
* Health
* Entertainment
* Shopping
* Other

11. Rules for Implementation
* No ORMs: Do not use SQLAlchemy or similar libraries.
* Security: Use parameterized queries only. Never use string formatting in SQL.
* Data Integrity: Enable PRAGMA foreign_keys = ON on every connection.
* Data Types: Store amount as REAL (float), not INTEGER. Dates must follow the YYYY-MM-DD format consistently.
* Authentication: Hash passwords using `from werkzeug.security import generate_password_hash`.
* Idempotency: seed_db() must prevent duplicate inserts.

12. Expected Behavior
* get_db() returns a working connection with dictionary-like row access and foreign key enforcement enabled.
* init_db() creates tables safely and does not fail on repeated runs.
* seed_db() inserts demo data only once and does not duplicate records on multiple runs.
* The database successfully enforces the unique email constraint and valid foreign key relationships.

13. Error Handling Expectations
* Inserting a duplicate email should fail due to the UNIQUE constraint.
* Inserting an expense with an invalid user_id should fail due to the foreign key constraint.
* Invalid queries should raise clear errors for debugging purposes.

14. Definition of Done
* Database file is created on app startup.
* Both tables exist with the correct schema and constraints.
* Demo user exists with a hashed password.
* 8 sample expenses exist across various categories.
* No duplicate seed data is created on repeated runs.
* The app starts without errors.
* Foreign key enforcement works.
* All queries use parameterized SQL.