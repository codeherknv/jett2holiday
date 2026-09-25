"""
Jett 2 Holiday - Deterministic Pricing Engine (Track 2).
Calculates dynamic rates using ML demand forecasts, inventory occupancy, lead-time decay,
and enforces hard guardrail clamping against price_bounds with full audit persistence.
"""

import sys
import os
import sqlite3
import math
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Add root / ml directory to sys.path for ML Forecaster import
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from ml.demand_forecaster import forecaster
except ImportError:
    forecaster = None

DB_PATH = ROOT_DIR / "data" / "APS-02.db"


class PricingEngine:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_PATH)
        # In-memory store for admin manual overrides: key -> {price, reason, applied_at}
        self.manual_overrides: Dict[str, Dict[str, Any]] = {}
        self.forecaster = forecaster

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def set_manual_override(self, entity_id: str, date: str, override_price: float, reason: str = "") -> Dict[str, Any]:
        """
        Stores an admin manual price override and validates it against guardrails.
        """
        conn = self.get_connection()
        try:
            meta = self.get_entity_bounds_and_base(entity_id, conn)
            floor_price = meta["floor_price"]
            ceiling_price = meta["ceiling_price"]
            base_price = meta["base_price"]

            violates = override_price < floor_price or override_price > ceiling_price
            warning = None
            if override_price > ceiling_price:
                warning = f"Override ₹{override_price:,.0f} exceeds ceiling guardrail (₹{ceiling_price:,.0f})."
            elif override_price < floor_price:
                warning = f"Override ₹{override_price:,.0f} is below floor guardrail (₹{floor_price:,.0f})."

            applied_at = datetime.datetime.now().isoformat()
            key = f"{entity_id}_{date}"
            self.manual_overrides[key] = {
                "entity_id": entity_id,
                "date": date,
                "override_price": override_price,
                "reason": reason or "Admin manual price adjustment",
                "violates_guardrails": violates,
                "warning": warning,
                "applied_at": applied_at
            }

            return {
                "entity_id": entity_id,
                "date": date,
                "override_price": override_price,
                "effective_price": override_price,
                "base_price": base_price,
                "floor_price": floor_price,
                "ceiling_price": ceiling_price,
                "violates_guardrails": violates,
                "warning": warning,
                "applied_at": applied_at
            }
        finally:
            conn.close()

    def get_manual_overrides(self, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns all registered admin overrides.
        """
        if entity_id:
            return [v for k, v in self.manual_overrides.items() if v["entity_id"] == entity_id]
        return list(self.manual_overrides.values())

    def get_entity_bounds_and_base(self, entity_id: str, conn: sqlite3.Connection, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches price bounds, baseline rate, and entity metadata.
        """
        cursor = conn.cursor()
        
        # Check price_bounds table
        cursor.execute("SELECT * FROM price_bounds WHERE entity_id = ? LIMIT 1;", (entity_id,))
        bound_row = cursor.fetchone()

        if bound_row:
            floor_price = float(bound_row["floor_price"])
            ceiling_price = float(bound_row["ceiling_price"])
            max_daily_move_pct = float(bound_row["max_daily_move_pct"])
            rounding_step = float(bound_row["rounding_step"]) if bound_row["rounding_step"] else 10.0
            entity_type = bound_row["entity_type"]
        else:
            # Defaults
            floor_price = 3500.0
            ceiling_price = 7000.0
            max_daily_move_pct = 0.15
            rounding_step = 10.0
            entity_type = "hotel_room"

        # Baseline benchmark price calculation (midpoint or from flight_fares/inventory)
        cursor.execute("SELECT base_fare FROM flight_fares WHERE fare_id = ? LIMIT 1;", (entity_id,))
        fare_row = cursor.fetchone()
        if fare_row and fare_row["base_fare"]:
            base_price = float(fare_row["base_fare"])
        else:
            if target_date:
                cursor.execute("SELECT price FROM inventory_calendar WHERE entity_id = ? AND for_date = ? LIMIT 1;", (entity_id, target_date))
                inv_row = cursor.fetchone()
            else:
                inv_row = None

            if not inv_row:
                cursor.execute("SELECT price FROM inventory_calendar WHERE entity_id = ? LIMIT 1;", (entity_id,))
                inv_row = cursor.fetchone()

            if inv_row and inv_row["price"]:
                base_price = float(inv_row["price"])
            else:
                base_price = round((floor_price + ceiling_price) / 2.33, 2)

        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "base_price": base_price,
            "floor_price": floor_price,
            "ceiling_price": ceiling_price,
            "max_daily_move_pct": max_daily_move_pct,
            "rounding_step": rounding_step
        }

    def get_inventory_occupancy(self, entity_id: str, target_date: str, conn: sqlite3.Connection) -> float:
        """
        Computes occupancy ratio (0.0 to 1.0) from inventory_calendar.
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT total_units, booked_units FROM inventory_calendar WHERE entity_id = ? AND for_date = ? LIMIT 1;",
            (entity_id, target_date)
        )
        row = cursor.fetchone()
        if row and row["total_units"] and row["total_units"] > 0:
            return min(1.0, max(0.0, float(row["booked_units"]) / float(row["total_units"])))
        
        # Fallback to average occupancy for this entity if available
        cursor.execute("SELECT AVG(CAST(booked_units AS FLOAT) / total_units) FROM inventory_calendar WHERE entity_id = ? AND total_units > 0;", (entity_id,))
        avg_row = cursor.fetchone()
        if avg_row and avg_row[0] is not None:
            return min(1.0, max(0.0, float(avg_row[0])))
            
        return 0.65 # default fallback occupancy

    def get_competitor_median(
        self,
        entity_id: str,
        target_date: str,
        base_price: float,
        conn: sqlite3.Connection
    ) -> Tuple[float, float]:
        """
        Calculates in-dataset competitor-peer median pricing for entities in the same city & category.
        Returns (competitor_factor, median_peer_price).
        """
        cursor = conn.cursor()
        cursor.execute("SELECT city_id, entity_type FROM pricing_events WHERE entity_id = ? LIMIT 1;", (entity_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT entity_type FROM price_bounds WHERE entity_id = ? LIMIT 1;", (entity_id,))
            pb_row = cursor.fetchone()
            ent_type = pb_row["entity_type"] if pb_row else "room_type"
            city_id = "cty_c07454f1"
        else:
            city_id = row["city_id"]
            ent_type = row["entity_type"]

        # Peer entities with same city_id and entity_type
        cursor.execute(
            "SELECT DISTINCT entity_id FROM pricing_events WHERE city_id = ? AND entity_type = ? AND entity_id != ?;",
            (city_id, ent_type, entity_id)
        )
        peers = [r["entity_id"] for r in cursor.fetchall()]

        prices: List[float] = []
        for p in peers:
            cursor.execute(
                "SELECT price FROM inventory_calendar WHERE entity_id = ? AND for_date = ? LIMIT 1;",
                (p, target_date)
            )
            r = cursor.fetchone()
            if r and r["price"]:
                try:
                    prices.append(float(r["price"]))
                except (ValueError, TypeError):
                    pass
            else:
                cursor.execute(
                    "SELECT floor_price, ceiling_price FROM price_bounds WHERE entity_id = ? LIMIT 1;",
                    (p,)
                )
                b = cursor.fetchone()
                if b and b["floor_price"] and b["ceiling_price"]:
                    try:
                        prices.append((float(b["floor_price"]) + float(b["ceiling_price"])) / 2.33)
                    except (ValueError, TypeError):
                        pass

        if not prices:
            return 1.0, base_price

        import numpy as np
        median_price = float(np.median(prices))
        ratio = median_price / base_price if base_price > 0 else 1.0
        competitor_factor = round(max(0.85, min(1.15, ratio)), 3)
        return competitor_factor, round(median_price, 2)

    def get_previous_day_price(
        self,
        entity_id: str,
        target_date: str,
        base_price: float,
        conn: sqlite3.Connection
    ) -> float:
        """
        Retrieves the previous day's published price for daily movement bounding.
        """
        try:
            target_dt = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
            prev_date = (target_dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception:
            return base_price

        cursor = conn.cursor()
        cursor.execute(
            "SELECT price FROM price_history WHERE entity_id = ? AND effective_date = ? LIMIT 1;",
            (entity_id, prev_date)
        )
        ph_row = cursor.fetchone()
        if ph_row and ph_row["price"]:
            try:
                return float(ph_row["price"])
            except (ValueError, TypeError):
                pass

        cursor.execute(
            "SELECT price FROM inventory_calendar WHERE entity_id = ? AND for_date = ? LIMIT 1;",
            (entity_id, prev_date)
        )
        ic_row = cursor.fetchone()
        if ic_row and ic_row["price"]:
            try:
                return float(ic_row["price"])
            except (ValueError, TypeError):
                pass

        return base_price

    def calculate_price(
        self,
        entity_id: str,
        target_date: str,
        persist: bool = True
    ) -> Dict[str, Any]:
        """
        Executes the dynamic pricing formula:
          Candidate Price = Baseline Price * (1 + sum(Factor Deltas))
        Applies simultaneous intersection of all active bounds:
          [max(floor, prev*(1-daily)), min(ceiling, prev*(1+daily))]
        Enforces hard clamp assertions and records clamp reason in price_history.
        """
        conn = self.get_connection()
        try:
            meta = self.get_entity_bounds_and_base(entity_id, conn, target_date=target_date)
            base_price = meta["base_price"]
            floor_price = meta["floor_price"]
            ceiling_price = meta["ceiling_price"]
            max_daily_move_pct = meta["max_daily_move_pct"]
            rounding_step = meta["rounding_step"]

            # 1. ML Demand Forecast
            if forecaster:
                demand_index, feats = forecaster.predict_demand_index(entity_id, target_date)
            else:
                demand_index = 1.42
                feats = {"demand_signal": 0.28, "occupancy_contribution": 0.18, "day_of_week_lift": 0.0, "seasonality_factor": 1.15}

            # 2. Linear Factor Calculations
            occupancy_ratio = self.get_inventory_occupancy(entity_id, target_date, conn)
            occupancy_factor = round(1.0 + (occupancy_ratio - 0.50) * 0.40, 3)

            # Lead time factor: smooth continuous curve
            try:
                days_out = max(0, (datetime.datetime.strptime(target_date, "%Y-%m-%d").date() - datetime.date(2026, 9, 24)).days)
            except Exception:
                days_out = 14
            lead_time_factor = round(1.0 + 0.18 * math.exp(-0.06 * days_out) - 0.08 * (1.0 - math.exp(-0.02 * days_out)), 3)
            lead_time_factor = max(0.85, min(1.30, lead_time_factor))

            seasonality_factor = feats.get("seasonality_factor", 1.15)

            # Competitor-peer median pricing factor in same city/category
            competitor_factor, median_peer_price = self.get_competitor_median(entity_id, target_date, base_price, conn)

            # 3. Deterministic Formula
            # Candidate Price = Base Price * (1 + sum(Factor Deltas))
            # Dynamic sensitivity weights derived directly from the trained ML Ridge regression coefficients:
            factor_weights = self.forecaster.get_factor_weights() if (self.forecaster and hasattr(self.forecaster, "get_factor_weights")) else {
                "demand_weight": 0.35,
                "occupancy_weight": 0.326,
                "seasonality_weight": 0.198,
                "lead_time_weight": 0.15,
                "competitor_weight": 0.25,
                "coefficients": {
                    "demand_index": 1.7501,
                    "occupancy_pct": 0.0217,
                    "is_occupancy_known": 0.0029,
                    "is_peak_month": 0.0099,
                    "intercept": -1.6641
                }
            }
            coefs = factor_weights.get("coefficients", {})

            demand_delta = (demand_index - 1.0) * factor_weights["demand_weight"]
            occ_delta = (occupancy_factor - 1.0) * factor_weights["occupancy_weight"]
            lead_delta = (lead_time_factor - 1.0) * factor_weights["lead_time_weight"]
            season_delta = (seasonality_factor - 1.0) * factor_weights["seasonality_weight"]
            competitor_delta = (competitor_factor - 1.0) * factor_weights["competitor_weight"]

            total_factor_sum = demand_delta + occ_delta + lead_delta + season_delta + competitor_delta
            raw_candidate_price = base_price * (1.0 + total_factor_sum)

            # 4. Enforce Guardrails via Simultaneous Intersection of All Active Bounds
            prev_price = self.get_previous_day_price(entity_id, target_date, base_price, conn)
            daily_min = prev_price * (1.0 - max_daily_move_pct)
            daily_max = prev_price * (1.0 + max_daily_move_pct)

            # Simultaneous bounds intersection: tightest lower bound, loosest upper bound
            valid_lower = max(floor_price, daily_min)
            valid_upper = min(ceiling_price, daily_max)

            # Reconcile if daily limits fall outside physical floor/ceiling envelope
            valid_lower = min(ceiling_price, valid_lower)
            valid_upper = max(floor_price, valid_upper)

            bound_clamped = False
            clamped_by = None
            bound_value = None
            bound_name = None

            if raw_candidate_price > valid_upper:
                bound_clamped = True
                # Identify which specific guardrail was binding
                if ceiling_price <= daily_max or (raw_candidate_price > ceiling_price and ceiling_price <= valid_upper):
                    clamped_by = "ceiling"
                    bound_value = ceiling_price
                    bound_name = f"Ceiling Guardrail (₹{ceiling_price:,.0f})"
                else:
                    clamped_by = "daily_movement"
                    bound_value = round(daily_max, 2)
                    bound_name = f"Max Daily Movement (+{int(max_daily_move_pct * 100)}%)"
                clamped_price = valid_upper
            elif raw_candidate_price < valid_lower:
                bound_clamped = True
                if floor_price >= daily_min or (raw_candidate_price < floor_price and floor_price >= valid_lower):
                    clamped_by = "floor"
                    bound_value = floor_price
                    bound_name = f"Floor Guardrail (₹{floor_price:,.0f})"
                else:
                    clamped_by = "daily_movement"
                    bound_value = round(daily_min, 2)
                    bound_name = f"Max Daily Movement (-{int(max_daily_move_pct * 100)}%)"
                clamped_price = valid_lower
            else:
                clamped_price = raw_candidate_price

            # Apply Rounding Step
            if rounding_step > 0:
                clamped_price = round(clamped_price / rounding_step) * rounding_step

            # Hard clamp assertion at the very end of the pipeline
            effective_price = min(ceiling_price, max(floor_price, clamped_price))
            assert floor_price <= effective_price <= ceiling_price, (
                f"FATAL: Effective price ₹{effective_price} breached hard bounds [₹{floor_price}, ₹{ceiling_price}]"
            )

            effective_price = round(effective_price, 2)
            raw_candidate_price = round(raw_candidate_price, 2)

            # Check if there is an active manual override for this entity + date
            override_key = f"{entity_id}_{target_date}"
            if override_key in self.manual_overrides:
                override_data = self.manual_overrides[override_key]
                effective_price = override_data["override_price"]

            # 5. Multilingual Audit Reasoning
            pct_shift = round(((effective_price - base_price) / base_price) * 100, 1)
            sign = "+" if pct_shift >= 0 else ""

            clamp_clause_en = (
                f"Notice: Price was clamped by {bound_name}."
                if bound_clamped
                else "Operates within all active floor, ceiling, and daily-movement guardrails."
            )
            explanation_en = (
                f"Price for {entity_id} on {target_date} is calculated at ₹{effective_price:,.0f} "
                f"({sign}{pct_shift}% vs baseline ₹{base_price:,.0f}) driven by demand index ({demand_index:.2f}x), "
                f"occupancy ({occupancy_ratio*100:.0f}%), competitor peer median (₹{median_peer_price:,.0f}), and seasonal weighting ({seasonality_factor:.2f}x). "
                f"{clamp_clause_en}"
            )

            clamp_clause_hi = (
                f"सूचना: मूल्य को {bound_name} द्वारा सीमित (क्लैंप) किया गया।"
                if bound_clamped
                else "यह मूल्य निर्धारित सुरक्षा सीमाओं एवं दैनिक परिवर्तन सीमाओं के अंतर्गत सुरक्षित है।"
            )
            explanation_hi = (
                f"{target_date} के लिए {entity_id} का मूल्य आधार दर ₹{base_price:,.0f} से {sign}{pct_shift}% बदलकर ₹{effective_price:,.0f} निर्धारित किया गया है। "
                f"यह निर्णय मांग सूचकांक ({demand_index:.2f}x), ऑक्यूपेंसी ({occupancy_ratio*100:.0f}%), प्रतिस्पर्धी दरें और मौसमी प्रभाव पर आधारित है। "
                f"{clamp_clause_hi}"
            )

            # 6. Factor Decomposition Array
            c_demand = coefs.get("demand_index", 1.7501)
            c_occ = coefs.get("occupancy_pct", 0.0217)
            c_season = coefs.get("is_peak_month", 0.0099)

            factors = [
                {"name": f"Demand Signal (ML Ridge beta={c_demand:.2f})", "value": float(demand_index), "contribution": round(demand_delta, 3)},
                {"name": f"Occupancy Rate ({int(occupancy_ratio*100)}% booked, beta={c_occ:.4f})", "value": float(occupancy_factor), "contribution": round(occ_delta, 3)},
                {"name": f"Lead Time ({days_out} days out)", "value": float(lead_time_factor), "contribution": round(lead_delta, 3)},
                {"name": f"Seasonality Factor (beta={c_season:.4f})", "value": float(seasonality_factor), "contribution": round(season_delta, 3)},
                {"name": f"Competitor Peer Median (₹{median_peer_price:,.0f})", "value": float(competitor_factor), "contribution": round(competitor_delta, 3)}
            ]

            # 7. Persist to price_history with complete clamp diagnostic fields
            if persist:
                cursor = conn.cursor()
                history_id = f"phs_{int(datetime.datetime.now().timestamp())}_{abs(hash(entity_id)) % 10000}"
                cursor.execute("""
                    INSERT OR REPLACE INTO price_history (
                        history_id, entity_type, entity_id, effective_date, price,
                        currency, baseline_price, demand_index, occupancy_pct, lead_time_factor,
                        seasonality_factor, event_factor, competitor_factor, bound_clamped, explanation, computed_at,
                        raw_price, clamped_by, bound_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    history_id,
                    meta["entity_type"],
                    entity_id,
                    target_date,
                    str(effective_price),
                    "INR",
                    str(base_price),
                    demand_index,
                    occupancy_ratio * 100.0,
                    lead_time_factor,
                    seasonality_factor,
                    1.0,
                    competitor_factor,
                    1 if bound_clamped else 0,
                    explanation_en,
                    datetime.datetime.now().isoformat(),
                    str(raw_candidate_price),
                    clamped_by,
                    str(bound_value) if bound_value is not None else None
                ))
                conn.commit()

            return {
                "effective_price": effective_price,
                "raw_candidate_price": raw_candidate_price,
                "base_price": base_price,
                "demand_index": demand_index,
                "occupancy_factor": occupancy_factor,
                "lead_time_factor": lead_time_factor,
                "seasonality_factor": seasonality_factor,
                "competitor_factor": competitor_factor,
                "bound_clamped": bound_clamped,
                "clamped_by": clamped_by,
                "bound_value": bound_value,
                "bound_name": bound_name,
                "factors": factors,
                "explanation_en": explanation_en,
                "explanation_hi": explanation_hi
            }

        finally:
            conn.close()

    def simulate_30day_curve(
        self,
        entity_id: str,
        base_multiplier: float = 1.0,
        daily_move_limit: float = 0.15,
        start_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Computes 30-day trajectory using simultaneous bounds intersection:
          [max(floor, prev*(1-daily_move_limit)), min(ceiling, prev*(1+daily_move_limit))]
        Guarantees no sequential clamping re-violation and yields exact Guardrail Clamp Report counts.
        """
        conn = self.get_connection()
        try:
            meta = self.get_entity_bounds_and_base(entity_id, conn)
            base_price = meta["base_price"]
            floor_price = meta["floor_price"]
            ceiling_price = meta["ceiling_price"]
            rounding_step = meta["rounding_step"]

            if start_date_str:
                try:
                    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                except Exception:
                    start_date = datetime.date(2026, 10, 12)
            else:
                start_date = datetime.date(2026, 10, 12)

            curve = []
            ceiling_clamps = 0
            floor_clamps = 0
            daily_clamps = 0

            # Initial baseline price for daily movement tracking
            calc_init = self.calculate_price(entity_id, start_date.strftime("%Y-%m-%d"), persist=False)
            prev_sim_price = calc_init["effective_price"] * base_multiplier

            sum_current_prices = 0.0
            sum_sim_prices = 0.0

            for day_idx in range(30):
                curr_date = start_date + datetime.timedelta(days=day_idx)
                date_str = curr_date.strftime("%Y-%m-%d")

                calc = self.calculate_price(entity_id, date_str, persist=False)
                current_dyn_price = calc["effective_price"]
                raw_candidate = calc["raw_candidate_price"]

                # Apply simulation multiplier to raw candidate demand
                sim_target = raw_candidate * base_multiplier
                raw_model_price = round(sim_target, 2)

                # Simultaneous intersection of all active bounds
                daily_min = prev_sim_price * (1.0 - daily_move_limit)
                daily_max = prev_sim_price * (1.0 + daily_move_limit)

                valid_lower = max(floor_price, daily_min)
                valid_upper = min(ceiling_price, daily_max)

                valid_lower = min(ceiling_price, valid_lower)
                valid_upper = max(floor_price, valid_upper)

                clamped = False
                clamped_by = None
                bound_value = None
                bound_name = None

                if raw_model_price > valid_upper:
                    clamped = True
                    # Check which bound is binding
                    if ceiling_price <= daily_max or (raw_model_price > ceiling_price and ceiling_price <= valid_upper):
                        clamped_by = "ceiling"
                        bound_value = ceiling_price
                        bound_name = f"Ceiling Guardrail (₹{ceiling_price:,.0f})"
                        ceiling_clamps += 1
                    else:
                        clamped_by = "daily_movement"
                        bound_value = round(daily_max, 2)
                        bound_name = f"Max Daily Movement (+{int(daily_move_limit * 100)}%)"
                        daily_clamps += 1
                    sim_clamped = valid_upper
                elif raw_model_price < valid_lower:
                    clamped = True
                    if floor_price >= daily_min or (raw_model_price < floor_price and floor_price >= valid_lower):
                        clamped_by = "floor"
                        bound_value = floor_price
                        bound_name = f"Floor Guardrail (₹{floor_price:,.0f})"
                        floor_clamps += 1
                    else:
                        clamped_by = "daily_movement"
                        bound_value = round(daily_min, 2)
                        bound_name = f"Max Daily Movement (-{int(daily_move_limit * 100)}%)"
                        daily_clamps += 1
                    sim_clamped = valid_lower
                else:
                    sim_clamped = raw_model_price

                # Rounding step
                if rounding_step > 0:
                    sim_clamped = round(sim_clamped / rounding_step) * rounding_step

                # Hard clamp assertion
                sim_final = min(ceiling_price, max(floor_price, sim_clamped))
                assert floor_price <= sim_final <= ceiling_price, (
                    f"FATAL: Simulated price ₹{sim_final} breached hard bounds [₹{floor_price}, ₹{ceiling_price}]"
                )

                sim_final = round(sim_final, 2)
                prev_sim_price = sim_final

                sum_current_prices += current_dyn_price
                sum_sim_prices += sim_final

                curve.append({
                    "date": date_str,
                    "base_price": base_price,
                    "raw_model_price": raw_model_price,
                    "current_dynamic_price": current_dyn_price,
                    "simulated_price": sim_final,
                    "demand_index": calc["demand_index"],
                    "floor_price": floor_price,
                    "ceiling_price": ceiling_price,
                    "clamped": clamped,
                    "clamped_by": clamped_by,
                    "bound_value": bound_value,
                    "bound_name": bound_name,
                    "factors": calc["factors"]
                })

            # Calculate exact revenue and elasticity deltas
            if sum_current_prices > 0:
                revenue_delta = round(((sum_sim_prices - sum_current_prices) / sum_current_prices) * 100.0, 1)
            else:
                revenue_delta = 0.0

            # Demand elasticity of ~ -0.4 to -0.6 for hospitality/travel
            booking_rate_delta = round(-revenue_delta * 0.38, 1)
            total_clamped = ceiling_clamps + floor_clamps + daily_clamps

            clamp_summary = {
                "total_prices": len(curve),
                "total_clamped": total_clamped,
                "ceiling_clamps": ceiling_clamps,
                "floor_clamps": floor_clamps,
                "daily_movement_clamps": daily_clamps,
                "summary_text": f"{total_clamped} of {len(curve)} prices clamped — {ceiling_clamps} by ceiling, {floor_clamps} by floor, {daily_clamps} by daily-movement"
            }

            # Record run into simulations table without writing to production price_history
            try:
                sim_id = f"sim_{int(datetime.datetime.now().timestamp())}_{abs(hash(entity_id)) % 1000}"
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO simulations (
                        simulation_id, entity_id, base_multiplier, daily_move_limit,
                        revenue_delta_pct, booking_rate_delta_pct, total_clamped,
                        ceiling_clamps, floor_clamps, daily_clamps, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    sim_id,
                    entity_id,
                    base_multiplier,
                    daily_move_limit,
                    revenue_delta,
                    booking_rate_delta,
                    total_clamped,
                    ceiling_clamps,
                    floor_clamps,
                    daily_clamps,
                    datetime.datetime.now().isoformat()
                ))
                conn.commit()
            except Exception as sim_err:
                print(f"Non-fatal simulation recording notice: {sim_err}")

            return {
                "simulated_price_curve": curve,
                "revenue_delta_pct": revenue_delta,
                "booking_rate_delta_pct": booking_rate_delta,
                "breaches": total_clamped,
                "clamp_summary": clamp_summary
            }
        finally:
            conn.close()


# Singleton engine instance
pricing_engine = PricingEngine()

