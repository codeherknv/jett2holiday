"""
Jett 2 Holiday - FastAPI Application Entry Point.
Implements the core REST API contracts for dynamic pricing, factor explainability,
simulation what-if engine, and event telemetry logging.
"""

import sqlite3
from fastapi import FastAPI, Depends, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List

from .database import get_db
from .schemas import (
    PricingCalculateRequest,
    PricingCalculateResponse,
    PricingExplainResponse,
    PricingSimulateRequest,
    PricingSimulateResponse,
    EventLogRequest,
    EventLogResponse,
)
from .mock_data import (
    get_mock_pricing_calculate,
    get_mock_pricing_explain,
    get_mock_pricing_simulate,
    get_mock_event_log,
)

app = FastAPI(
    title="Jett 2 Holiday — Dynamic Pricing & Demand Forecasting API",
    description="Real-time dynamic pricing engine, factor explainability, and what-if simulation for hotels and flights (APS-02).",
    version="0.1.0",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Healthcheck & Discovery
# ==========================================
@app.get("/", tags=["Health"])
def root_status():
    return {
        "service": "Jett 2 Holiday Dynamic Pricing Engine",
        "status": "online",
        "version": "0.1.0",
        "docs_url": "/docs",
        "endpoints": [
            "POST /pricing/calculate",
            "GET /pricing/explain",
            "POST /pricing/simulate",
            "POST /events"
        ]
    }


@app.get("/health", tags=["Health"])
def health_check(db: sqlite3.Connection = Depends(get_db)):
    """
    Verifies service health and SQLite connectivity.
    """
    try:
        cursor = db.cursor()
        cursor.execute("SELECT sqlite_version();")
        version = cursor.fetchone()[0]
        return {"status": "healthy", "database": "connected", "sqlite_version": version}
    except Exception as exc:
        return {"status": "degraded", "database_error": str(exc)}


@app.get("/entities", tags=["Metadata"])
def list_sample_entities(db: sqlite3.Connection = Depends(get_db)):
    """
    Returns available hotel rooms and flight fares for UI dropdown selectors.
    """
    # Quick metadata query for front-end selector
    try:
        cursor = db.cursor()
        cursor.execute("SELECT entity_id, entity_type, floor_price, ceiling_price, max_daily_move_pct FROM price_bounds")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception:
        # Fallback sample entities
        return [
            {
                "entity_id": "htl_sng_001_deluxe",
                "entity_name": "Dal Lake Luxury Heritage Resort (Deluxe)",
                "entity_type": "hotel_room",
                "floor_price": 3500.0,
                "ceiling_price": 7000.0,
                "max_daily_move_pct": 0.15
            },
            {
                "entity_id": "flt_del_srx_101_eco",
                "entity_name": "DEL -> SXR Express (Economy)",
                "entity_type": "flight_fare",
                "floor_price": 4200.0,
                "ceiling_price": 11500.0,
                "max_daily_move_pct": 0.20
            }
        ]


# ==========================================
# 1. Dynamic Pricing Calculation
# ==========================================
@app.post(
    "/pricing/calculate",
    response_model=PricingCalculateResponse,
    tags=["Pricing Engine"],
    summary="Compute dynamic price for an entity on a target date",
)
def calculate_pricing(
    request: PricingCalculateRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Calculates candidate and effective clamped dynamic price using ML demand forecast,
    occupancy ratios, lead time decay, and hard guardrails.
    
    TODO [Phase 2]: Wire real ML model inference & bounds clamping via `db`.
    """
    # Current stub returns realistic mock response matching contract
    return get_mock_pricing_calculate(request.entity_id, request.target_date)


# ==========================================
# 2. Factor Decomposition & Explainability
# ==========================================
@app.get(
    "/pricing/explain",
    response_model=PricingExplainResponse,
    tags=["Explainability"],
    summary="Decompose dynamic price into contributing factors and plain-language reasoning",
)
def explain_pricing(
    entity_id: str = Query(..., examples=["htl_sng_001_deluxe"], description="Unique entity identifier"),
    date: str = Query(..., examples=["2026-10-15"], description="Target date (YYYY-MM-DD)"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Provides full auditability and decomposition of the factors driving a dynamic price shift.
    Returns both English and Hindi audit strings.
    
    TODO [Phase 2]: Retrieve feature contributions from regression model & price_history table.
    """
    return get_mock_pricing_explain(entity_id, date)


# ==========================================
# 3. What-If Scenario Simulation
# ==========================================
@app.post(
    "/pricing/simulate",
    response_model=PricingSimulateResponse,
    tags=["Simulation"],
    summary="Run what-if simulation across a 30-day curve with custom multipliers and move caps",
)
def simulate_pricing(
    request: PricingSimulateRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Simulates rate adjustments across a 30-day forecast horizon under varying
    base multipliers and daily move limits.
    
    TODO [Phase 2]: Execute batch simulation against pre-computed demand curve and save scenario.
    """
    return get_mock_pricing_simulate(
        entity_id=request.entity_id,
        base_multiplier=request.base_multiplier,
        daily_move_limit=request.daily_move_limit
    )


# ==========================================
# 4. Telemetry Event Ingestion
# ==========================================
@app.post(
    "/events",
    response_model=EventLogResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Telemetry & Events"],
    summary="Log search, view, booking, cancellation, or abandonment telemetry",
)
def log_event(
    request: EventLogRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Records an incoming user interaction event to train the real-time demand model.
    
    TODO [Phase 2]: Execute SQL INSERT into pricing_events and update inventory_calendar if booking.
    """
    return get_mock_event_log(
        entity_id=request.entity_id,
        event_type=request.event_type,
        timestamp=request.timestamp,
        lead_time_days=request.lead_time_days
    )
