import os
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from features import build_features
    from model import forecast_all_entities
except ImportError:
    from ml.features import build_features
    from ml.model import forecast_all_entities


TRAIN_END = pd.Timestamp("2026-08-10")
VALIDATION_START = pd.Timestamp("2026-08-11")
VALIDATION_END = pd.Timestamp("2026-08-17")

PRODUCTION_START = pd.Timestamp("2026-09-01")
PRODUCTION_DAYS = 30

ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIRS = [
    ROOT_DIR / "artifacts",
    Path(__file__).resolve().parent / "artifacts",
]


def split_train_validation(df: pd.DataFrame):
    df = df.copy()
    df["for_date"] = pd.to_datetime(df["for_date"])

    train_df = df[df["for_date"] <= TRAIN_END].copy()
    validation_df = df[
        (df["for_date"] >= VALIDATION_START)
        & (df["for_date"] <= VALIDATION_END)
    ].copy()

    if train_df.empty:
        raise ValueError("Training dataset is empty.")
    if validation_df.empty:
        raise ValueError("Validation dataset is empty.")

    return train_df, validation_df


def calculate_mae(actual, predicted):
    return np.mean(np.abs(actual - predicted))


def calculate_rmse(actual, predicted):
    return np.sqrt(np.mean((actual - predicted) ** 2))


def calculate_mape(actual, predicted):
    mask = actual != 0
    if mask.sum() == 0:
        return np.nan
    return np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100


def calculate_wape(actual, predicted):
    denom = np.sum(np.abs(actual))
    if denom == 0:
        return np.nan
    return np.sum(np.abs(actual - predicted)) / denom * 100


def calculate_smape(actual, predicted):
    denom = np.abs(actual) + np.abs(predicted)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(denom == 0, 0.0, np.abs(actual - predicted) / denom * 2)
    return np.mean(ratio) * 100


def calculate_metrics(actual_df, forecast_df):
    actual = actual_df[["entity_id", "for_date", "demand_index"]].copy()
    predicted = forecast_df[["entity_id", "for_date", "predicted_demand_index"]].copy()

    actual["for_date"] = pd.to_datetime(actual["for_date"])
    predicted["for_date"] = pd.to_datetime(predicted["for_date"])

    merged = actual.merge(predicted, on=["entity_id", "for_date"], how="inner")
    if merged.empty:
        raise ValueError("No overlapping validation rows.")

    a = merged["demand_index"].to_numpy()
    p = merged["predicted_demand_index"].to_numpy()

    metrics = {
        "MAE": float(calculate_mae(a, p)),
        "RMSE": float(calculate_rmse(a, p)),
        "MAPE": float(calculate_mape(a, p)),
        "WAPE": float(calculate_wape(a, p)),
        "sMAPE": float(calculate_smape(a, p)),
    }
    return metrics, merged


def evaluate_model(train_df, validation_df, validation_future_features):
    print("\n========== VALIDATION ==========")
    print(
        f"Training range: {train_df['for_date'].min().date()} "
        f"-> {train_df['for_date'].max().date()}"
    )
    print(
        f"Validation range: {validation_df['for_date'].min().date()} "
        f"-> {validation_df['for_date'].max().date()}"
    )
    print(f"Training entities: {train_df['entity_id'].nunique()}")
    print(f"Validation entities: {validation_df['entity_id'].nunique()}")

    validation_dates = sorted(validation_df["for_date"].drop_duplicates().tolist())
    validation_forecasts = forecast_all_entities(
        train_df,
        future_features=validation_future_features,
        forecast_days=len(validation_dates),
        forecast_start=VALIDATION_START,
    )

    validation_forecasts = validation_forecasts[
        (validation_forecasts["for_date"] >= VALIDATION_START)
        & (validation_forecasts["for_date"] <= VALIDATION_END)
    ].copy()

    metrics, comparison = calculate_metrics(validation_df, validation_forecasts)

    print("\nValidation metrics:")
    print(f"MAE:   {metrics['MAE']:.6f}")
    print(f"RMSE:  {metrics['RMSE']:.6f}")
    print(f"MAPE:  {metrics['MAPE']:.2f}%  (rubric metric)")
    print(f"WAPE:  {metrics['WAPE']:.2f}%")
    print(f"sMAPE: {metrics['sMAPE']:.2f}%")
    print(f"\nCompared rows: {len(comparison):,}")
    print("\n================================\n")
    return metrics, comparison


def train_final_model(features_df, production_future_features):
    print("\n========== FINAL FORECAST ==========")
    production_history = features_df[features_df["for_date"] <= VALIDATION_END].copy()

    print(
        f"Final training range: {production_history['for_date'].min().date()} "
        f"-> {production_history['for_date'].max().date()}"
    )

    forecasts = forecast_all_entities(
        production_history,
        future_features=production_future_features,
        forecast_days=PRODUCTION_DAYS,
        forecast_start=PRODUCTION_START,
    )

    forecasts = forecasts[
        (forecasts["for_date"] >= PRODUCTION_START)
        & (
            forecasts["for_date"]
            < PRODUCTION_START + pd.Timedelta(days=PRODUCTION_DAYS)
        )
    ].copy()

    print(
        f"Production forecast range: {forecasts['for_date'].min().date()} "
        f"-> {forecasts['for_date'].max().date()}"
    )
    print(f"Forecast rows: {len(forecasts):,}")
    print(f"Forecast entities: {forecasts['entity_id'].nunique():,}")
    print("\nModel usage:")
    print(forecasts["model"].value_counts().to_string())
    print("\n====================================\n")
    return forecasts


def main():
    print("Loading feature dataset...")
    features, production_future_features = build_features()

    print(f"\nTotal rows: {len(features):,}")
    print(f"Total entities: {features['entity_id'].nunique():,}")

    train_df, validation_df = split_train_validation(features)

    _, validation_future_features = build_features(
        forecast_as_of=TRAIN_END,
        forecast_start=VALIDATION_START,
        forecast_days=(VALIDATION_END - VALIDATION_START).days + 1,
    )

    metrics, comparison = evaluate_model(train_df, validation_df, validation_future_features)

    forecasts = train_final_model(features, production_future_features)

    for adir in ARTIFACT_DIRS:
        adir.mkdir(parents=True, exist_ok=True)
        forecasts.to_csv(adir / "demand_forecast.csv", index=False)
        (adir / "model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Production forecast saved to: {[str(d / 'demand_forecast.csv') for d in ARTIFACT_DIRS]}")

    print("\nFirst forecast rows:")
    print(forecasts.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
