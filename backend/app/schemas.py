"""
Pydantic Schemas for Jett 2 Holiday API Contracts.
Defines input and output shapes for all 4 core endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


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
    raw_price: Optional[float] = Field(default=None, description="Unclamped model candidate price")
    clamped_by: Optional[str] = Field(default=None, description="Which specific guardrail clamped: ceiling, floor, daily_movement")
    bound_value: Optional[float] = Field(default=None, description="Numeric bound value")
    bound_name: Optional[str] = Field(default=None, description="Human readable bound name")


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
    start_date: Optional[str] = Field(default=None, examples=["2026-10-15"], description="Optional start date for the 30-day simulation window")


class SimulatedPricePoint(BaseModel):
    date: str = Field(..., examples=["2026-10-15"])
    base_price: float = Field(..., examples=[4500.0])
    raw_model_price: Optional[float] = Field(default=None, examples=[7450.0], description="Unbounded raw model price before guardrail clamping")
    current_dynamic_price: float = Field(..., examples=[5850.0], description="Baseline published price")
    simulated_price: float = Field(..., examples=[6130.68], description="Published dynamic price after all guardrails")
    demand_index: float = Field(..., examples=[1.42])
    floor_price: float = Field(..., examples=[3500.0])
    ceiling_price: float = Field(..., examples=[7000.0])
    clamped: bool = Field(..., examples=[False])
    clamped_by: Optional[str] = Field(default=None, examples=["ceiling"], description="Guardrail that clamped the price: ceiling, floor, or daily_movement")
    bound_value: Optional[float] = Field(default=None, examples=[6130.68], description="Numeric value of the clamping bound")
    bound_name: Optional[str] = Field(default=None, examples=["Ceiling Guardrail (₹6,130.68)"], description="Human-readable named bound")
    factors: Optional[List[Dict[str, Any]]] = Field(default=None, description="Driving factor decomposition list")


class ClampSummary(BaseModel):
    total_prices: int = Field(..., examples=[30])
    total_clamped: int = Field(..., examples=[14])
    ceiling_clamps: int = Field(..., examples=[9])
    floor_clamps: int = Field(..., examples=[3])
    daily_movement_clamps: int = Field(..., examples=[2])
    summary_text: str = Field(..., examples=["14 of 30 prices clamped — 9 by ceiling, 3 by floor, 2 by daily-movement"])


class PricingSimulateResponse(BaseModel):
    simulated_price_curve: List[SimulatedPricePoint] = Field(..., description="30-day simulated price trajectory curve")
    revenue_delta_pct: float = Field(..., examples=[12.4], description="Projected change in revenue percentage")
    booking_rate_delta_pct: float = Field(..., examples=[-2.1], description="Projected change in booking conversion rate percentage")
    breaches: int = Field(..., examples=[0], description="Count of dates where simulated rate violated guardrail constraints")
    clamp_summary: Optional[ClampSummary] = Field(default=None, description="Guardrail clamp report summary stats")


# ==========================================
# 4. /events Schemas
# ==========================================
class EventLogRequest(BaseModel):
    entity_id: str = Field(..., examples=["htl_sng_001_deluxe"], description="Entity identifier associated with event")
    event_type: str = Field(..., examples=["booking"], description="Event category: search, view, booking, cancellation, abandon")
    timestamp: str = Field(..., examples=["2026-10-12T14:30:00Z"], description="ISO 8601 formatted timestamp")
    lead_time_days: int = Field(..., ge=0, examples=[14], description="Days between event trigger and target travel date")
    for_date: Optional[str] = Field(default=None, examples=["2026-10-15"], description="Target stay or flight date (YYYY-MM-DD)")


class EventLogResponse(BaseModel):
    status: str = Field(default="logged", examples=["logged"], description="Status confirmation string")



# ==========================================
# 5. Manual Override Schemas
# ==========================================
class PricingOverrideRequest(BaseModel):
    entity_id: str = Field(..., examples=["htl_sng_001_deluxe"])
    date: str = Field(..., examples=["2026-10-15"])
    override_price: float = Field(..., ge=0, examples=[5200.0])
    reason: Optional[str] = Field(default="Manual revenue manager override", examples=["Corporate booking adjustment"])


class PricingOverrideResponse(BaseModel):
    entity_id: str
    date: str
    override_price: float
    effective_price: float
    base_price: float
    floor_price: float
    ceiling_price: float
    violates_guardrails: bool
    warning: Optional[str] = None
    applied_at: str

