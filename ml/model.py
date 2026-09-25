"""
APS-02 hierarchical pooled time-series demand forecaster.

Core idea:
    Instead of fitting 170 independent short Prophet series, learn the
    common temporal shape from all entities together, then personalize that
    common forecast with each entity's historical level and weekday residual.

This remains a time-series model:
    historical demand_index -> pooled temporal series -> Prophet forecast
    -> entity-level reconstruction.

Optional external regressors are aggregated across entities per day and are
used only when they have real historical variation and a non-constant future
path. No target-derived future values are used.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from prophet import Prophet
except ImportError:  # pragma: no cover
    Prophet = None


FORECAST_DAYS = 30
FORECAST_START = pd.Timestamp("2026-09-01")

MIN_TARGET = 0.20
MAX_TARGET = 2.00

# A small set of genuine future-known numeric signals. These are aggregated
# across entities into a daily global series before entering Prophet.
GLOBAL_REGRESSOR_CANDIDATES = [
    "searches_7d",
    "views_7d",
    "bookings_7d",
    "events_7d",
    "booking_rate_7d",
    "conversion_rate_7d",
    "price_floor_ratio",
    "price_ceiling_ratio",
    "is_peak_month",
]
MAX_GLOBAL_REGRESSORS = 2

# Artifact paths (supports both ml/artifacts and repo root artifacts/)
ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIRS = [
    ROOT_DIR / "artifacts",
    Path(__file__).resolve().parent / "artifacts",
]
MODEL_METADATA_PATH = ROOT_DIR / "artifacts" / "pooled_timeseries_metadata.json"


def _clean_history(features_df: pd.DataFrame) -> pd.DataFrame:
    required = {"entity_id", "for_date", "demand_index"}
    missing = required - set(features_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = features_df.copy()
    out["for_date"] = pd.to_datetime(out["for_date"], errors="coerce")
    out["demand_index"] = pd.to_numeric(out["demand_index"], errors="coerce")
    out = out.dropna(subset=["entity_id", "for_date", "demand_index"])
    return out.sort_values(["entity_id", "for_date"]).reset_index(drop=True)


def _entity_levels(history: pd.DataFrame) -> pd.Series:
    """Robust entity baseline from the historical target only."""
    full = history.groupby("entity_id")["demand_index"].median()
    recent = (
        history.sort_values("for_date")
        .groupby("entity_id")
        .tail(min(14, history["for_date"].nunique()))
        .groupby("entity_id")["demand_index"]
        .median()
    )
    levels = 0.40 * full + 0.60 * recent
    return levels.clip(lower=MIN_TARGET, upper=MAX_TARGET)


def _normalized_history(history: pd.DataFrame, levels: pd.Series) -> pd.DataFrame:
    out = history.copy()
    out["entity_level"] = out["entity_id"].map(levels)
    out["normalized_y"] = out["demand_index"] / out["entity_level"]
    out["weekday"] = out["for_date"].dt.weekday
    return out


def _choose_global_regressors(
    normalized_history: pd.DataFrame,
    future_features: pd.DataFrame | None,
) -> list[str]:
    """Select at most two global daily regressors using training only."""
    if future_features is None:
        return []

    scored: list[tuple[str, float]] = []
    hist = normalized_history.copy()
    hist["for_date"] = pd.to_datetime(hist["for_date"])
    future = future_features.copy()
    future["for_date"] = pd.to_datetime(future["for_date"])

    global_target = (
        hist.groupby("for_date")["normalized_y"]
        .median()
        .rename("target")
    )

    for col in GLOBAL_REGRESSOR_CANDIDATES:
        if col not in hist.columns or col not in future.columns:
            continue

        h = (
            hist.assign(value=pd.to_numeric(hist[col], errors="coerce"))
            .groupby("for_date")["value"]
            .median()
        )
        f = (
            future.assign(value=pd.to_numeric(future[col], errors="coerce"))
            .groupby("for_date")["value"]
            .median()
        )

        if h.nunique(dropna=True) < 2:
            continue
        if f.nunique(dropna=True) < 2:
            continue

        aligned = pd.concat([global_target, h], axis=1).dropna()
        if len(aligned) < 5 or aligned["value"].nunique() < 2:
            continue

        corr = aligned["target"].corr(aligned["value"])
        if pd.notna(corr):
            scored.append((col, abs(float(corr))))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in scored[:MAX_GLOBAL_REGRESSORS]]


def _build_global_frame(
    normalized_history: pd.DataFrame,
    regressor_source: pd.DataFrame | None,
    regressors: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Build pooled daily target and pooled future regressor paths."""
    train_global = (
        normalized_history.groupby("for_date")["normalized_y"]
        .median()
        .reset_index(name="y")
        .rename(columns={"for_date": "ds"})
    )

    if not regressors or regressor_source is None:
        return train_global, None

    source = regressor_source.copy()
    source["for_date"] = pd.to_datetime(source["for_date"], errors="coerce")

    for col in regressors:
        source[col] = pd.to_numeric(source[col], errors="coerce")

    global_future = (
        source.groupby("for_date")[regressors]
        .median()
        .reset_index()
        .rename(columns={"for_date": "ds"})
    )

    for col in regressors:
        train_values = (
            normalized_history.groupby("for_date")[col]
            .median()
            if col in normalized_history.columns
            else pd.Series(dtype=float)
        )
        train_global[col] = train_global["ds"].map(train_values)

        fallback = pd.to_numeric(train_global[col], errors="coerce").median()
        if pd.isna(fallback):
            fallback = 0.0
        train_global[col] = train_global[col].fillna(fallback)
        global_future[col] = global_future[col].fillna(fallback)

        # Keep the future path within the historical support.
        lo = train_global[col].quantile(0.01)
        hi = train_global[col].quantile(0.99)
        if pd.notna(lo) and pd.notna(hi) and lo < hi:
            global_future[col] = global_future[col].clip(lo, hi)

    return train_global, global_future


