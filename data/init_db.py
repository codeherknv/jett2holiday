"""
Database Initializer for APS-02.db
Creates schema tables and sample baseline records for Jett 2 Holiday if APS-02.db is not present.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "APS-02.db")

SCHEMA_SQL = """
-- Cities
CREATE TABLE IF NOT EXISTS cities (
    city_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT,
    peak_months TEXT, -- e.g. "04,05,10,11"
    season_profile TEXT
);

-- Hotels
CREATE TABLE IF NOT EXISTS hotels (
    hotel_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city_id TEXT REFERENCES cities(city_id),
    star_rating REAL,
    property_type TEXT
);

-- Flights
CREATE TABLE IF NOT EXISTS flights (
    flight_id TEXT PRIMARY KEY,
    flight_number TEXT NOT NULL,
    origin_city_id TEXT REFERENCES cities(city_id),
    destination_city_id TEXT REFERENCES cities(city_id),
    departure_time TEXT
);

CREATE TABLE IF NOT EXISTS flight_fares (
    fare_id TEXT PRIMARY KEY,
    flight_id TEXT REFERENCES flights(flight_id),
    cabin_class TEXT,
    base_fare REAL
);

-- Price Bounds & Guardrails
CREATE TABLE IF NOT EXISTS price_bounds (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL, -- 'hotel_room' or 'flight_fare'
    floor_price REAL NOT NULL,
    ceiling_price REAL NOT NULL,
    max_daily_move_pct REAL NOT NULL DEFAULT 0.15,
    rounding_step REAL DEFAULT 10.0,
    manual_override_flag INTEGER DEFAULT 0
);

-- Inventory Calendar
CREATE TABLE IF NOT EXISTS inventory_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    target_date TEXT NOT NULL,
    total_capacity INTEGER NOT NULL,
    booked_units INTEGER NOT NULL DEFAULT 0,
    UNIQUE(entity_id, target_date)
);

-- Pricing Events (Search, View, Booking, Cancellation, Abandonment)
CREATE TABLE IF NOT EXISTS pricing_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'search', 'view', 'booking', 'cancellation', 'abandon'
    timestamp TEXT NOT NULL,
    lead_time_days INTEGER DEFAULT 0
);

-- Price History
CREATE TABLE IF NOT EXISTS price_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    target_date TEXT NOT NULL,
    base_price REAL NOT NULL,
    effective_price REAL NOT NULL,
    demand_index REAL,
    occupancy_factor REAL,
    lead_time_factor REAL,
    seasonality_factor REAL,
    bound_clamped INTEGER DEFAULT 0,
    explanation_en TEXT,
    explanation_hi TEXT,
    simulated_scenario_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Currencies & Languages
CREATE TABLE IF NOT EXISTS currencies (
    currency_code TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    minor_unit INTEGER DEFAULT 2
);

CREATE TABLE IF NOT EXISTS languages (
    locale_code TEXT PRIMARY KEY, -- 'en-IN', 'hi'
    name TEXT NOT NULL
);

-- Simulations
CREATE TABLE IF NOT EXISTS simulations (
    simulation_id TEXT PRIMARY KEY,
    name TEXT,
    entity_id TEXT,
    factor_deltas TEXT, -- JSON string
    projected_revenue_delta REAL,
    projected_booking_rate_delta REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SAMPLE_DATA_SQL = """
-- Sample Cities
INSERT OR IGNORE INTO cities (city_id, name, state, peak_months, season_profile) VALUES
('srinagar', 'Srinagar', 'Jammu & Kashmir', '04,05,09,10,11,12', 'Autumn & Snow Peak'),
('goa', 'Goa', 'Goa', '11,12,01,02', 'Winter Beach Peak'),
('delhi', 'New Delhi', 'Delhi', '10,11,12,01,02', 'Winter High Season');

-- Sample Hotels
INSERT OR IGNORE INTO hotels (hotel_id, name, city_id, star_rating, property_type) VALUES
('htl_sng_001', 'Dal Lake Luxury Heritage Resort', 'srinagar', 5.0, 'Heritage Resort'),
('htl_goa_002', 'Candolim Bay Boutique Villa', 'goa', 4.5, 'Boutique Resort');

-- Sample Price Bounds
INSERT OR IGNORE INTO price_bounds (entity_id, entity_type, floor_price, ceiling_price, max_daily_move_pct, rounding_step) VALUES
('htl_sng_001_deluxe', 'hotel_room', 3500.0, 7000.0, 0.15, 50.0),
('flt_del_srx_101_eco', 'flight_fare', 4200.0, 11500.0, 0.20, 100.0);

-- Sample Languages
INSERT OR IGNORE INTO languages (locale_code, name) VALUES
('en-IN', 'English (India)'),
('hi', 'Hindi');

-- Sample Currencies
INSERT OR IGNORE INTO currencies (currency_code, symbol, minor_unit) VALUES
('INR', '₹', 0);
"""


def init_database(db_path=DB_PATH):
    print(f"Initializing SQLite database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_SQL)
    cursor.executescript(SAMPLE_DATA_SQL)
    conn.commit()
    conn.close()
    print("Database schema and baseline seed records created successfully.")


if __name__ == "__main__":
    init_database()
