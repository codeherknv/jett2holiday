"""
Jett 2 Holiday - FastAPI Application Entry Point.
Implements the core REST API contracts for dynamic pricing, factor explainability,
simulation what-if engine, and event telemetry logging.
"""

import sqlite3
import datetime
from fastapi import FastAPI, Depends, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List

from .database import get_db
from .pricing_engine import pricing_engine
from .schemas import (
    PricingCalculateRequest,
    PricingCalculateResponse,
    PricingExplainResponse,
    PricingSimulateRequest,
    PricingSimulateResponse,
    EventLogRequest,
    EventLogResponse,
    PricingOverrideRequest,
    PricingOverrideResponse,
)
from .auth import (
    AdminLoginRequest,
    TravellerSignupRequest,
    TravellerLoginRequest,
    AuthTokenResponse,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    hash_password,
    verify_password,
    create_access_token,
    require_admin,
    require_traveller,
    validate_email_format,
)


app = FastAPI(
    title="Jett 2 Holiday — Dynamic Pricing & Demand Forecasting API",
    description="Real-time dynamic pricing engine, factor explainability, guardrail clamp diagnostics, and what-if simulation for hotels and flights (APS-02).",
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
            "GET /pricing/horizon",
            "POST /pricing/simulate",
            "POST /pricing/override",
            "GET /pricing/overrides",
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


# ==========================================
# Authentication Endpoints
# ==========================================
@app.post(
    "/auth/admin/login",
    response_model=AuthTokenResponse,
    tags=["Authentication"],
    summary="Authenticate admin with single server-side hackathon account",
)
def admin_login(request: AdminLoginRequest):
    """
    Validates hardcoded admin credentials (admin / admin@123).
    Issues signed JWT with role='admin' on success.
    """
    if request.username != ADMIN_USERNAME or request.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": "admin", "role": "admin", "name": "System Administrator"})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        role="admin",
        user_id="usr_admin",
        display_name="System Administrator",
        email="admin@jett2holiday.internal"
    )


@app.post(
    "/auth/signup",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register a new traveller account with bcrypt password hashing",
)
def traveller_signup(
    request: TravellerSignupRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Validates email format, password length, hashes password with bcrypt,
    creates row in users table with opaque ID, and returns JWT with role='traveller'.
    """
    if not validate_email_format(request.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format.")
    if len(request.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters.")

    clean_email = request.email.strip().lower()
    cursor = db.cursor()
    cursor.execute("SELECT user_id FROM users WHERE email = ? LIMIT 1;", (clean_email,))
    if cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    import uuid
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    hashed_pw = hash_password(request.password)
    now_iso = datetime.datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO users (user_id, email, password_hash, display_name, created_at)
        VALUES (?, ?, ?, ?, ?);
    """, (user_id, clean_email, hashed_pw, request.display_name.strip(), now_iso))
    db.commit()

    token = create_access_token({"sub": user_id, "role": "traveller", "name": request.display_name.strip()})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        role="traveller",
        user_id=user_id,
        display_name=request.display_name.strip(),
        email=clean_email
    )


