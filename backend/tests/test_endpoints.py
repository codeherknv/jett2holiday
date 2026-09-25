"""
Integration, schema conformance, and role-based access control tests for Jett 2 Holiday.
Tests:
1. Health & public discovery endpoints.
2. Admin authentication (hardcoded demo account) + Traveller authentication (bcrypt + users table).
3. 401 Unauthorized rejection when accessing protected endpoints without a token.
4. 403 Forbidden rejection when role claim is mismatched (e.g. traveller hitting admin endpoints or vice versa).
5. Dynamic pricing calculation, factor explainability, 30-day forecast horizon with clamp report.
6. Traveller search, booking flow, inventory calendar increment, and user_id traceability.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ==========================================
# Fixtures & Helpers for Auth Tokens
# ==========================================
@pytest.fixture(scope="module")
def admin_headers():
    res = client.post("/auth/admin/login", json={"username": "admin", "password": "admin@123"})
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def traveller_headers():
    unique_email = f"traveller_{uuid.uuid4().hex[:6]}@example.com"
    signup_res = client.post("/auth/signup", json={
        "email": unique_email,
        "password": "traveller@123",
        "display_name": "Test Traveller"
    })
    assert signup_res.status_code == 201, f"Traveller signup failed: {signup_res.text}"
    token = signup_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==========================================
# 1. Health & Public Endpoints
# ==========================================
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_languages_endpoint_is_public():
    response = client.get("/languages")
    assert response.status_code == 200
    langs = response.json()
    assert isinstance(langs, list)
    bcp47_codes = [l["bcp47"] for l in langs]
    assert "en-IN" in bcp47_codes
    assert "hi" in bcp47_codes


# ==========================================
# 2. Authentication Rejection & Role Enforcement
# ==========================================
def test_unauthenticated_requests_return_401():
    # Direct access without token must return 401
    assert client.post("/pricing/calculate", json={"entity_id": "rmt_ca391f47", "target_date": "2026-10-15"}).status_code == 401
    assert client.get("/pricing/explain?entity_id=rmt_ca391f47&date=2026-10-15").status_code == 401
    assert client.get("/pricing/horizon?entity_id=rmt_ca391f47").status_code == 401
    assert client.post("/pricing/simulate", json={"entity_id": "rmt_ca391f47", "base_multiplier": 1.1, "daily_move_limit": 0.15}).status_code == 401
    assert client.get("/entities").status_code == 401
    assert client.get("/traveller/search?date=2026-10-15").status_code == 401
    assert client.post("/events", json={"entity_id": "rmt_ca391f47", "event_type": "view", "timestamp": "2026-10-12T14:30:00Z", "lead_time_days": 14}).status_code == 401


def test_admin_login_validation():
    # Invalid password
    bad_res = client.post("/auth/admin/login", json={"username": "admin", "password": "wrongpassword"})
    assert bad_res.status_code == 401
    # Invalid username
    bad_res2 = client.post("/auth/admin/login", json={"username": "not_admin", "password": "admin@123"})
    assert bad_res2.status_code == 401


def test_cross_role_access_returns_403(admin_headers, traveller_headers):
    # 1. Traveller attempting admin endpoints -> 403 Forbidden
    res_traveller_on_admin = client.post(
        "/pricing/calculate",
        json={"entity_id": "rmt_ca391f47", "target_date": "2026-10-15"},
        headers=traveller_headers
    )
    assert res_traveller_on_admin.status_code == 403

    # 2. Admin attempting traveller endpoints -> 403 Forbidden
    res_admin_on_traveller = client.get("/traveller/search?date=2026-10-15", headers=admin_headers)
    assert res_admin_on_traveller.status_code == 403


# ==========================================
# 3. Authenticated Admin Dynamic Pricing & Diagnostics
# ==========================================
def test_calculate_pricing_endpoint(admin_headers):
    payload = {
        "entity_id": "rmt_ca391f47",
        "target_date": "2026-10-15"
    }
    response = client.post("/pricing/calculate", json=payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "effective_price" in data
    assert "base_price" in data
    assert "demand_index" in data
    assert "occupancy_factor" in data
    assert "lead_time_factor" in data
    assert "seasonality_factor" in data
    assert "bound_clamped" in data
    assert "raw_price" in data
    assert isinstance(data["bound_clamped"], bool)
    assert data["effective_price"] > 0
    if data["bound_clamped"]:
        assert data["clamped_by"] in ["ceiling", "floor", "daily_movement"]


def test_explain_pricing_endpoint(admin_headers):
    response = client.get("/pricing/explain?entity_id=rmt_ca391f47&date=2026-10-15", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    
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


def test_pricing_horizon_clamp_diagnostics(admin_headers):
    response = client.get("/pricing/horizon?entity_id=rmt_ca391f47", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "simulated_price_curve" in data
    assert "clamp_summary" in data
    curve = data["simulated_price_curve"]
    assert len(curve) == 30
    
    # Assert live clamp summary structure
    summary = data["clamp_summary"]
    assert summary["total_prices"] == 30
    assert "summary_text" in summary
    assert "ceiling_clamps" in summary
    assert "floor_clamps" in summary
    assert "daily_movement_clamps" in summary
    
    for point in curve:
        assert "date" in point
        assert "simulated_price" in point
        assert "demand_index" in point
        assert "floor_price" in point
        assert "ceiling_price" in point
        assert "clamped" in point
        assert "raw_model_price" in point
        if point["clamped"]:
            assert point["clamped_by"] in ["ceiling", "floor", "daily_movement"]
            assert point["bound_value"] is not None


def test_simulate_pricing_endpoint(admin_headers):
    payload = {
        "entity_id": "rmt_ca391f47",
        "base_multiplier": 1.15,
        "daily_move_limit": 0.20
    }
    response = client.post("/pricing/simulate", json=payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "simulated_price_curve" in data
    assert len(data["simulated_price_curve"]) == 30
    assert "revenue_delta_pct" in data
    assert "booking_rate_delta_pct" in data
    assert "breaches" in data


def test_entities_endpoint(admin_headers):
    response = client.get("/entities", headers=admin_headers)
    assert response.status_code == 200
    entities = response.json()
    assert isinstance(entities, list)
    assert len(entities) > 0


# ==========================================
# 4. Authenticated Traveller Search & Booking Flow
# ==========================================
def test_traveller_search_flow(traveller_headers):
    response = client.get("/traveller/search?date=2026-10-15", headers=traveller_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "entity_id" in first
    assert "entity_name" in first
    assert "available_units" in first
    assert "dynamic_price" in first
    assert "badge_context" in first
    assert "badge_color" in first


def test_traveller_booking_with_user_traceability(traveller_headers):
    target_date = "2026-11-20"
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE inventory_calendar SET booked_units = 0, total_units = 10 WHERE entity_id = 'rmt_ca391f47' AND for_date = ?;",
        (target_date,)
    )
    conn.commit()
    initial_booked = 0
    conn.close()

    # Confirmed booking event by authenticated traveller with exact for_date
    payload = {
        "entity_id": "rmt_ca391f47",
        "event_type": "booking",
        "timestamp": "2026-10-15T10:00:00Z",
        "lead_time_days": 14,
        "for_date": target_date
    }
    resp = client.post("/events", json=payload, headers=traveller_headers)
    assert resp.status_code == 201

    # Verify inventory was incremented for that specific date only
    conn2 = get_db_connection()
    cursor2 = conn2.cursor()
    cursor2.execute(
        "SELECT booked_units FROM inventory_calendar WHERE entity_id = 'rmt_ca391f47' AND for_date = ? LIMIT 1;",
        (target_date,)
    )
    updated_booked = cursor2.fetchone()["booked_units"]

    # Verify pricing_events row has user_id populated and exact for_date
    cursor2.execute(
        "SELECT user_id, session_id, for_date FROM pricing_events WHERE entity_id = 'rmt_ca391f47' ORDER BY rowid DESC LIMIT 1;"
    )
    pe_row = cursor2.fetchone()
    assert pe_row["user_id"] is not None
    assert pe_row["user_id"].startswith("usr_")
    assert pe_row["for_date"] == target_date
    conn2.close()

    assert updated_booked == initial_booked + 1


def test_traveller_booking_sold_out_409(traveller_headers):
    sold_out_date = "2026-12-25"
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure a row exists where booked_units == total_units
    cursor.execute("""
        INSERT INTO inventory_calendar (
            inventory_id, entity_type, entity_id, for_date, total_units,
            booked_units, held_units, price, currency, min_stay_nights,
            closed_to_arrival, updated_at
        ) VALUES ('inv_test_soldout', 'room_type', 'rmt_ca391f47', ?, 5, 5, 0, '5000', 'INR', 1, 0, '2026-10-01')
        ON CONFLICT(inventory_id) DO UPDATE SET booked_units = 5, total_units = 5, held_units = 0;
    """, (sold_out_date,))
    conn.commit()

    cursor.execute("SELECT COUNT(*) as cnt FROM pricing_events WHERE entity_id = 'rmt_ca391f47' AND for_date = ?;", (sold_out_date,))
    events_before = cursor.fetchone()["cnt"]
    conn.close()

    # Attempt to book sold-out unit
    payload = {
        "entity_id": "rmt_ca391f47",
        "event_type": "booking",
        "timestamp": "2026-10-15T10:00:00Z",
        "lead_time_days": 10,
        "for_date": sold_out_date
    }
    resp = client.post("/events", json=payload, headers=traveller_headers)
    assert resp.status_code == 409
    data = resp.json()
    assert data["detail"] == "This unit is sold out for your selected dates."

    # Verify atomic rollback: pricing_events row was NOT inserted
    conn2 = get_db_connection()
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT COUNT(*) as cnt FROM pricing_events WHERE entity_id = 'rmt_ca391f47' AND for_date = ?;", (sold_out_date,))
    events_after = cursor2.fetchone()["cnt"]
    conn2.close()

    assert events_after == events_before


# ==========================================
# 5. ML Forecaster Pipeline & Diagnostic Tests
# ==========================================
def test_forecaster_metrics_endpoint(admin_headers):
    resp = client.get("/pricing/forecaster/metrics", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["dedup_removed_count"] >= 23
    assert data["outlier_clip_threshold"] > 10000000.0  # ~17.11M
    assert data["test_mae"] is not None
    assert data["naive_mae"] is not None
    assert data["test_mae"] <= data["naive_mae"]  # Model beats naive baseline
    assert data["test_r2"] > data["naive_r2"]     # Model R2 beats naive negative R2
    assert "coefficients" in data
    assert "demand_index" in data["coefficients"]
    assert "occupancy_pct" in data["coefficients"]
    assert "is_peak_month" in data["coefficients"]


def test_pricing_explain_reads_real_coefficients(admin_headers):
    resp = client.get("/pricing/explain?entity_id=rmt_ca391f47&date=2026-10-15", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "factors" in data
    factor_names = [f["name"] for f in data["factors"]]
    # Verify Ridge coefficient beta is reflected in the factor display name
    assert any("ML Ridge beta=" in name for name in factor_names)


if __name__ == "__main__":
    pytest.main(["-v", __file__])

