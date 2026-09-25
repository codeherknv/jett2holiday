"""
Feature engineering for the dynamic-pricing demand model.

Design:
    - Training target comes directly from price_history.demand_index.
    - pricing_events are converted into point-in-time behavioral features.
    - inventory_calendar is used as a future-state feature when available.
    - cities / flights / airlines / hotels / price_bounds provide static/context features.
    - No synthetic "search + 2*view + 4*booking" demand target is created.
    - No future events are allowed to leak into a training row or future forecast row.

Outputs:
    artifacts/features_train.csv
    artifacts/features_forecast.csv
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
ARTIFACT_DIR = PROJECT_DIR / "artifacts"


FORECAST_AS_OF = pd.Timestamp("2026-08-31")
FORECAST_START = pd.Timestamp("2026-09-01")
FORECAST_DAYS = 30

EVENT_WINDOWS = (3, 7, 14, 30)


# ---------------------------------------------------------------------
# Loading / basic utilities
# ---------------------------------------------------------------------

def get_db_path() -> Path:
    """Resolve APS-02.db from the project layout."""
    env_path = os.environ.get("DB_PATH")
    if env_path:
        return Path(env_path)

    project_dir = Path(__file__).resolve().parent.parent
    candidates = [
        project_dir / "data" / "APS-02.db",
        project_dir / "data-model" / "APS-02.db",
        Path(__file__).resolve().parent / "data" / "APS-02.db",
    ]
    for c in candidates:
        if c.exists():
            return c
    return project_dir / "data" / "APS-02.db"


def get_db_connection():
    import sqlite3

    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(
            f"APS-02.db not found at {db_path}. "
            "Set DB_PATH to the SQLite file if it is elsewhere."
        )
    return sqlite3.connect(str(db_path))


def load_table(conn, table_name: str) -> pd.DataFrame:
    return pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)


def clean_dates(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_localize(None)
    return df


def safe_div(a, b):
    """Numeric-safe elementwise division without divide-by-zero warnings."""
    a_num = pd.to_numeric(pd.Series(a), errors="coerce").fillna(0.0)
    b_num = pd.to_numeric(pd.Series(b), errors="coerce").fillna(0.0)
    result = np.zeros(len(a_num), dtype=float)
    mask = b_num.to_numpy() != 0
    if mask.any():
        result[mask] = a_num.to_numpy()[mask] / b_num.to_numpy()[mask]
    return result


# ---------------------------------------------------------------------
# Entity -> city / static metadata
# ---------------------------------------------------------------------

def build_entity_metadata(
    events: pd.DataFrame,
    flight_fares: pd.DataFrame,
    flights: pd.DataFrame,
    airports: pd.DataFrame,
    airlines: pd.DataFrame,
    cities: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build one row of static metadata per entity.

    Room-type entities get their city from the pricing-events city_id
    because there is no room_types CSV in the supplied dataset.

    Flight-fare entities are mapped:
        fare -> flight -> origin airport -> city
    with pricing_events.city_id as a fallback.
    """

    event_city = (
        events.dropna(subset=["entity_id", "city_id"])
        .groupby("entity_id")["city_id"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
        .rename("event_city_id")
        .reset_index()
    )

    fare_meta = flight_fares.merge(
        flights[
            [
                "flight_id",
                "airline_id",
                "origin_airport_id",
                "dest_airport_id",
                "duration_minutes",
                "stops",
            ]
        ],
        on="flight_id",
        how="left",
    ).merge(
        airports[["airport_id", "city_id", "is_international"]].rename(
            columns={
                "airport_id": "origin_airport_id",
                "city_id": "origin_city_id",
                "is_international": "origin_is_international",
            }
        ),
        on="origin_airport_id",
        how="left",
    ).merge(
        airports[["airport_id", "city_id"]].rename(
            columns={
                "airport_id": "dest_airport_id",
                "city_id": "dest_city_id",
            }
        ),
        on="dest_airport_id",
        how="left",
    ).merge(
        airlines[["airline_id", "low_cost", "alliance"]].rename(
            columns={"low_cost": "airline_low_cost", "alliance": "airline_alliance"}
        ),
        on="airline_id",
        how="left",
    )

    fare_meta = fare_meta[
        [
            "fare_id",
            "airline_id",
            "origin_city_id",
            "dest_city_id",
            "duration_minutes",
            "stops",
            "origin_is_international",
            "airline_low_cost",
            "airline_alliance",
            "cabin_class",
            "fare_class",
            "seats_total",
            "base_fare",
            "taxes",
        ]
    ].rename(columns={"fare_id": "entity_id"})

    # Static room-type information available in supplied data is limited
    # to city inferred from pricing events.
    room_meta = event_city.copy()
    room_meta["entity_type"] = "room_type"
    room_meta["city_id"] = room_meta["event_city_id"]
    room_meta = room_meta[["entity_id", "entity_type", "city_id"]]

    flight_entity_meta = fare_meta.copy()
    flight_entity_meta["entity_type"] = "flight_fare"
    flight_entity_meta["city_id"] = flight_entity_meta["origin_city_id"]

    static = pd.concat(
        [
            room_meta,
            flight_entity_meta[
                [
                    "entity_id",
                    "entity_type",
                    "city_id",
                    "origin_city_id",
                    "dest_city_id",
                    "duration_minutes",
                    "stops",
                    "origin_is_international",
                    "airline_low_cost",
                    "airline_alliance",
                    "cabin_class",
                    "fare_class",
                    "seats_total",
                    "base_fare",
                    "taxes",
                ]
            ],
        ],
        ignore_index=True,
    )

    # Event-derived city is the final fallback for entities not present in
    # the fare metadata.
    static = static.merge(event_city, on="entity_id", how="outer")
    static["city_id"] = static["city_id"].fillna(static["event_city_id"])
    static = static.drop(columns=["event_city_id"])

    # Avoid accidental duplicate entity rows.
    static = (
        static.sort_values(["entity_id"])
        .drop_duplicates("entity_id", keep="first")
        .reset_index(drop=True)
    )

    # City attributes.
    city_cols = [
        "city_id",
        "country_id",
        "country_code",
        "region",
        "population",
        "season_profile",
        "peak_months",
        "primary_language",
    ]
    static = static.merge(cities[city_cols], on="city_id", how="left")

    return static


# ---------------------------------------------------------------------
# Point-in-time event features
# ---------------------------------------------------------------------

def build_event_features(
    events: pd.DataFrame,
    entity_dates: pd.DataFrame,
    as_of_cap: pd.Timestamp | None,
) -> pd.DataFrame:
    """
    For every entity/date row, summarize events whose occurred_at is known
    by that row's as-of date and whose for_date matches the row date.

    This deliberately prevents future-event leakage.

    The windows are measured backward from the target date:
        e.g. searches_7d = searches for this entity/target date where the
        event occurred during the 7 days before the target date.

    For a forecast row, as_of_cap is also enforced, so a Sept forecast made
    on Aug 31 cannot see a Sept 10 event that occurs later.
    """

    e = events.copy()
    e["occurred_at"] = pd.to_datetime(e["occurred_at"], errors="coerce", utc=True).dt.tz_localize(None)
    e["for_date"] = pd.to_datetime(e["for_date"], errors="coerce", utc=True).dt.tz_localize(None)
    e = e.dropna(subset=["entity_id", "for_date", "occurred_at"])

    if as_of_cap is not None:
        e = e[e["occurred_at"] <= as_of_cap].copy()

    base = entity_dates[["entity_id", "for_date"]].drop_duplicates().copy()

    # Merge only events belonging to the same entity and target date.
    x = base.merge(
        e,
        on=["entity_id", "for_date"],
        how="left",
        suffixes=("", "_event"),
    )

    x["party_size"] = pd.to_numeric(x["party_size"], errors="coerce")
    x["quoted_price"] = pd.to_numeric(x["quoted_price"], errors="coerce")
    x["converted"] = pd.to_numeric(x["converted"], errors="coerce").fillna(0.0)

    x["days_before_target"] = (
        x["for_date"] - x["occurred_at"].dt.normalize()
    ).dt.days

    # Same-day events are allowed; events after the target date are not.
    x = x[(x["days_before_target"].isna()) | (x["days_before_target"] >= 0)].copy()

    result = base.copy()

    event_types = ["search", "view", "booking", "abandon", "cancellation"]

    for window in EVENT_WINDOWS:
        mask = x["days_before_target"].between(0, window - 1, inclusive="both")

        for event_type in event_types:
            col = f"{'searches' if event_type == 'search' else event_type + 's'}_{window}d"
            vals = (
                x.loc[mask & x["event_type"].eq(event_type)]
                .groupby(["entity_id", "for_date"])
                .size()
                .rename(col)
            )
            result = result.merge(vals, on=["entity_id", "for_date"], how="left")

    # Event-level numeric summaries.
    for window in EVENT_WINDOWS:
        mask = x["days_before_target"].between(0, window - 1, inclusive="both")
        w = x.loc[mask].copy()

        agg = (
            w.groupby(["entity_id", "for_date"])
            .agg(
                total_events=("event_id", "count"),
                avg_party_size=("party_size", "mean"),
                avg_quoted_price=("quoted_price", "mean"),
                booking_conversions=("converted", "sum"),
            )
            .rename(
                columns={
                    "total_events": f"events_{window}d",
                    "avg_party_size": f"avg_party_size_{window}d",
                    "avg_quoted_price": f"avg_quoted_price_{window}d",
                    "booking_conversions": f"conversions_{window}d",
                }
            )
        )
        result = result.merge(agg, on=["entity_id", "for_date"], how="left")

    # Conversion / booking ratios.
    for window in EVENT_WINDOWS:
        searches = result[f"searches_{window}d"]
        views = result[f"views_{window}d"]
        bookings = result[f"bookings_{window}d"]
        conversions = result[f"conversions_{window}d"]

        result[f"booking_rate_{window}d"] = safe_div(bookings, searches + views + 1)
        result[f"conversion_rate_{window}d"] = safe_div(conversions, result[f"events_{window}d"] + 1)

    numeric_cols = [c for c in result.columns if c not in ["entity_id", "for_date"]]
    result[numeric_cols] = result[numeric_cols].fillna(0.0)

    return result


# ---------------------------------------------------------------------
# Inventory features
# ---------------------------------------------------------------------

def build_inventory_features(
    inventory: pd.DataFrame,
    entity_dates: pd.DataFrame,
) -> pd.DataFrame:
    inv = inventory.copy()
    inv["for_date"] = pd.to_datetime(inv["for_date"], errors="coerce", utc=True).dt.tz_localize(None)

    inv = inv[
        [
            "entity_id",
            "for_date",
            "total_units",
            "booked_units",
            "held_units",
            "price",
            "min_stay_nights",
            "closed_to_arrival",
        ]
    ].copy()

    inv["inventory_booking_pct"] = 100.0 * safe_div(
        inv["booked_units"], inv["total_units"]
    )
    inv["inventory_held_pct"] = 100.0 * safe_div(
        inv["held_units"], inv["total_units"]
    )
    inv["inventory_available_units"] = (
        inv["total_units"] - inv["booked_units"] - inv["held_units"]
    )

    # Merge to preserve every requested entity/date.
    out = entity_dates.merge(
        inv,
        on=["entity_id", "for_date"],
        how="left",
    )

    out["has_inventory_snapshot"] = out["total_units"].notna().astype(int)

    numeric = [
        "total_units",
        "booked_units",
        "held_units",
        "price",
        "min_stay_nights",
        "inventory_booking_pct",
        "inventory_held_pct",
        "inventory_available_units",
    ]
    out[numeric] = out[numeric].fillna(0.0)
    out["closed_to_arrival"] = out["closed_to_arrival"].fillna(False).astype(int)

    return out


# ---------------------------------------------------------------------
# Price / bounds features
# ---------------------------------------------------------------------

def build_price_features(
    price_history: pd.DataFrame,
    price_bounds: pd.DataFrame,
    inventory: pd.DataFrame,
    train_dates: pd.DataFrame,
    future_dates: pd.DataFrame,
    as_of_date: pd.Timestamp = FORECAST_AS_OF,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build one price feature set that is available in both train and forecast.

    Training:
        current_price = observed price_history.price for that date.

    Forecast:
        current_price = inventory_calendar.price when present.
        Otherwise fall back to the latest known historical price at or before
        FORECAST_AS_OF, with midpoint(floor, ceiling) as a final fallback.

    This avoids a train/future availability mismatch while still using the
    future inventory price signal where it actually exists.
    """

    bounds = price_bounds[
        [
            "entity_id",
            "floor_price",
            "ceiling_price",
            "max_daily_move_pct",
            "max_weekly_move_pct",
            "rounding_step",
            "override_active",
        ]
    ].copy()

    # --- Training observed price ---
    ph = price_history[["entity_id", "effective_date", "price"]].copy()
    ph["effective_date"] = pd.to_datetime(
        ph["effective_date"], errors="coerce", utc=True
    ).dt.tz_localize(None)
    ph["price"] = pd.to_numeric(ph["price"], errors="coerce")

    train_out = train_dates.copy()
    train_out = train_out.merge(
        ph.rename(columns={"effective_date": "for_date", "price": "current_price"}),
        on=["entity_id", "for_date"],
        how="left",
    )
    train_out = train_out.merge(bounds, on="entity_id", how="left")

    # --- Forecast price ---
    inv = inventory[["entity_id", "for_date", "price"]].copy()
    inv["for_date"] = pd.to_datetime(
        inv["for_date"], errors="coerce", utc=True
    ).dt.tz_localize(None)
    inv["price"] = pd.to_numeric(inv["price"], errors="coerce")
    inv = inv.rename(columns={"price": "inventory_price"})

    future_out = future_dates.copy().merge(
        inv, on=["entity_id", "for_date"], how="left"
    )
    future_out = future_out.merge(bounds, on="entity_id", how="left")

    latest = (
        ph[ph["effective_date"] <= pd.Timestamp(as_of_date)]
        .sort_values(["entity_id", "effective_date"])
        .drop_duplicates("entity_id", keep="last")
        [["entity_id", "price"]]
        .rename(columns={"price": "latest_historical_price"})
    )
    future_out = future_out.merge(latest, on="entity_id", how="left")

    midpoint = (
        pd.to_numeric(future_out["floor_price"], errors="coerce")
        + pd.to_numeric(future_out["ceiling_price"], errors="coerce")
    ) / 2.0

    future_out["current_price"] = (
        future_out["inventory_price"]
        .combine_first(future_out["latest_historical_price"])
        .combine_first(midpoint)
    )

    # Same engineered price relationships for both datasets.
    for df in (train_out, future_out):
        df["price_floor_ratio"] = safe_div(
            df["current_price"], df["floor_price"]
        )
        df["price_ceiling_ratio"] = safe_div(
            df["current_price"], df["ceiling_price"]
        )

    future_out["has_inventory_price"] = future_out["inventory_price"].notna().astype(int)

    train_out = train_out.drop(
        columns=["inventory_price", "latest_historical_price"], errors="ignore"
    )
    future_out = future_out.drop(
        columns=["inventory_price", "latest_historical_price"], errors="ignore"
    )

    return train_out, future_out


# ---------------------------------------------------------------------
# Calendar features
# ---------------------------------------------------------------------

def add_calendar_features(
    df: pd.DataFrame,
    forecast_as_of: pd.Timestamp = FORECAST_AS_OF,
) -> pd.DataFrame:
    out = df.copy()
    d = out["for_date"]

    out["day_of_week"] = d.dt.weekday
    out["day_of_month"] = d.dt.day
    out["day_of_year"] = d.dt.dayofyear
    out["week_of_year"] = d.dt.isocalendar().week.astype(int)
    out["month"] = d.dt.month
    out["is_weekend"] = (d.dt.weekday >= 5).astype(int)
    out["is_month_start"] = d.dt.is_month_start.astype(int)
    out["is_month_end"] = d.dt.is_month_end.astype(int)
    out["days_from_forecast_as_of"] = (d - pd.Timestamp(forecast_as_of)).dt.days

    def parse_peak_months(value):
        if pd.isna(value):
            return set()
        return {
            int(x.strip())
            for x in str(value).split(",")
            if x.strip().isdigit() and 1 <= int(x.strip()) <= 12
        }

    out["_peak_month_set"] = out["peak_months"].map(parse_peak_months) if "peak_months" in out.columns else pd.Series([set()] * len(out), index=out.index)
    out["is_peak_month"] = [
        int(month in peaks)
        for month, peaks in zip(d.dt.month, out["_peak_month_set"])
    ]
    out = out.drop(columns=["_peak_month_set"], errors="ignore")

    return out


# ---------------------------------------------------------------------
# Main feature construction
# ---------------------------------------------------------------------

def build_features(
    forecast_as_of: pd.Timestamp = FORECAST_AS_OF,
    forecast_start: pd.Timestamp = FORECAST_START,
    forecast_days: int = FORECAST_DAYS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    print("Loading raw tables from APS-02.db...")

    conn = get_db_connection()
    try:
        currencies = load_table(conn, "currencies")
        inventory = load_table(conn, "inventory_calendar")
        languages = load_table(conn, "languages")
        bounds = load_table(conn, "price_bounds")
        price_history = load_table(conn, "price_history")
        countries = load_table(conn, "countries")
        airlines = load_table(conn, "airlines")
        cities = load_table(conn, "cities")
        hotels = load_table(conn, "hotels")
        events = load_table(conn, "pricing_events")
        airports = load_table(conn, "airports")
        flights = load_table(conn, "flights")
        fares = load_table(conn, "flight_fares")
    finally:
        conn.close()

    print(
        "Loaded:",
        f"price_history={len(price_history):,},",
        f"pricing_events={len(events):,},",
        f"inventory={len(inventory):,},",
        f"flight_fares={len(fares):,}",
    )

    # Date cleanup.
    price_history = clean_dates(price_history, ["effective_date", "computed_at"])
    inventory = clean_dates(inventory, ["for_date", "updated_at"])
    events = clean_dates(events, ["occurred_at", "for_date"])

    # ---------------------------------------------------------------
    # Training base = actual historical demand_index rows.
    # ---------------------------------------------------------------
    train = price_history[
        [
            "entity_type",
            "entity_id",
            "effective_date",
            "demand_index",
        ]
    ].copy()

    train = train.rename(columns={"effective_date": "for_date"})

    # ---------------------------------------------------------------
    # Forecast base = entities with historical targets x next 30 days.
    # ---------------------------------------------------------------
    target_entities = (
        train[["entity_type", "entity_id"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    future_dates = pd.DataFrame(
        {
            "for_date": pd.date_range(
                pd.Timestamp(forecast_start),
                periods=forecast_days,
                freq="D",
            )
        }
    )

    future = target_entities.merge(future_dates, how="cross")

    # ---------------------------------------------------------------
    # Static metadata.
    # ---------------------------------------------------------------
    static = build_entity_metadata(
        events=events,
        flight_fares=fares,
        flights=flights,
        airports=airports,
        airlines=airlines,
        cities=cities,
    )

    train = train.merge(static, on=["entity_id", "entity_type"], how="left")
    future = future.merge(static, on=["entity_id", "entity_type"], how="left")

    # ---------------------------------------------------------------
    # Point-in-time event features.
    # ---------------------------------------------------------------
    def build_rowwise_events(
        base: pd.DataFrame,
        cap_mode: str,
        as_of_date: pd.Timestamp,
    ) -> pd.DataFrame:
        e = events[
            [
                "event_id",
                "entity_id",
                "event_type",
                "occurred_at",
                "for_date",
                "party_size",
                "quoted_price",
                "converted",
            ]
        ].copy()

        e["party_size"] = pd.to_numeric(e["party_size"], errors="coerce").fillna(0.0)
        e["quoted_price"] = pd.to_numeric(e["quoted_price"], errors="coerce").fillna(0.0)
        e["converted"] = pd.to_numeric(e["converted"], errors="coerce").fillna(0.0)

        base2 = base[["entity_id", "for_date"]].drop_duplicates().copy()
        x = base2.merge(e, on=["entity_id", "for_date"], how="left")
        x["days_before_target"] = (
            x["for_date"] - x["occurred_at"].dt.normalize()
        ).dt.days

        # Events after the target date are never usable.
        x = x[x["days_before_target"].ge(0) | x["days_before_target"].isna()].copy()

        if cap_mode == "historical":
            x = x[x["occurred_at"] <= x["for_date"]]
        elif cap_mode == "forecast":
            x = x[x["occurred_at"] <= pd.Timestamp(as_of_date)]

        result = base2.copy()

        types = ["search", "view", "booking", "abandon", "cancellation"]
        for window in EVENT_WINDOWS:
            mask = x["days_before_target"].between(0, window - 1, inclusive="both")
            for t in types:
                col = f"{'searches' if t == 'search' else t + 's'}_{window}d"
                s = (
                    x.loc[mask & x["event_type"].eq(t)]
                    .groupby(["entity_id", "for_date"])
                    .size()
                    .rename(col)
                )
                if s.empty:
                    result[col] = 0.0
                else:
                    result = result.merge(s, on=["entity_id", "for_date"], how="left")

            w = x.loc[mask]
            if w.empty:
                result[f"events_{window}d"] = 0.0
                result[f"avg_party_size_{window}d"] = 0.0
                result[f"avg_quoted_price_{window}d"] = 0.0
                result[f"conversions_{window}d"] = 0.0
            else:
                agg = (
                    w.groupby(["entity_id", "for_date"])
                    .agg(
                        events=("event_id", "count"),
                        avg_party_size=("party_size", "mean"),
                        avg_quoted_price=("quoted_price", "mean"),
                        conversions=("converted", "sum"),
                    )
                    .rename(
                        columns={
                            "events": f"events_{window}d",
                            "avg_party_size": f"avg_party_size_{window}d",
                            "avg_quoted_price": f"avg_quoted_price_{window}d",
                            "conversions": f"conversions_{window}d",
                        }
                    )
                )
                result = result.merge(agg, on=["entity_id", "for_date"], how="left")

            searches = result[f"searches_{window}d"].fillna(0)
            views = result[f"views_{window}d"].fillna(0)
            bookings = result[f"bookings_{window}d"].fillna(0)
            conversions = result[f"conversions_{window}d"].fillna(0)

            result[f"booking_rate_{window}d"] = safe_div(
                bookings, searches + views + 1
            )
            result[f"conversion_rate_{window}d"] = safe_div(
                conversions, result[f"events_{window}d"].fillna(0) + 1
            )

        numeric = [c for c in result.columns if c not in ["entity_id", "for_date"]]
        result[numeric] = result[numeric].fillna(0.0)
        return result

    train_events = build_rowwise_events(train, "historical", forecast_as_of)
    future_events = build_rowwise_events(future, "forecast", forecast_as_of)

    train = train.merge(train_events, on=["entity_id", "for_date"], how="left")
    future = future.merge(future_events, on=["entity_id", "for_date"], how="left")

    # ---------------------------------------------------------------
    # Bounds / prices.
    # ---------------------------------------------------------------
    train_price, future_price = build_price_features(
        price_history=price_history,
        price_bounds=bounds,
        inventory=inventory,
        train_dates=train[["entity_id", "for_date"]],
        future_dates=future[["entity_id", "for_date"]],
        as_of_date=forecast_as_of,
    )

    train = train.merge(
        train_price, on=["entity_id", "for_date"], how="left"
    )
    future = future.merge(
        future_price, on=["entity_id", "for_date"], how="left"
    )

    # ---------------------------------------------------------------
    # Calendar.
    # ---------------------------------------------------------------
    train = add_calendar_features(train, forecast_as_of)
    future = add_calendar_features(future, forecast_as_of)

    # ---------------------------------------------------------------
    # Clean numeric columns.
    # ---------------------------------------------------------------
    for df in (train, future):
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
        df[numeric_cols] = df[numeric_cols].fillna(0.0)

        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].fillna("unknown")

    # ---------------------------------------------------------------
    # Final feature selection.
    # ---------------------------------------------------------------
    banned_features = {
        "occupancy_pct",
        "lead_time_factor",
        "seasonality_factor",
        "event_factor",
        "competitor_factor",
        "baseline_price",
        "price",
        "historical_price",
        "historical_baseline_price",
        "total_units",
        "booked_units",
        "held_units",
        "inventory_booking_pct",
        "inventory_held_pct",
        "inventory_available_units",
        "has_inventory_snapshot",
        "closed_to_arrival",
        "min_stay_nights",
    }
    train = train.drop(columns=[c for c in banned_features if c in train.columns], errors="ignore")
    future = future.drop(columns=[c for c in banned_features if c in future.columns], errors="ignore")

    key_cols = {"entity_type", "entity_id", "for_date"}
    candidate_cols = [
        c for c in train.columns
        if c not in key_cols and c != "demand_index" and c in future.columns
    ]
    constant_train = [
        c for c in candidate_cols
        if train[c].nunique(dropna=True) <= 1
    ]
    train = train.drop(columns=constant_train, errors="ignore")
    future = future.drop(columns=constant_train, errors="ignore")

    shared_features = [
        c for c in train.columns
        if c in future.columns and c not in {"demand_index"}
    ]
    train = train[["entity_type", "entity_id", "for_date", "demand_index"] + [
        c for c in shared_features
        if c not in {"entity_type", "entity_id", "for_date", "demand_index"}
    ]]
    future = future[["entity_type", "entity_id", "for_date"] + [
        c for c in shared_features
        if c not in {"entity_type", "entity_id", "for_date", "demand_index"}
    ]]

    train = train.sort_values(["entity_type", "entity_id", "for_date"]).reset_index(drop=True)
    future = future.sort_values(["entity_type", "entity_id", "for_date"]).reset_index(drop=True)

    return train, future


def print_diagnostics(train: pd.DataFrame, future: pd.DataFrame) -> None:
    """Print and persist feature and future-availability diagnostics."""
    print("\n========== TRAINING FEATURES ==========")
    print(f"Rows: {len(train):,}")
    print(f"Entities: {train.entity_id.nunique():,}")
    print(f"Date range: {train.for_date.min().date()} -> {train.for_date.max().date()}")
    print(f"Features: {train.shape[1]}")
    print("Shared predictors:", train.shape[1] - 4)
    print("\nTarget demand_index:")
    print(train["demand_index"].describe())
    print(f"\nTarget missing: {train['demand_index'].isna().sum():,}")

    print("\n========== FORECAST FEATURES ==========")
    print(f"Rows: {len(future):,}")
    print(f"Entities: {future.entity_id.nunique():,}")
    print(f"Date range: {future.for_date.min().date()} -> {future.for_date.max().date()}")

    key_cols = {"entity_type", "entity_id", "for_date", "demand_index"}
    audit_rows = []
    all_cols = list(dict.fromkeys(list(train.columns) + list(future.columns)))

    for col in all_cols:
        tr_exists = col in train.columns
        fu_exists = col in future.columns
        tr = train[col] if tr_exists else pd.Series(dtype="float64")
        fu = future[col] if fu_exists else pd.Series(dtype="float64")
        audit_rows.append({
            "feature": col,
            "train_dtype": str(tr.dtype) if tr_exists else "missing",
            "future_dtype": str(fu.dtype) if fu_exists else "missing",
            "train_missing_pct": round(float(tr.isna().mean() * 100), 2) if tr_exists else 100.0,
            "future_missing_pct": round(float(fu.isna().mean() * 100), 2) if fu_exists else 100.0,
            "train_unique": int(tr.nunique(dropna=True)) if tr_exists else 0,
            "future_unique": int(fu.nunique(dropna=True)) if fu_exists else 0,
            "train_constant": bool(tr.nunique(dropna=True) <= 1) if tr_exists else True,
            "future_constant": bool(fu.nunique(dropna=True) <= 1) if fu_exists else True,
            "future_available": bool(fu_exists and fu.notna().any()),
            "is_key_or_target": col in key_cols,
        })

    audit = pd.DataFrame(audit_rows)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    audit_path = ARTIFACT_DIR / "feature_audit.csv"
    audit.to_csv(audit_path, index=False)

    print("\n========== FEATURE AUDIT ==========")
    print(f"Audit saved: {audit_path}")


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    train, future = build_features()
    print_diagnostics(train, future)

    train_path = ARTIFACT_DIR / "features_train.csv"
    future_path = ARTIFACT_DIR / "features_forecast.csv"

    train.to_csv(train_path, index=False)
    future.to_csv(future_path, index=False)

    print("\nSaved:")
    print(train_path)
    print(future_path)


if __name__ == "__main__":
    main()