@app.post(
    "/auth/login",
    response_model=AuthTokenResponse,
    tags=["Authentication"],
    summary="Authenticate existing traveller",
)
def traveller_login(
    request: TravellerLoginRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Validates traveller credentials via bcrypt and issues signed JWT with role='traveller'.
    """
    clean_email = request.email.strip().lower()
    cursor = db.cursor()
    cursor.execute("SELECT user_id, email, password_hash, display_name FROM users WHERE email = ? LIMIT 1;", (clean_email,))
    row = cursor.fetchone()
    if not row or not verify_password(request.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": row["user_id"], "role": "traveller", "name": row["display_name"]})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        role="traveller",
        user_id=row["user_id"],
        display_name=row["display_name"],
        email=row["email"]
    )


@app.get("/entities", dependencies=[Depends(require_admin)], tags=["Metadata"])
def list_entities(db: sqlite3.Connection = Depends(get_db)):

    """
    Returns hotel room types and flight fares from APS-02.db for UI dropdown selectors.
    """
    try:
        cursor = db.cursor()
        
        # 1. Fetch real flight fares with airlines and flight numbers
        cursor.execute("""
            SELECT pb.entity_id, pb.entity_type, pb.floor_price, pb.ceiling_price, pb.max_daily_move_pct,
                   (a.name || ' Flight ' || f.flight_number || ' (' || UPPER(ff.cabin_class) || ')') as entity_name
            FROM price_bounds pb
            JOIN flight_fares ff ON ff.fare_id = pb.entity_id
            JOIN flights f ON f.flight_id = ff.flight_id
            JOIN airlines a ON a.airline_id = f.airline_id
            LIMIT 6;
        """)
        flight_rows = cursor.fetchall()

        # 2. Fetch room types from price_bounds
        cursor.execute("""
            SELECT pb.entity_id, pb.entity_type, pb.floor_price, pb.ceiling_price, pb.max_daily_move_pct
            FROM price_bounds pb
            WHERE pb.entity_type = 'room_type'
            LIMIT 6;
        """)
        room_rows = cursor.fetchall()

        hotel_names = {
            "rmt_ca391f47": "Villa Mahal Resort (Deluxe Room)",
            "rmt_6b804d20": "Hillview Regency Suites (Lake View)",
            "rmt_0b9115b1": "Garden Orchard Homestay (Heritage Suite)",
            "rmt_16e525d2": "Riverside Kothi Inn (Executive Room)",
            "rmt_4da4065d": "Grand Regency Inn (Presidential Suite)",
            "rmt_1e984702": "Casa Manor Resort (Luxury Villa)",
        }

        results = []
        for r in room_rows:
            e_id = r["entity_id"]
            name = hotel_names.get(e_id, f"Hotel Deluxe Room ({e_id})")
            results.append({
                "entity_id": e_id,
                "entity_name": f"{name} [{e_id}]",
                "entity_type": "hotel_room",
                "floor_price": float(r["floor_price"]),
                "ceiling_price": float(r["ceiling_price"]),
                "max_daily_move_pct": float(r["max_daily_move_pct"])
            })

        for f in flight_rows:
            results.append({
                "entity_id": f["entity_id"],
                "entity_name": f"{f['entity_name']} [{f['entity_id']}]",
                "entity_type": "flight_fare",
                "floor_price": float(f["floor_price"]),
                "ceiling_price": float(f["ceiling_price"]),
                "max_daily_move_pct": float(f["max_daily_move_pct"])
            })

        if results:
            return results
    except Exception as exc:
        print("Error fetching entities:", exc)

    # Safe Fallback
    return [
        {
            "entity_id": "rmt_ca391f47",
            "entity_name": "Villa Mahal Resort (Deluxe Room) [rmt_ca391f47]",
            "entity_type": "hotel_room",
            "floor_price": 2485.41,
            "ceiling_price": 6130.68,
            "max_daily_move_pct": 0.15
        },
        {
            "entity_id": "far_5a8bce18",
            "entity_name": "Air India Flight AI-7050 (ECONOMY) [far_5a8bce18]",
            "entity_type": "flight_fare",
            "floor_price": 3200.0,
            "ceiling_price": 9500.0,
            "max_daily_move_pct": 0.20
        }
    ]


# ==========================================
# 1. Dynamic Pricing Calculation
# ==========================================
@app.post(
    "/pricing/calculate",
    response_model=PricingCalculateResponse,
    dependencies=[Depends(require_admin)],
    tags=["Pricing Engine"],
    summary="Compute dynamic price for an entity on a target date",
)
def calculate_pricing(
    request: PricingCalculateRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Calculates dynamic rate using ML demand forecast, inventory occupancy,
    and enforces hard guardrails against price_bounds with audit persistence in price_history.
    """
    result = pricing_engine.calculate_price(
        entity_id=request.entity_id,
        target_date=request.target_date,
        persist=True
    )
    return PricingCalculateResponse(
        effective_price=result["effective_price"],
        base_price=result["base_price"],
        demand_index=result["demand_index"],
        occupancy_factor=result["occupancy_factor"],
        lead_time_factor=result["lead_time_factor"],
        seasonality_factor=result["seasonality_factor"],
        bound_clamped=result["bound_clamped"],
        raw_price=result.get("raw_candidate_price"),
        clamped_by=result.get("clamped_by"),
        bound_value=result.get("bound_value"),
        bound_name=result.get("bound_name"),
    )



# ==========================================
# 2. Factor Decomposition & Explainability
# ==========================================
@app.get(
    "/pricing/explain",
    response_model=PricingExplainResponse,
    dependencies=[Depends(require_admin)],
    tags=["Explainability"],
    summary="Decompose dynamic price into contributing factors and plain-language reasoning",
)
def explain_pricing(

    entity_id: str = Query(..., examples=["rmt_ca391f47"], description="Unique entity identifier"),
    date: str = Query(..., examples=["2026-10-15"], description="Target date (YYYY-MM-DD)"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Provides auditability and decomposition of the factors driving a dynamic price shift.
    Queries price_history audit records or computes factor decomposition on the fly.
    Returns both English and Hindi audit strings.
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT price, baseline_price, demand_index, occupancy_pct, lead_time_factor,
               seasonality_factor, competitor_factor, bound_clamped, explanation, raw_price, clamped_by, bound_value
        FROM price_history
        WHERE entity_id = ? AND effective_date = ?
        ORDER BY rowid DESC
        LIMIT 1;
    """, (entity_id, date))
    ph_row = cursor.fetchone()

    if ph_row and ph_row["price"]:
        base_price = float(ph_row["baseline_price"])
        effective_price = float(ph_row["price"])
        demand_index = float(ph_row["demand_index"])
        occ_raw = float(ph_row["occupancy_pct"])
        occupancy_ratio = occ_raw / 100.0 if occ_raw > 1.0 else occ_raw
        lead_time_factor = float(ph_row["lead_time_factor"])
        seasonality_factor = float(ph_row["seasonality_factor"])
        competitor_factor = float(ph_row["competitor_factor"]) if ph_row["competitor_factor"] is not None else 1.0
        bound_clamped = bool(ph_row["bound_clamped"])
        clamped_by = ph_row["clamped_by"]
        bound_value = ph_row["bound_value"]
        bound_name = f"{clamped_by.replace('_', ' ').title()} Guardrail (₹{float(bound_value):,.0f})" if clamped_by and bound_value else None

        pct_shift = round(((effective_price - base_price) / base_price) * 100, 1)
        sign = "+" if pct_shift >= 0 else ""
        clamp_clause_en = f"Notice: Price was clamped by {bound_name}." if bound_clamped else "Operates within all active floor, ceiling, and daily-movement guardrails."
        explanation_en = (
            f"Price for {entity_id} on {date} is calculated at ₹{effective_price:,.0f} ({sign}{pct_shift}% vs baseline ₹{base_price:,.0f}) "
            f"driven by demand index ({demand_index:.2f}x), occupancy ({occupancy_ratio*100:.0f}%), and seasonal weighting ({seasonality_factor:.2f}x). "
            f"{clamp_clause_en}"
        )
        clamp_clause_hi = f"सूचना: मूल्य को {bound_name} द्वारा सीमित (क्लैंप) किया गया।" if bound_clamped else "यह मूल्य निर्धारित सुरक्षा सीमाओं के अंतर्गत सुरक्षित है।"
        explanation_hi = (
            f"{date} के लिए {entity_id} का मूल्य आधार दर ₹{base_price:,.0f} से {sign}{pct_shift}% बदलकर ₹{effective_price:,.0f} निर्धारित किया गया है। "
            f"यह निर्णय मांग सूचकांक ({demand_index:.2f}x), ऑक्यूपेंसी ({occupancy_ratio*100:.0f}%) और मौसमी प्रभाव पर आधारित है। "
            f"{clamp_clause_hi}"
        )

        factor_weights = pricing_engine.forecaster.get_factor_weights() if (pricing_engine and getattr(pricing_engine, "forecaster", None)) else {
            "demand_weight": 0.35, "occupancy_weight": 0.326, "seasonality_weight": 0.198,
            "lead_time_weight": 0.15, "competitor_weight": 0.25,
            "coefficients": {"demand_index": 1.7501, "occupancy_pct": 0.0217, "is_peak_month": 0.0099}
        }
        coefs = factor_weights.get("coefficients", {})
        c_demand = coefs.get("demand_index", 1.7501)
        c_occ = coefs.get("occupancy_pct", 0.0217)
        c_season = coefs.get("is_peak_month", 0.0099)

        factors = [
            {"name": f"Demand Signal (ML Ridge beta={c_demand:.2f})", "value": float(demand_index), "contribution": round((demand_index - 1.0) * factor_weights["demand_weight"], 3)},
            {"name": f"Occupancy Rate ({int(occupancy_ratio*100)}% booked, beta={c_occ:.4f})", "value": float(round(1.0 + (occupancy_ratio - 0.5)*0.4, 3)), "contribution": round((occupancy_ratio - 0.5) * factor_weights["occupancy_weight"], 3)},
            {"name": "Lead Time Factor", "value": float(lead_time_factor), "contribution": round((lead_time_factor - 1.0) * factor_weights["lead_time_weight"], 3)},
            {"name": f"Seasonality Factor (beta={c_season:.4f})", "value": float(seasonality_factor), "contribution": round((seasonality_factor - 1.0) * factor_weights["seasonality_weight"], 3)},
            {"name": "Competitor Factor", "value": float(competitor_factor), "contribution": round((competitor_factor - 1.0) * factor_weights["competitor_weight"], 3)}
        ]
        return PricingExplainResponse(
            effective_price=effective_price,
            base_price=base_price,
            factors=factors,
            explanation_en=explanation_en,
            explanation_hi=explanation_hi
        )

    result = pricing_engine.calculate_price(
        entity_id=entity_id,
        target_date=date,
        persist=False
    )
    return PricingExplainResponse(
        effective_price=result["effective_price"],
        base_price=result["base_price"],
        factors=result["factors"],
        explanation_en=result["explanation_en"],
        explanation_hi=result["explanation_hi"]
    )


@app.get(
    "/pricing/forecaster/metrics",
    dependencies=[Depends(require_admin)],
    tags=["ML Forecaster"],
    summary="Get demand forecaster training metrics, dedup stats, and validation performance",
)
def get_forecaster_metrics():
    """
    Returns telemetry dedup count, outlier clip threshold, test MAE/R2, naive baseline comparison,
    and learned model coefficients.
    """
    if pricing_engine and getattr(pricing_engine, "forecaster", None):
        return pricing_engine.forecaster.get_metrics_summary()
    return {"status": "forecaster unavailable"}


# ==========================================
# 3. 30-Day Forecast Horizon & Clamp Summary
# ==========================================
@app.get(
    "/pricing/horizon",
    response_model=PricingSimulateResponse,
    dependencies=[Depends(require_admin)],
    tags=["Forecast Horizon"],
    summary="Get 30-day baseline forecast curve with Guardrail Clamp Report",
)
def get_forecast_horizon(
    entity_id: str = Query(..., examples=["rmt_ca391f47"], description="Entity identifier"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Retrieves the 30-day dynamic price trajectory, demand indices, and guardrail clamp summary.
    """
    sim_data = pricing_engine.simulate_30day_curve(
        entity_id=entity_id,
        base_multiplier=1.0,
        daily_move_limit=0.15
    )
    return PricingSimulateResponse(
        simulated_price_curve=sim_data["simulated_price_curve"],
        revenue_delta_pct=sim_data["revenue_delta_pct"],
        booking_rate_delta_pct=sim_data["booking_rate_delta_pct"],
        breaches=sim_data["breaches"],
        clamp_summary=sim_data.get("clamp_summary")
    )


# ==========================================
# 4. What-If Scenario Simulation
# ==========================================
@app.post(
    "/pricing/simulate",
    response_model=PricingSimulateResponse,
    dependencies=[Depends(require_admin)],
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
    """
    sim_data = pricing_engine.simulate_30day_curve(
        entity_id=request.entity_id,
        base_multiplier=request.base_multiplier,
        daily_move_limit=request.daily_move_limit
    )
    return PricingSimulateResponse(
        simulated_price_curve=sim_data["simulated_price_curve"],
        revenue_delta_pct=sim_data["revenue_delta_pct"],
        booking_rate_delta_pct=sim_data["booking_rate_delta_pct"],
        breaches=sim_data["breaches"],
        clamp_summary=sim_data.get("clamp_summary")
    )


# ==========================================
# 5. Manual Price Overrides
# ==========================================
@app.post(
    "/pricing/override",
    response_model=PricingOverrideResponse,
    dependencies=[Depends(require_admin)],
    tags=["Manual Overrides"],
    summary="Apply an admin manual price override for a specific date",
)
def apply_price_override(
    request: PricingOverrideRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Allows a revenue manager to set an explicit manual price override, validating against bounds.
    """
    override_res = pricing_engine.set_manual_override(
        entity_id=request.entity_id,
        date=request.date,
        override_price=request.override_price,
        reason=request.reason or "Admin manual adjustment"
    )
    return PricingOverrideResponse(**override_res)


@app.get(
    "/pricing/overrides",
    dependencies=[Depends(require_admin)],
    tags=["Manual Overrides"],
    summary="List all active manual overrides",
)
def list_price_overrides(
    entity_id: Optional[str] = Query(None, description="Optional entity filter"),
    db: sqlite3.Connection = Depends(get_db)
):
    return pricing_engine.get_manual_overrides(entity_id=entity_id)



# ==========================================
# 6. Telemetry Event Ingestion
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
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_traveller)
):
    """
    Records an incoming user interaction event to train the real-time demand model
    and increments booked inventory units on confirmed bookings.
    IDs are treated as opaque strings without prefix assumptions.
    Attaches authenticated traveller user_id to pricing_events for booking traceability.
    Wraps inventory_calendar update and pricing_events insert in a single atomic transaction.
    """
    try:
        cursor = db.cursor()
        import uuid
        event_id = f"evt_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
        user_id = current_user.get("sub")

        # Opaque lookup of entity_type and city_id
        cursor.execute("SELECT entity_type FROM price_bounds WHERE entity_id = ? LIMIT 1;", (request.entity_id,))
        pb_row = cursor.fetchone()
        if pb_row:
            entity_type = pb_row["entity_type"]
        else:
            cursor.execute("SELECT entity_type FROM inventory_calendar WHERE entity_id = ? LIMIT 1;", (request.entity_id,))
            ic_row = cursor.fetchone()
            entity_type = ic_row["entity_type"] if ic_row else "room_type"

        cursor.execute("SELECT city_id FROM pricing_events WHERE entity_id = ? LIMIT 1;", (request.entity_id,))
        pe_row = cursor.fetchone()
        city_id = pe_row["city_id"] if pe_row else "cty_c07454f1"

        # Determine real target travel date (no hardcoded date)
        if request.for_date:
            target_for_date = request.for_date
        else:
            try:
                dt = datetime.datetime.fromisoformat(request.timestamp.replace("Z", "+00:00"))
                target_for_date = (dt.date() + datetime.timedelta(days=request.lead_time_days)).strftime("%Y-%m-%d")
            except Exception:
                target_for_date = datetime.date.today().strftime("%Y-%m-%d")

        # 1. If booking event, check availability and atomically update inventory for target_for_date
        if request.event_type.lower() == "booking":
            cursor.execute(
                "SELECT inventory_id, total_units, booked_units, held_units FROM inventory_calendar WHERE entity_id = ? AND for_date = ? LIMIT 1;",
                (request.entity_id, target_for_date)
            )
            inv_row = cursor.fetchone()
            if inv_row:
                total_u = int(inv_row["total_units"])
                booked_u = int(inv_row["booked_units"])
                held_u = int(inv_row["held_units"])
                if (booked_u + held_u) >= total_u:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This unit is sold out for your selected dates."
                    )
                cursor.execute("""
                    UPDATE inventory_calendar
                    SET booked_units = booked_units + 1,
                        updated_at = ?
                    WHERE entity_id = ? AND for_date = ?;
                """, (datetime.datetime.now().isoformat(), request.entity_id, target_for_date))
            else:
                inv_id = f"inv_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
                cursor.execute("""
                    INSERT INTO inventory_calendar (
                        inventory_id, entity_type, entity_id, for_date, total_units,
                        booked_units, held_units, price, currency, min_stay_nights,
                        closed_to_arrival, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    inv_id, entity_type, request.entity_id, target_for_date, 10,
                    1, 0, "4500.00", "INR", 1,
                    0, datetime.datetime.now().isoformat()
                ))

        # 2. Insert into pricing_events with authenticated user_id and exact target_for_date
        cursor.execute("""
            INSERT INTO pricing_events (
                event_id, entity_type, entity_id, city_id, event_type, occurred_at, for_date,
                lead_time_days, channel, party_size, quoted_price, currency, converted, session_id, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            event_id,
            entity_type,
            request.entity_id,
            city_id,
            request.event_type,
            request.timestamp,
            target_for_date,
            request.lead_time_days,
            "direct_web",
            2,
            "4500.00",
            "INR",
            1 if request.event_type.lower() == "booking" else 0,
            f"ses_{int(datetime.datetime.now().timestamp())}",
            user_id
        ))

        # Single atomic commit: both inventory and event log succeed together
        db.commit()
        return EventLogResponse(status="logged")

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record booking event: {str(exc)}"
        )



