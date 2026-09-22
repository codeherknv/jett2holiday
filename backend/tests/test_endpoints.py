"""
Integration and schema conformance tests for Jett 2 Holiday FastAPI endpoints.
Tests all 4 required contract endpoints using FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_calculate_pricing_endpoint():
    payload = {
        "entity_id": "htl_sng_001_deluxe",
        "target_date": "2026-10-15"
    }
    response = client.post("/pricing/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Assert contract fields
    assert "effective_price" in data
    assert "base_price" in data
    assert "demand_index" in data
    assert "occupancy_factor" in data
    assert "lead_time_factor" in data
    assert "seasonality_factor" in data
    assert "bound_clamped" in data
    assert isinstance(data["bound_clamped"], bool)
    assert data["effective_price"] > 0


def test_explain_pricing_endpoint():
    response = client.get("/pricing/explain?entity_id=htl_sng_001_deluxe&date=2026-10-15")
    assert response.status_code == 200
    data = response.json()
    
    # Assert contract fields
    assert "effective_price" in data
    assert "base_price" in data
    assert "factors" in data
    assert isinstance(data["factors"], list)
    assert len(data["factors"]) > 0
    assert "name" in data["factors"][0]
    assert "value" in data["factors"][0]
    assert "contribution" in data["factors"][0]
    assert "explanation_en" in data
    assert "explanation_hi" in data


def test_simulate_pricing_endpoint():
    payload = {
        "entity_id": "htl_sng_001_deluxe",
        "base_multiplier": 1.15,
        "daily_move_limit": 0.20
    }
    response = client.post("/pricing/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Assert contract fields
    assert "simulated_price_curve" in data
    assert len(data["simulated_price_curve"]) == 30
    assert "revenue_delta_pct" in data
    assert "booking_rate_delta_pct" in data
    assert "breaches" in data


def test_events_endpoint():
    payload = {
        "entity_id": "htl_sng_001_deluxe",
        "event_type": "booking",
        "timestamp": "2026-10-12T14:30:00Z",
        "lead_time_days": 14
    }
    response = client.post("/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "logged"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
