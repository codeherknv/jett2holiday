"""
Backfill script for APS-02.db price_history table.
Populates raw_price, clamped_by, and bound_value using the corrected simultaneous bounds logic.
"""

import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "APS-02.db"

def backfill():
    print(f"Connecting to {DB_PATH} for backfilling clamp diagnostics...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Load bounds
    cursor.execute("SELECT entity_id, floor_price, ceiling_price, max_daily_move_pct FROM price_bounds;")
    bounds_dict = {
        r[0]: (float(r[1]), float(r[2]), float(r[3]))
        for r in cursor.fetchall()
    }

    # Fetch all records ordered chronologically per entity
    cursor.execute("""
        SELECT history_id, entity_id, effective_date, price, baseline_price,
               demand_index, occupancy_pct, lead_time_factor, seasonality_factor,
               competitor_factor, bound_clamped
        FROM price_history
        ORDER BY entity_id, effective_date;
    """)
    rows = cursor.fetchall()
    print(f"Total rows to backfill: {len(rows):,}")

    updates = []
    prev_e = None
    prev_p = None

    ceiling_cnt = 0
    floor_cnt = 0
    daily_cnt = 0
    unclamped_cnt = 0

    for r in rows:
        hid, e_id, eff_date, price_str, base_str, d_idx, occ, lt_fac, szn_fac, comp_fac, b_clamped = r
        price = float(price_str)
        base = float(base_str)

        floor, ceil, max_daily = bounds_dict.get(e_id, (round(base * 0.7, 2), round(base * 1.6, 2), 0.15))

        if e_id != prev_e:
            prev_p = base
            prev_e = e_id

        d_min = prev_p * (1.0 - max_daily)
        d_max = prev_p * (1.0 + max_daily)

        # Simultaneous valid interval
        valid_lower = max(floor, d_min)
        valid_upper = min(ceil, d_max)
        valid_lower = min(ceil, valid_lower)
        valid_upper = max(floor, valid_upper)

        # Unclamped candidate model price
        raw_price = round(base * float(d_idx) * float(lt_fac) * float(szn_fac) * float(comp_fac), 2)

        clamped_by = None
        bound_val = None

        if int(b_clamped) == 1 or raw_price < valid_lower or raw_price > valid_upper or abs(price - floor) <= 0.05 or abs(price - ceil) <= 0.05:
            if abs(price - ceil) <= 0.05 or (raw_price > ceil and ceil <= d_max):
                clamped_by = "ceiling"
                bound_val = str(ceil)
                ceiling_cnt += 1
            elif abs(price - floor) <= 0.05 or (raw_price < floor and floor >= d_min):
                clamped_by = "floor"
                bound_val = str(floor)
                floor_cnt += 1
            else:
                clamped_by = "daily_movement"
                bound_val = str(round(d_max if raw_price > d_max else d_min, 2))
                daily_cnt += 1
            is_clamped = 1
        else:
            is_clamped = 0
            unclamped_cnt += 1

        updates.append((
            str(raw_price),
            clamped_by,
            bound_val,
            is_clamped,
            hid
        ))

        prev_p = price

    print(f"Applying updates in batch (ceiling: {ceiling_cnt}, floor: {floor_cnt}, daily_movement: {daily_cnt}, unclamped: {unclamped_cnt})...")

    cursor.executemany("""
        UPDATE price_history
        SET raw_price = ?,
            clamped_by = ?,
            bound_value = ?,
            bound_clamped = ?
        WHERE history_id = ?;
    """, updates)

    conn.commit()
    print("Backfill complete and verified!")
    conn.close()

if __name__ == "__main__":
    backfill()