# ==========================================
# 7. Traveller-Facing Flow & Languages
# ==========================================
@app.get(
    "/traveller/search",
    dependencies=[Depends(require_traveller)],
    tags=["Traveller"],
    summary="Live search for traveller-facing flow with availability, dynamic pricing, and transparent context badges",
)
def traveller_search(

    date: str = Query("2026-10-15", description="Stay date"),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Returns live inventory availability with dynamic prices and transparent context badges
    (e.g., 'Peak Autumn Season • 85% Booked').
    """
    cursor = db.cursor()
    
    # 1. Fetch available hotel rooms (prioritize bookable inventory)
    cursor.execute("""
        SELECT ic.entity_id, ic.entity_type, ic.for_date, ic.total_units, ic.booked_units, ic.price,
               NULL as flight_name
        FROM inventory_calendar ic
        WHERE ic.for_date = ? AND ic.entity_type = 'room_type'
        ORDER BY (ic.total_units - ic.booked_units) DESC, ic.entity_id ASC
        LIMIT 4;
    """, (date,))
    room_rows = cursor.fetchall()

    # 2. Fetch available flights with airlines and flight numbers
    cursor.execute("""
        SELECT ic.entity_id, ic.entity_type, ic.for_date, ic.total_units, ic.booked_units, ic.price,
               (a.name || ' Flight ' || f.flight_number || ' (' || UPPER(ff.cabin_class) || ')') as flight_name
        FROM inventory_calendar ic
        JOIN flight_fares ff ON ff.fare_id = ic.entity_id
        JOIN flights f ON f.flight_id = ff.flight_id
        JOIN airlines a ON a.airline_id = f.airline_id
        WHERE ic.for_date = ?
        ORDER BY (ic.total_units - ic.booked_units) DESC, ic.entity_id ASC
        LIMIT 2;
    """, (date,))
    flight_rows = cursor.fetchall()

    combined_rows = list(room_rows) + list(flight_rows)

    if not combined_rows:
        cursor.execute("""
            SELECT pb.entity_id, pb.entity_type, ? as for_date, 10 as total_units, 4 as booked_units, pb.floor_price as price,
                   NULL as flight_name
            FROM price_bounds pb
            LIMIT 6;
        """, (date,))
        combined_rows = cursor.fetchall()

    results = []
    hotel_names = {
        "rmt_ca391f47": "Villa Mahal Resort (Deluxe Heritage Room)",
        "rmt_6b804d20": "Hillview Regency Suites (Lake View Suite)",
        "rmt_0b9115b1": "Garden Orchard Homestay (Royal Suite)",
        "rmt_16e525d2": "Riverside Kothi Inn (Executive Garden View)",
        "rmt_4da4065d": "Grand Regency Inn (Presidential Suite)",
        "rmt_1e984702": "Casa Manor Resort (Luxury Mountain Villa)",
        "rmt_ad2452fd": "Heritage Grand Palace (Royal Deluxe Room)",
        "rmt_0f009220": "Mountain Valley Eco Resort (Forest View)",
        "rmt_33c6c9be": "Sunrise Beachfront Haven (Ocean Balcony)",
        "rmt_4acc0255": "Royal Heritage Haveli (Courtyard Suite)",
    }

    for r in combined_rows:
        e_id = r["entity_id"]
        total = int(r["total_units"]) if r["total_units"] else 10
        booked = int(r["booked_units"]) if r["booked_units"] is not None else 4
        available = max(0, total - booked)
        occupancy_pct = int(round((booked / total) * 100)) if total > 0 else 50

        # Calculate live dynamic rate
        calc = pricing_engine.calculate_price(e_id, date, persist=False)
        dyn_price = calc["effective_price"]

        # Transparent context badge
        if available == 0:
            badge_context = "Fully Booked • 100% Sold Out"
            badge_color = "amber"
        elif occupancy_pct >= 80:
            badge_context = f"Peak Autumn Season • {occupancy_pct}% Booked ({available} Left)"
            badge_color = "amber"
        elif calc["bound_clamped"]:
            badge_context = f"Protected Price • Capped by {calc.get('bound_name') or 'Safety Bound'}"
            badge_color = "emerald"
        else:
            badge_context = f"High Availability • {available} Units Left"
            badge_color = "teal"

        if r["flight_name"]:
            name = r["flight_name"]
        else:
            name = hotel_names.get(e_id, f"Premium Deluxe Suite [{e_id}]")

        results.append({
            "entity_id": e_id,
            "entity_name": name,
            "entity_type": r["entity_type"],
            "date": date,
            "total_units": total,
            "booked_units": booked,
            "available_units": available,
            "occupancy_pct": occupancy_pct,
            "base_price": calc["base_price"],
            "dynamic_price": dyn_price,
            "bound_clamped": calc["bound_clamped"],
            "badge_context": badge_context,
            "badge_color": badge_color
        })

    return results


@app.get(
    "/languages",
    tags=["Metadata"],
    summary="Fetch supported BCP-47 languages directly from SQLite languages table",
)
def get_languages(db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieves supported BCP-47 languages (en-IN, hi) directly from the languages table.
    """
    cursor = db.cursor()
    cursor.execute("SELECT language_id, bcp47, english_name, native_name, script, rtl FROM languages WHERE bcp47 IN ('en-IN', 'hi');")
    return [dict(r) for r in cursor.fetchall()]