def _fit_global_prophet(train_global: pd.DataFrame, regressors: list[str]):
    if Prophet is None:
        raise ImportError(
            "Prophet is not installed. Install it with: "
            "python -m pip install prophet"
        )

    model = Prophet(
        growth="linear",
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="additive",
        changepoint_prior_scale=0.02,
        seasonality_prior_scale=3.0,
        n_changepoints=min(4, max(1, len(train_global) // 7)),
        interval_width=0.80,
    )

    for col in regressors:
        model.add_regressor(col, standardize=True, mode="additive")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(train_global[["ds", "y"] + regressors])

    return model


def _seasonal_naive_global(
    normalized_history: pd.DataFrame,
    future_dates: pd.DatetimeIndex,
) -> pd.Series:
    """Pooled weekly fallback using the last observed normalized week."""
    global_daily = (
        normalized_history.groupby("for_date")["normalized_y"]
        .median()
        .sort_index()
    )
    recent = global_daily.tail(7).to_numpy(dtype=float)
    if len(recent) == 0:
        recent = np.array([1.0])
    values = np.resize(recent, len(future_dates))
    return pd.Series(values, index=future_dates)


def forecast_all_entities(
    features_df: pd.DataFrame,
    future_features: pd.DataFrame | None = None,
    forecast_days: int = FORECAST_DAYS,
    max_entities: int | None = None,
    forecast_start: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Hierarchical pooled time-series forecast.

    One global temporal model learns the shared shape. Each entity keeps its
    own historical level plus a shrinkage weekday residual.
    """
    history = _clean_history(features_df)

    if future_features is not None:
        future_features = future_features.copy()
        future_features["for_date"] = pd.to_datetime(
            future_features["for_date"], errors="coerce"
        )

    if forecast_start is None:
        forecast_start = history["for_date"].max() + pd.Timedelta(days=1)
    else:
        forecast_start = pd.Timestamp(forecast_start)

    future_dates = pd.date_range(
        start=forecast_start,
        periods=forecast_days,
        freq="D",
    )

    entity_ids = history["entity_id"].drop_duplicates().tolist()
    if max_entities is not None:
        entity_ids = entity_ids[:max_entities]
        history = history[history["entity_id"].isin(entity_ids)].copy()
        if future_features is not None:
            future_features = future_features[
                future_features["entity_id"].isin(entity_ids)
            ].copy()

    levels = _entity_levels(history)
    normalized = _normalized_history(history, levels)

    regressors = _choose_global_regressors(normalized, future_features)
    train_global, future_global = _build_global_frame(
        normalized,
        future_features,
        regressors,
    )

    print(
        f"Generating {forecast_days}-day forecasts for "
        f"{len(entity_ids)} entities..."
    )
    print("Model: hierarchical pooled Prophet time-series")
    print(
        "Global regressors: "
        + (", ".join(regressors) if regressors else "none")
    )

    global_forecast = None
    global_in_sample = None
    model_name = "seasonal_naive_pooled"

    try:
        model = _fit_global_prophet(train_global, regressors)
        future_global_frame = pd.DataFrame({"ds": future_dates})

        if regressors:
            if future_global is None:
                raise ValueError("Future global regressor frame is missing.")
            future_global_frame = future_global_frame.merge(
                future_global,
                on="ds",
                how="left",
            )
            for col in regressors:
                fallback = train_global[col].median()
                future_global_frame[col] = future_global_frame[col].fillna(fallback)

        prediction = model.predict(future_global_frame)
        global_forecast = pd.Series(
            prediction["yhat"].to_numpy(dtype=float),
            index=future_dates,
        )

        train_prediction = model.predict(train_global[["ds"] + regressors])
        global_in_sample = pd.Series(
            train_prediction["yhat"].to_numpy(dtype=float),
            index=pd.to_datetime(train_global["ds"]),
        )
        model_name = "prophet_pooled"
    except Exception as exc:
        print(
            f"[WARNING] Pooled Prophet failed: {type(exc).__name__}: {exc}. "
            "Using pooled seasonal-naive fallback."
        )
        global_forecast = _seasonal_naive_global(normalized, future_dates)

        last_week = normalized.groupby("for_date")["normalized_y"].median().tail(7)
        global_in_sample = last_week

    # Pooled weekday shape used as a shrinkage target.
    pooled_weekday = (
        normalized.groupby("weekday")["normalized_y"]
        .median()
    )
    pooled_weekday = pooled_weekday / pooled_weekday.median()

    forecasts: list[pd.DataFrame] = []
    metadata: list[dict] = []

    for entity_number, entity_id in enumerate(entity_ids, start=1):
        entity_hist = normalized[normalized["entity_id"] == entity_id].copy()
        level = float(levels.loc[entity_id])

        residuals = []
        for _, row in entity_hist.iterrows():
            base = global_in_sample.get(row["for_date"], np.nan)
            if pd.notna(base) and base > 0:
                residuals.append(
                    {
                        "weekday": int(row["weekday"]),
                        "ratio": float(row["normalized_y"] / base),
                    }
                )

        if residuals:
            residual_df = pd.DataFrame(residuals)
            entity_weekday = residual_df.groupby("weekday")["ratio"].median()
            counts = residual_df.groupby("weekday")["ratio"].count()
            for wd, value in pooled_weekday.items():
                local = float(entity_weekday.get(wd, 1.0))
                n = int(counts.get(wd, 0))
                weight = n / (n + 5.0)
                entity_weekday.loc[wd] = weight * local + (1 - weight) * 1.0
        else:
            entity_weekday = pd.Series(1.0, index=range(7))

        values = []
        for date, base in global_forecast.items():
            wd_adjust = float(entity_weekday.get(date.weekday(), 1.0))
            values.append(level * float(base) * wd_adjust)

        entity_forecast = pd.DataFrame(
            {
                "entity_id": entity_id,
                "for_date": future_dates,
                "predicted_demand_index": np.clip(
                    np.asarray(values, dtype=float),
                    MIN_TARGET,
                    MAX_TARGET,
                ),
                "model": model_name,
            }
        )
        forecasts.append(entity_forecast)

        metadata.append(
            {
                "entity_id": entity_id,
                "entity_level": level,
                "weekday_residuals": {
                    str(k): float(v) for k, v in entity_weekday.items()
                },
                "global_regressors": regressors,
            }
        )

        if entity_number % 25 == 0 or entity_number == len(entity_ids):
            print(f"Processed {entity_number}/{len(entity_ids)} entities")

    result = pd.concat(forecasts, ignore_index=True)
    result = result.sort_values(["entity_id", "for_date"]).reset_index(drop=True)

    for adir in ARTIFACT_DIRS:
        adir.mkdir(parents=True, exist_ok=True)
        (adir / "pooled_timeseries_metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

    return result


def print_forecast_summary(forecast_df: pd.DataFrame) -> None:
    print("\n========== FORECAST SUMMARY ==========")
    print(f"Rows: {len(forecast_df):,}")
    print(f"Entities: {forecast_df['entity_id'].nunique():,}")
    print(
        f"Forecast range: {forecast_df['for_date'].min().date()} "
        f"-> {forecast_df['for_date'].max().date()}"
    )
    print("\nModel usage:")
    print(forecast_df["model"].value_counts().to_string())
    print("\nPredicted demand statistics:")
    print(forecast_df["predicted_demand_index"].describe())
    print("\n======================================\n")


if __name__ == "__main__":
    try:
        from features import build_features
    except ImportError:
        from ml.features import build_features

    features, future_features = build_features()
    forecasts = forecast_all_entities(
        features,
        future_features=future_features,
        forecast_days=FORECAST_DAYS,
        forecast_start=FORECAST_START,
        max_entities=10,
    )
    print_forecast_summary(forecasts)
    print(forecasts.head(20).to_string(index=False))
