"""
Mock Data Generator and Contract Stubs for Jett 2 Holiday.
Generates realistic, deterministic mock responses for the 4 API contracts.
Each function is annotated with TODO markers detailing the real ML and pricing engine logic to be implemented in Phase 2.
"""

import datetime
from typing import Dict, Any, List
from .schemas import (
    PricingCalculateResponse,
    PricingExplainResponse,
    FactorItem,
    PricingSimulateResponse,
    SimulatedPricePoint,
    EventLogResponse,
)


def get_mock_pricing_calculate(entity_id: str, target_date: str) -> PricingCalculateResponse:
    """
    Mock response for POST /pricing/calculate
    
    TODO [Phase 2]: Replace with real Pricing Engine calculation:
      1. Ingest entity attributes & base fare from `hotels`/`flight_fares`.
      2. Call ML Demand Forecaster (Prophet / Regression) for `target_date` to yield `demand_index`.
      3. Compute `occupancy_factor` from `inventory_calendar` (booked_units / total_capacity).
      4. Compute `lead_time_factor` from days until target_date using exponential decay (exp(-k_c * lead_time)).
      5. Compute `seasonality_factor` from `cities.peak_months`.
      6. Candidate Price = Base Price * (1 + sum(factors_delta)).
      7. Enforce hard guardrails from `price_bounds` (clamp between floor_price and ceiling_price,
         respecting max_daily_move_pct).
      8. Persist result into `price_history`.
    """
    # Deterministic baseline mock values based on entity prefix
    is_flight = "flt" in entity_id.lower()
    base_price = 5500.0 if is_flight else 4500.0
    demand_index = 1.42
    occupancy_factor = 1.18
    lead_time_factor = 1.04
    seasonality_factor = 1.15
    
    # Raw un-clamped calculation: base_price * (1 + (0.42*0.3 + 0.18*0.4 + 0.04*0.1 + 0.15*0.2)) = approx 5850.0
    effective_price = 7250.0 if is_flight else 5850.0
    bound_clamped = False

    return PricingCalculateResponse(
        effective_price=effective_price,
        base_price=base_price,
        demand_index=demand_index,
        occupancy_factor=occupancy_factor,
        lead_time_factor=lead_time_factor,
        seasonality_factor=seasonality_factor,
        bound_clamped=bound_clamped
    )


def get_mock_pricing_explain(entity_id: str, date_str: str) -> PricingExplainResponse:
    """
    Mock response for GET /pricing/explain
    
    TODO [Phase 2]: Replace with real Factor Decomposition:
      1. Query `price_history` for (entity_id, target_date).
      2. If not pre-computed, execute the Regression feature attribution step.
      3. Format dynamic plain-language multilingual summaries (English & Hindi)
         using BCP-47 locale formatting templates.
    """
    is_flight = "flt" in entity_id.lower()
    base_price = 5500.0 if is_flight else 4500.0
    effective_price = 7250.0 if is_flight else 5850.0

    factors = [
        FactorItem(name="Demand Index (forecast)", value=1.42, contribution=0.28),
        FactorItem(name="Occupancy Factor (85% booked)", value=1.18, contribution=0.18),
        FactorItem(name="Lead Time (14 days out)", value=1.04, contribution=0.04),
        FactorItem(name="Seasonality (Autumn Peak)", value=1.15, contribution=0.15)
    ]

    explanation_en = (
        f"Price for {entity_id} on {date_str} is elevated to ₹{effective_price:,.0f} (+30% over baseline ₹{base_price:,.0f}) "
        "driven by high forecasted search volume, strong occupancy (85%), and peak seasonal travel trends. "
        "No clamping was required as price remains within floor (₹3,500) and ceiling (₹7,000) guardrails."
    )

    explanation_hi = (
        f"{date_str} के लिए {entity_id} का मूल्य आधार दर ₹{base_price:,.0f} से बढ़कर ₹{effective_price:,.0f} (+30%) हो गया है। "
        "यह वृद्धि उच्च अनुमानित मांग, 85% ऑक्यूपेंसी और शरद ऋतु के पीक टूरिस्ट सीजन के कारण है। "
        "यह मूल्य निर्धारित फ्लोर (₹3,500) और सीलिंग (₹7,000) सीमाओं के अंतर्गत सुरक्षित है।"
    )

    return PricingExplainResponse(
        effective_price=effective_price,
        base_price=base_price,
        factors=factors,
        explanation_en=explanation_en,
        explanation_hi=explanation_hi
    )


