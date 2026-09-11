from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TRAINING_CSV = DATA_DIR / "training_ready.csv"
MODEL_FILE = DATA_DIR / "ml_model.pkl"
FEATURE_FILE = DATA_DIR / "ml_model_features.json"
SUMMARY_FILE = DATA_DIR / "ml_model_summary.json"


TARGET_COLUMN = "total_fare"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["route"] = frame["origin"] + "-" + frame["destination"]
    frame["departure_date"] = pd.to_datetime(frame["departure_date"], errors="coerce")
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], errors="coerce")
    frame["day_of_week"] = frame["departure_date"].dt.dayofweek
    frame["day_of_month"] = frame["departure_date"].dt.day
    frame["month"] = frame["departure_date"].dt.month
    frame["week_of_year"] = frame["departure_date"].dt.isocalendar().week.astype(int)

    time_strings = frame["departure_time"].fillna("00:00").astype(str)
    frame["departure_hour"] = pd.to_numeric(time_strings.str.slice(0, 2), errors="coerce").fillna(0)
    frame["departure_minute"] = pd.to_numeric(time_strings.str.slice(3, 5), errors="coerce").fillna(0)
    frame["is_weekend"] = frame["day_of_week"].isin([5, 6]).astype(int)

    numeric_fill = {
        "duration_minutes": frame["duration_minutes"].median(),
        "stops": frame["stops"].median(),
        "base_fare": frame["base_fare"].median(),
        "taxes": frame["taxes"].median(),
        "convenience_fee": frame["convenience_fee"].median(),
    }
    for column, value in numeric_fill.items():
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(value)

    for column in ["availability", "fare_class", "source_type", "source", "airline", "airline_code"]:
        frame[column] = frame[column].fillna("unknown")

    frame["base_plus_taxes"] = frame["base_fare"].fillna(0) + frame["taxes"].fillna(0)
    frame["fare_gap"] = frame[TARGET_COLUMN] - frame["base_plus_taxes"]

    return frame


def compute_baseline(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.Series:
    route_horizon_medians = (
        train_df.groupby(["route", "advance_days"])[TARGET_COLUMN]
        .median()
        .rename("route_horizon_baseline")
    )
    test_index = pd.MultiIndex.from_frame(test_df[["route", "advance_days"]])
    baseline_series = test_index.map(route_horizon_medians)
    baseline_series = baseline_series.fillna(train_df[TARGET_COLUMN].median())
    return baseline_series


def build_model_summary(model, metrics: dict, train_rows: int, test_rows: int, feature_columns: list[str]) -> dict:
    return {
        "model_name": model.__class__.__name__,
        "train_rows": train_rows,
        "test_rows": test_rows,
        "metrics": metrics,
        "feature_columns": feature_columns,
    }


def main() -> None:
    if not TRAINING_CSV.exists():
        raise FileNotFoundError(f"Missing training CSV: {TRAINING_CSV}")

    df = pd.read_csv(TRAINING_CSV)
    df = build_features(df)

    df = df.sort_values("observed_at").reset_index(drop=True)
    split_index = max(1, int(len(df) * 0.8))
    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    feature_columns = [
        "route",
        "origin",
        "destination",
        "advance_days",
        "source",
        "source_type",
        "airline",
        "airline_code",
        "fare_class",
        "availability",
        "day_of_week",
        "day_of_month",
        "month",
        "week_of_year",
        "departure_hour",
        "departure_minute",
        "is_weekend",
        "duration_minutes",
        "stops",
        "base_fare",
        "taxes",
        "convenience_fee",
        "base_plus_taxes",
        "fare_gap",
    ]

    categorical_columns = [
        "route",
        "origin",
        "destination",
        "source",
        "source_type",
        "airline",
        "airline_code",
        "fare_class",
        "availability",
    ]

    train_dummies = pd.get_dummies(train_df[feature_columns], columns=categorical_columns, drop_first=False)
    test_dummies = pd.get_dummies(test_df[feature_columns], columns=categorical_columns, drop_first=False)

    feature_columns_all = sorted(set(train_dummies.columns) | set(test_dummies.columns))
    train_matrix = train_dummies.reindex(columns=feature_columns_all, fill_value=0)
    test_matrix = test_dummies.reindex(columns=feature_columns_all, fill_value=0)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=18,
        min_samples_leaf=2,
        random_state=42,
    )
    model.fit(train_matrix, train_df[TARGET_COLUMN])

    y_test = test_df[TARGET_COLUMN].astype(float).to_numpy()
    predictions = model.predict(test_matrix)

    baseline_predictions = compute_baseline(train_df, test_df).to_numpy()

    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    baseline_mae = mean_absolute_error(y_test, baseline_predictions)
    baseline_rmse = np.sqrt(mean_squared_error(y_test, baseline_predictions))

    mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100
    baseline_mape = np.mean(np.abs((y_test - baseline_predictions) / y_test)) * 100

    metrics = {
        "mae": float(mae),
        "rmse": float(rmse),
        "mape": float(mape),
        "baseline_mae": float(baseline_mae),
        "baseline_rmse": float(baseline_rmse),
        "baseline_mape": float(baseline_mape),
        "improvement_vs_baseline_mae_percent": float(((baseline_mae - mae) / baseline_mae) * 100 if baseline_mae else 0.0),
    }

    summary = build_model_summary(model, metrics, len(train_df), len(test_df), feature_columns_all)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with MODEL_FILE.open("wb") as handle:
        pickle.dump(model, handle)
    FEATURE_FILE.write_text(json.dumps(feature_columns_all, indent=2), encoding="utf-8")
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps({
        "model_file": str(MODEL_FILE),
        "feature_file": str(FEATURE_FILE),
        "summary_file": str(SUMMARY_FILE),
        "metrics": metrics,
    }, indent=2))


if __name__ == "__main__":
    main()
