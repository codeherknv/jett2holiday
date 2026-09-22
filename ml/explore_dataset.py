"""
Dataset Exploration Script for APS-02.db (Jett 2 Holiday).
Inspects tables, schemas, row counts, and sample distributions.
Uses pandas.read_sql when available with graceful fallback to sqlite3.
"""

import sys
import os
import sqlite3
from pathlib import Path

# Resolve path to database
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "APS-02.db"

TARGET_TABLES = [
    "pricing_events",
    "inventory_calendar",
    "price_bounds",
    "hotels",
    "flights",
    "flight_fares",
    "cities",
    "price_history",
    "currencies",
    "languages",
    "simulations",
]


def explore_with_pandas(conn):
    import pandas as pd

    print("=" * 70)
    print("[APS-02.db Dataset Overview - Pandas Engine]")
    print("=" * 70)

    for table in TARGET_TABLES:
        try:
            count_df = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table};", conn)
            count = count_df.iloc[0]["count"]

            print(f"\n>> Table: [ {table.upper()} ] - Total Rows: {count:,}")
            
            schema_df = pd.read_sql_query(f"PRAGMA table_info({table});", conn)
            columns_summary = [f"{row['name']} ({row['type']})" for _, row in schema_df.iterrows()]
            print(f"   Columns: {', '.join(columns_summary)}")

            if count > 0:
                sample_df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 3;", conn)
                print("   Sample Rows:")
                print(sample_df.to_string(index=False))
            else:
                print("   (Table is currently empty - ready for ingestion)")
                
        except Exception as exc:
            print(f"   [WARN] Could not inspect table '{table}': {exc}")

    print("\n" + "=" * 70)
    print("Exploration complete.")
    print("TODO [Phase 2 - Feature Engineering]:")
    print(" 1. Apply IQR clipping to handle deliberate ~1% rate outliers in pricing_events.")
    print(" 2. Compute recency decay exp(-k_r * days_since_event) & booking commitment scores.")
    print(" 3. Train Prophet / Linear Regression for 30-day forward demand index generation.")
    print("=" * 70)


def explore_with_sqlite3(conn):
    cursor = conn.cursor()
    print("=" * 70)
    print("[APS-02.db Dataset Overview - Standard SQLite Engine]")
    print("=" * 70)

    for table in TARGET_TABLES:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"\n>> Table: [ {table.upper()} ] - Total Rows: {count:,}")

            cursor.execute(f"PRAGMA table_info({table});")
            columns = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
            print(f"   Columns: {', '.join(columns)}")

            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
                rows = cursor.fetchall()
                print(f"   Sample Rows ({len(rows)}): {repr(rows).encode('ascii', 'backslashreplace').decode('ascii')}")
            else:
                print("   (Table is currently empty - ready for ingestion)")
        except Exception as exc:
            print(f"   [WARN] Could not inspect table '{table}': {exc}")

    print("\n" + "=" * 70)
    print("Exploration complete.")
    print("=" * 70)


def main():
    if not DB_PATH.exists():
        print(f"[ERROR] Database file not found at {DB_PATH}")
        print("Please run `python data/init_db.py` to create the schema.")
        return

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    try:
        # Check if pandas is available
        import pandas  # noqa: F401
        explore_with_pandas(conn)
    except ImportError:
        print("[INFO] pandas is not installed in the current environment; running with built-in sqlite3.")
        explore_with_sqlite3(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

