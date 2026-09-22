"""
Pydantic Schemas for Jett 2 Holiday API Contracts.
Defines input and output shapes for all 4 core endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


# ==========================================
# 1. /pricing/calculate Schemas
# ==========================================
class PricingCalculateRequest(BaseModel):
    entity_id: str = Field(..., examples=["htl_sng_001_deluxe"], description="Unique identifier for hotel room or flight cabin")
    target_date: str = Field(..., examples=["2026-10-15"], description="Target stay or flight date (YYYY-MM-DD)")


class PricingCalculateResponse(BaseModel):
    effective_price: float = Field(..., examples=[5850.0], description="Final calculated price after applying factors and bounds clamping")
    base_price: float = Field(..., examples=[4500.0], description="Baseline unadjusted benchmark price")
    demand_index: float = Field(..., examples=[1.42], description="Normalized forecast demand index (1.0 = baseline)")
    occupancy_factor: float = Field(..., examples=[1.18], description="Multiplier derived from booked units vs capacity ratio")
    lead_time_factor: float = Field(..., examples=[1.04], description="Multiplier derived from booking intent decay & commitment curve")
    seasonality_factor: float = Field(..., examples=[1.15], description="Seasonal multiplier based on city peak profile")
    bound_clamped: bool = Field(..., examples=[False], description="True if candidate price was clamped to floor/ceiling guardrails")


# ==========================================
# 2. /pricing/explain Schemas
# ==========================================
class FactorItem(BaseModel):
    name: str = Field(..., examples=["Demand Index (forecast)"], description="Name of the contributing factor")
    value: float = Field(..., examples=[1.42], description="Raw feature or factor value")
    contribution: float = Field(..., examples=[0.28], description="Relative contribution or delta impact percentage (e.g. +28%)")


class PricingExplainResponse(BaseModel):
    effective_price: float = Field(..., examples=[5850.0], description="Computed dynamic price")
    base_price: float = Field(..., examples=[4500.0], description="Base benchmark price")
    factors: List[FactorItem] = Field(..., description="Decomposed pricing factors")
    explanation_en: str = Field(
        ...,
        examples=["Price elevated by 30% due to combined autumn seasonal surge and high property occupancy. No clamping applied; within guardrails."],
        description="Plain-English explainability narrative"
    )
    explanation_hi: str = Field(
        ...,
        examples=["उच्च मांग, ऑक्यूपेंसी और शरद ऋतु पीक सीजन के कारण मूल्य में 30% की वृद्धि की गई है।"],
        description="Hindi explainability narrative for multilingual audit"
    )


# ==========================================
# 3. /pricing/simulate Schemas
# ==========================================
class PricingSimulateRequest(BaseModel):
    entity_id: str = Field(..., examples=["htl_sng_001_deluxe"], description="Entity identifier to simulate")
    base_multiplier: float = Field(..., ge=0.1, le=5.0, examples=[1.15], description="Multiplier scalar to test price sensitivity")
    daily_move_limit: float = Field(..., ge=0.01, le=1.0, examples=[0.20], description="Maximum permitted day-over-day price jump percentage (e.g. 0.20 for 20%)")


class SimulatedPricePoint(BaseModel):
    date: str = Field(..., examples=["2026-10-15"])
    base_price: float = Field(..., examples=[4500.0])
    current_dynamic_price: float = Field(..., examples=[5850.0])
    simulated_price: float = Field(..., examples=[6727.5])
    demand_index: float = Field(..., examples=[1.42])
    floor_price: float = Field(..., examples=[3500.0])
    ceiling_price: float = Field(..., examples=[7000.0])
    clamped: bool = Field(..., examples=[False])


class PricingSimulateResponse(BaseModel):
    simulated_price_curve: List[SimulatedPricePoint] = Field(..., description="30-day simulated price trajectory curve")
    revenue_delta_pct: float = Field(..., examples=[12.4], description="Projected change in revenue percentage (e.g. +12.4%)")
    booking_rate_delta_pct: float = Field(..., examples=[-2.1], description="Projected change in booking conversion rate percentage (e.g. -2.1%)")
    breaches: int = Field(..., examples=[0], description="Count of dates where simulated rate violated guardrail constraints")


# ==========================================
# 4. /events Schemas
# ==========================================
class EventLogRequest(BaseModel):
    entity_id: str = Field(..., examples=["htl_sng_001_deluxe"], description="Entity identifier associated with event")
    event_type: str = Field(..., examples=["booking"], description="Event category: search, view, booking, cancellation, abandon")
    timestamp: str = Field(..., examples=["2026-10-12T14:30:00Z"], description="ISO 8601 formatted timestamp")
    lead_time_days: int = Field(..., ge=0, examples=[14], description="Days between event trigger and target travel date")


class EventLogResponse(BaseModel):
    status: str = Field(default="logged", examples=["logged"], description="Status confirmation string")
