"""
Migration: Add Guardrail Clamp Report columns and simulations table to APS-02.db.
Adds raw_price, clamped_by, bound_value, and simulated_scenario_id to price_history.
Also creates simulations table for segregated What-If scenarios.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "APS-02.db"

def migrate():
    print(f"Connecting to {DB_PATH} for schema migration...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Inspect existing columns in price_history
    cursor.execute("PRAGMA table_info(price_history);")
    existing_cols = {row[1] for row in cursor.fetchall()}
    print(f"Existing columns in price_history ({len(existing_cols)}): {sorted(list(existing_cols))}")

    # Columns to add to price_history
    new_columns = [
        ("raw_price", "TEXT"),
        ("clamped_by", "TEXT"),
        ("bound_value", "TEXT"),
        ("simulated_scenario_id", "TEXT")
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            print(f"Adding column '{col_name} ({col_type})' to price_history...")
            cursor.execute(f"ALTER TABLE price_history ADD COLUMN {col_name} {col_type};")
        else:
            print(f"Column '{col_name}' already exists in price_history.")

    # 2. Ensure simulations table exists for segregated what-if runs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            simulation_id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            base_multiplier REAL NOT NULL,
            daily_move_limit REAL NOT NULL,
            revenue_delta_pct REAL,
            booking_rate_delta_pct REAL,
            total_clamped INTEGER,
            ceiling_clamps INTEGER,
            floor_clamps INTEGER,
            daily_clamps INTEGER,
            created_at TEXT NOT NULL
        );
    """)
    print("Ensured simulations table exists.")

    conn.commit()

    # Verify migration
    cursor.execute("PRAGMA table_info(price_history);")
    updated_cols = [f"{row[1]} ({row[2]})" for row in cursor.fetchall()]
    print(f"\nMigration successful! Updated price_history columns:\n{', '.join(updated_cols)}")

    conn.close()

if __name__ == "__main__":
    migrate()