def get_mock_pricing_simulate(entity_id: str, base_multiplier: float, daily_move_limit: float) -> PricingSimulateResponse:
    """
    Mock response for POST /pricing/simulate
    
    TODO [Phase 2]: Implement dynamic What-If simulation engine:
      1. Fetch 30-day baseline demand forecast and price trajectory for `entity_id`.
      2. Apply user-supplied `base_multiplier` to demand sensitivity and pricing factors.
      3. Simulate day-by-day rates enforcing `daily_move_limit` clamp.
      4. Detect guardrail boundary breaches and count clamping violations.
      5. Compute projected revenue delta % and price-elasticity booking rate impact %.
      6. Record run into `simulations` table with scenario_id.
    """
    start_date = datetime.date(2026, 10, 12)
    curve: List[SimulatedPricePoint] = []
    
    base_fare = 4500.0
    floor_price = 3500.0
    ceiling_price = 7000.0
    breaches_count = 0

    # Generate a realistic 30-day curve matching Screen Sketch 2
    for day_idx in range(30):
        curr_date = start_date + datetime.timedelta(days=day_idx)
        date_str = curr_date.strftime("%Y-%m-%d")
        
        # Synthetic bell-curve peaking around Oct 15-18
        progress = day_idx / 30.0
        peak_wave = max(0.0, 1.0 - abs(day_idx - 5) / 10.0) # peak at day 5 (Oct 17)
        
        sim_demand = 1.0 + (0.55 * peak_wave)
        current_dyn = base_fare * (1.0 + 0.30 * peak_wave)
        
        # Apply what-if multiplier
        raw_sim = current_dyn * base_multiplier
        
        # Guardrail check
        clamped = False
        if raw_sim > ceiling_price:
            clamped = True
            breaches_count += 1
            sim_price = ceiling_price
        elif raw_sim < floor_price:
            clamped = True
            breaches_count += 1
            sim_price = floor_price
        else:
            sim_price = round(raw_sim, 2)

        curve.append(
            SimulatedPricePoint(
                date=date_str,
                base_price=base_fare,
                current_dynamic_price=round(current_dyn, 2),
                simulated_price=round(sim_price, 2),
                demand_index=round(sim_demand, 2),
                floor_price=floor_price,
                ceiling_price=ceiling_price,
                clamped=clamped
            )
        )

    # Calculate projected impacts
    revenue_delta = round((base_multiplier - 1.0) * 82.5, 1) # e.g. 1.15 -> +12.4%
    booking_rate_delta = round(-(base_multiplier - 1.0) * 14.0, 1) # price elasticity dampening

    return PricingSimulateResponse(
        simulated_price_curve=curve,
        revenue_delta_pct=revenue_delta,
        booking_rate_delta_pct=booking_rate_delta,
        breaches=breaches_count
    )


def get_mock_event_log(entity_id: str, event_type: str, timestamp: str, lead_time_days: int) -> EventLogResponse:
    """
    Mock response for POST /events
    
    TODO [Phase 2]: Insert incoming event into SQLite `pricing_events`:
      - INSERT INTO pricing_events (entity_id, event_type, timestamp, lead_time_days) VALUES (...)
      - If event_type == 'booking', increment `booked_units` in `inventory_calendar`.
      - Invalidate / update cached short-term demand counters.
    """
    return EventLogResponse(status="logged")
