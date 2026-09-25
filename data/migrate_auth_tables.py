"""
Migration script for Jett 2 Holiday:
1. Creates the new `users` table for traveller authentication with bcrypt password hashes.
2. Performs an additive migration on `pricing_events` by adding a nullable `user_id TEXT` column.
Leaves all other existing columns, rows, and core tables untouched.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "APS-02.db")


def run_migration():
    print(f"Connecting to SQLite database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create `users` table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    print("[SUCCESS] Verified/created `users` table.")

    # 2. Check and add `user_id` column to `pricing_events`
    cursor.execute("PRAGMA table_info(pricing_events);")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE pricing_events ADD COLUMN user_id TEXT;")
        print("[SUCCESS] Added nullable `user_id TEXT` column to `pricing_events`.")
    else:
        print("[INFO] `user_id` column already exists in `pricing_events`.")

    conn.commit()

    # Verify table schema
    cursor.execute("PRAGMA table_info(users);")
    users_cols = [(col[1], col[2], col[3]) for col in cursor.fetchall()]
    print(f"[VERIFY] users columns: {users_cols}")

    cursor.execute("PRAGMA table_info(pricing_events);")
    pe_cols = [(col[1], col[2]) for col in cursor.fetchall()]
    print(f"[VERIFY] pricing_events columns: {pe_cols}")

    conn.close()
    print("[COMPLETE] Migration successfully executed.")


if __name__ == "__main__":
    run_migration()
