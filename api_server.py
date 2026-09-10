import csv
import json
import pickle
import sqlite3
from io import StringIO

import pandas as pd
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import median
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "airfare_intelligence.db"
DGCA_ROUTE_WEIGHT_FILE = ROOT / "data" / "dgca_route_weights.csv"
GOV_ROUTE_WEIGHT_FILE = ROOT / "data" / "gov" / "route_basket_fixed8_2025-01_to_2026-05 (2).csv"
MOSPI_CPI_FILE = ROOT / "data" / "gov" / "mospi_cpi_airfare.csv"
MODEL_FILE = ROOT / "data" / "ml_model.pkl"
MODEL_FEATURES_FILE = ROOT / "data" / "ml_model_features.json"
HOST = "127.0.0.1"
PORT = 8000
ROUTES = {
    ("DEL", "BOM"), ("DEL", "BLR"), ("DEL", "CCU"),
    ("DEL", "HYD"), ("DEL", "GOI"), ("DEL", "PAT"),
    ("BOM", "BLR"), ("MAA", "DEL"),
}
HORIZONS = (1, 7, 15, 30, 45)
KNOWN_AIRLINES = ("IndiGo", "Air India", "Air India Express", "Akasa Air", "SpiceJet")
KNOWN_SOURCES = ("cleartrip", "easemytrip", "yatra")
WEIGHT_STATUS = "Traffic-based route weights from DGCA route basket"


def load_route_weights():
    weights = {route: 1.0 for route in ROUTES}

    weight_files = [DGCA_ROUTE_WEIGHT_FILE, GOV_ROUTE_WEIGHT_FILE]
    for candidate in weight_files:
        if not candidate.exists():
            continue

        with candidate.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                route_value = (row.get("route") or row.get("Corridor") or "").strip().upper()
                weight_value = (row.get("weight") or row.get("Weight") or "").strip()

                if route_value and weight_value:
                    try:
                        normalized_weight = float(weight_value)
                    except ValueError:
                        continue

                    if "-" in route_value:
                        route_parts = route_value.split("-")
                        if len(route_parts) != 2:
                            continue
                        route = (route_parts[0].strip().upper(), route_parts[1].strip().upper())
                        if route in ROUTES:
                            weights[route] = normalized_weight
                        continue

                origin = (row.get("IATA_A") or "").strip().upper()
                destination = (row.get("IATA_B") or "").strip().upper()
                if not origin or not destination:
                    continue
                route = (origin, destination)
                if route not in ROUTES:
                    continue
                try:
                    weights[route] = float(weight_value)
                except ValueError:
                    continue

    return weights


ROUTE_WEIGHTS = load_route_weights()


def load_mospi_cpi_reference():
    if not MOSPI_CPI_FILE.exists():
        return []

    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
        "june": 6, "july": 7, "august": 8, "september": 9,
        "october": 10, "november": 11, "december": 12,
    }

    rows = []
    with MOSPI_CPI_FILE.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            year = (row.get("Year") or "").strip()
            month_name = (row.get("Month") or "").strip()
            cpi_value = (row.get("CPI_Airfare_Index") or "").strip()
            if not year or not month_name or not cpi_value or cpi_value == "-":
                continue
            month_number = month_map.get(month_name.lower())
            if month_number is None:
                try:
                    month_number = int(month_name)
                except ValueError:
                    continue
            rows.append({
                "month": f"{year}-{month_number:02d}",
                "cpi_value": float(cpi_value),
            })

    rows.sort(key=lambda item: item["month"])
    return rows


def as_number(value):
    return float(value) if value is not None else None


MODEL_RAW_COLUMNS = [
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
MODEL_CATEGORICAL_COLUMNS = [
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


def load_ml_model():
    if not MODEL_FILE.exists() or not MODEL_FEATURES_FILE.exists():
        return None, None

    try:
        with MODEL_FILE.open("rb") as handle:
            model = pickle.load(handle)
        with MODEL_FEATURES_FILE.open("r", encoding="utf-8") as handle:
            feature_columns = json.load(handle)
        return model, feature_columns
    except Exception:
        return None, None


def build_model_feature_row(row):
    departure_date = row.get("departure_date") or row.get("observed_at", "")[:10]
    departure_time = row.get("departure_time") or "00:00"

    def parse_time_component(value, index):
        try:
            return int(str(value).split(":")[index].strip())
        except Exception:
            return 0

    try:
        departure_dt = datetime.strptime(departure_date, "%Y-%m-%d")
        departure_date_obj = departure_dt
    except Exception:
        departure_date_obj = datetime.now()

    base_fare = float(row.get("base_fare") or 0)
    taxes = float(row.get("taxes") or 0)
    convenience_fee = float(row.get("convenience_fee") or 0)
    total_fare = float(row.get("total_fare") or 0)

    return {
        "route": f"{row.get('origin')}-{row.get('destination')}",
        "origin": row.get("origin"),
        "destination": row.get("destination"),
        "advance_days": int(row.get("advance_days") or 0),
        "source": row.get("source") or "unknown",
        "source_type": row.get("source_type") or "unknown",
        "airline": row.get("airline") or "unknown",
        "airline_code": row.get("airline_code") or "unknown",
        "fare_class": row.get("fare_class") or "ECONOMY",
        "availability": row.get("availability") or "unknown",
        "day_of_week": int(departure_date_obj.weekday()),
        "day_of_month": int(departure_date_obj.day),
        "month": int(departure_date_obj.month),
        "week_of_year": int(departure_date_obj.isocalendar()[1]),
        "departure_hour": parse_time_component(departure_time, 0),
        "departure_minute": parse_time_component(departure_time, 1),
        "is_weekend": int(departure_date_obj.weekday() >= 5),
        "duration_minutes": int(row.get("duration_minutes") or 0),
        "stops": int(row.get("stops") or 0),
        "base_fare": base_fare,
        "taxes": taxes,
        "convenience_fee": convenience_fee,
        "base_plus_taxes": base_fare + taxes,
        "fare_gap": total_fare - (base_fare + taxes),
    }


def run_model_forecast(advance_days):
    model, feature_columns = load_ml_model()
    if model is None or not feature_columns:
        return None

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT *
            FROM raw_fare_quotes
            WHERE advance_days = ?
              AND total_fare IS NOT NULL AND total_fare > 0
            ORDER BY observed_at DESC, id DESC
            """,
            (advance_days,),
        ).fetchall()

    latest_by_route = {}
    for row in rows:
        route = (row["origin"], row["destination"])
        if route not in latest_by_route:
            latest_by_route[route] = dict(row)

    records = []
    for route in sorted(ROUTES):
        latest_row = latest_by_route.get(route)
        if not latest_row:
            continue

        record = build_model_feature_row(latest_row)
        records.append(record)

    if not records:
        return None

    frame = pd.DataFrame(records)
    frame[MODEL_CATEGORICAL_COLUMNS] = frame[MODEL_CATEGORICAL_COLUMNS].fillna("unknown")
    for column in ["advance_days", "day_of_week", "day_of_month", "month", "week_of_year", "departure_hour", "departure_minute", "is_weekend", "duration_minutes", "stops", "base_fare", "taxes", "convenience_fee", "base_plus_taxes", "fare_gap"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

    encoded = pd.get_dummies(frame[MODEL_RAW_COLUMNS], columns=MODEL_CATEGORICAL_COLUMNS, drop_first=False)
    encoded = encoded.reindex(columns=feature_columns, fill_value=0)

    preds = model.predict(encoded)
    predictions = []
    for route, prediction in zip(sorted(ROUTES), preds):
        predictions.append({
            "route": f"{route[0]}-{route[1]}",
            "forecast_value": float(prediction),
            "model": model.__class__.__name__,
            "prediction_source": "model",
        })

    return predictions


def percentile(values, percent):
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percent
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    if lower_index == upper_index:
        return lower_value
    fraction = position - lower_index
    return lower_value + (upper_value - lower_value) * fraction


def build_cleaning_summary(rows):
    duplicate_key_fields = (
        "source", "origin", "destination", "departure_date", "advance_days",
        "airline", "flight_number", "departure_time", "arrival_time",
        "total_fare", "observed_at", "availability", "scrape_status",
        "base_fare", "taxes"
    )

    unique_keys = {}
    duplicate_rows = 0

    for row in rows:
        key = tuple((row.get(field) if row.get(field) is not None else "__NULL__") for field in duplicate_key_fields)
        unique_keys[key] = unique_keys.get(key, 0) + 1

    duplicate_rows = sum(count - 1 for count in unique_keys.values() if count > 1)

    invalid_quotes = 0
    route_fares = {}

    for row in rows:
        total_fare = row.get("total_fare")
        if total_fare is None:
            invalid_quotes += 1
            continue
        try:
            fare_value = float(total_fare)
        except (TypeError, ValueError):
            invalid_quotes += 1
            continue

        if fare_value <= 0:
            invalid_quotes += 1
            continue

        route_key = (row.get("origin"), row.get("destination"))
        route_fares.setdefault(route_key, []).append(fare_value)

    outlier_rows = 0
    route_groups_with_outliers = 0

    for route_key, fares in route_fares.items():
        values = sorted(fares)
        if len(values) < 4:
            continue

        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        group_outliers = sum(1 for fare in values if fare < lower_bound or fare > upper_bound)
        if group_outliers:
            route_groups_with_outliers += 1
            outlier_rows += group_outliers

    return {
        "duplicate_rows": duplicate_rows,
        "invalid_quotes": invalid_quotes,
        "outlier_rows": outlier_rows,
        "route_groups_with_outliers": route_groups_with_outliers,
    }


def route_payload(origin, destination, advance_days, departure_date=None):
    if (origin, destination) not in ROUTES:
        return {"error": "Unsupported route"}, 400
    if advance_days not in HORIZONS:
        return {"error": "Unsupported advance horizon"}, 400
    normalized_date = departure_date.replace("-", "") if departure_date else None

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        latest_observed = connection.execute(
            "SELECT MAX(substr(observed_at, 1, 10)) FROM raw_fare_quotes"
        ).fetchone()[0]
        rows = connection.execute(
            """
            SELECT source, airline, flight_number, departure_date,
                   departure_time, arrival_time, total_fare, currency,
                   availability, scrape_status, observed_at
            FROM raw_fare_quotes
                        WHERE origin = ? AND destination = ? AND advance_days = ?
                            AND (? IS NULL OR replace(departure_date, '-', '') = ?)
              AND total_fare IS NOT NULL AND total_fare > 0
            ORDER BY source, airline, total_fare
            """,
            (origin, destination, advance_days, normalized_date, normalized_date),
        ).fetchall()

    values = [float(row["total_fare"]) for row in rows]
    by_source = {}
    by_airline = {}
    by_observation_day = {}
    by_group_day = {}
    by_flight_group = {}
    for row in rows:
        source = row["source"] or "unknown"
        airline = row["airline"] or "unknown"
        fare = float(row["total_fare"])
        by_source.setdefault(source, []).append(fare)
        by_airline.setdefault(airline, []).append(fare)
        observed_day = (row["observed_at"] or "")[:10]
        by_observation_day.setdefault(observed_day, []).append(fare)
        by_group_day.setdefault(("ota", source, observed_day), []).append(fare)
        by_group_day.setdefault(("airline", airline, observed_day), []).append(fare)
        departure_time = row["departure_time"] or "Unknown"
        by_flight_group.setdefault(("airline", airline, departure_time), []).append(fare)
        by_flight_group.setdefault(("ota", source, departure_time), []).append(fare)

    def summarize(groups):
        return {
            name: {
                "median_fare": median(fares),
                "minimum_fare": min(fares),
                "maximum_fare": max(fares),
                "quote_count": len(fares),
            }
            for name, fares in sorted(groups.items()) if fares
        }

    normalized_airlines = {name: by_airline.get(name, []) for name in KNOWN_AIRLINES}
    normalized_sources = {name: by_source.get(name, []) for name in KNOWN_SOURCES}

    flight_series = {}
    for kind, names in (("airline", KNOWN_AIRLINES), ("ota", KNOWN_SOURCES)):
        flight_series[kind] = [
            {
                "name": name,
                "points": [
                    {"label": departure_time, "median_fare": median(fares)}
                    for (group_kind, group_name, departure_time), fares in sorted(by_flight_group.items())
                    if group_kind == kind and group_name == name
                ],
            }
            for name in names
        ]

    expected_departure_date = None
    if latest_observed:
        expected_departure_date = (
            datetime.strptime(latest_observed, "%Y-%m-%d")
            + timedelta(days=advance_days)
        ).strftime("%Y-%m-%d")

    return {
        "route": f"{origin}-{destination}",
        "origin": origin,
        "destination": destination,
        "advance_days": advance_days,
        "departure_date": departure_date,
        "latest_observation_date": latest_observed,
        "expected_departure_date": expected_departure_date,
        "cabin": "Economy",
        "route_weight": ROUTE_WEIGHTS.get((origin, destination), 1.0),
        "weight_status": WEIGHT_STATUS,
        "quote_count": len(rows),
        "median_fare": median(values) if values else None,
        "minimum_fare": min(values) if values else None,
        "maximum_fare": max(values) if values else None,
        "sources": summarize(normalized_sources),
        "airlines": summarize(normalized_airlines),
        "trend": [
            {"observed_day": day, "median_fare": median(fares), "quote_count": len(fares)}
            for day, fares in sorted(by_observation_day.items()) if day
        ],
        "series": {
            group_type: [
                {
                    "name": name,
                    "points": [
                        {"observed_day": day, "median_fare": median(fares)}
                        for (kind, group_name, day), fares in sorted(by_group_day.items())
                        if kind == group_type and group_name == name
                    ],
                }
                for name in (KNOWN_AIRLINES if group_type == "airline" else KNOWN_SOURCES)
            ]
            for group_type in ("airline", "ota")
        },
        "flight_series": flight_series,
        "quotes": [dict(row) for row in rows],
    }, 200


def route_horizons_payload(origin, destination):
    if (origin, destination) not in ROUTES:
        return {"error": "Unsupported route"}, 400

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT source, airline, advance_days, total_fare
            FROM raw_fare_quotes
            WHERE origin = ? AND destination = ?
              AND advance_days IN (1, 7, 15, 30, 45)
              AND total_fare IS NOT NULL AND total_fare > 0
            ORDER BY advance_days
            """,
            (origin, destination),
        ).fetchall()

    grouped = {}
    for row in rows:
        fare = float(row["total_fare"])
        horizon = row["advance_days"]
        grouped.setdefault(("airline", row["airline"] or "unknown", horizon), []).append(fare)
        grouped.setdefault(("ota", row["source"] or "unknown", horizon), []).append(fare)

    def series_for(kind, names):
        return [
            {
                "name": name,
                "points": [
                    {"observed_day": f"T+{days}", "median_fare": median(grouped[(kind, name, days)])}
                    for days in HORIZONS
                    if (kind, name, days) in grouped
                ],
            }
            for name in names
        ]

    return {
        "route": f"{origin}-{destination}",
        "origin": origin,
        "destination": destination,
        "cabin": "Economy",
        "view": "lead_time",
        "series": {
            "airline": series_for("airline", KNOWN_AIRLINES),
            "ota": series_for("ota", KNOWN_SOURCES),
        },
        "sources": {},
        "airlines": {},
        "quotes": [],
        "quote_count": len(rows),
        "horizons_with_data": sorted({row["advance_days"] for row in rows}),
    }, 200


def market_overview_payload():
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT origin, destination, advance_days, total_fare
            FROM raw_fare_quotes
            WHERE total_fare IS NOT NULL AND total_fare > 0
              AND advance_days IN (1, 7, 15, 30, 45)
            """
        ).fetchall()

    grouped = {}
    for origin, destination, advance_days, fare in rows:
        grouped.setdefault((origin, destination, advance_days), []).append(float(fare))

    route_rows = []
    for origin, destination in sorted(ROUTES):
        horizons = {}
        all_fares = []
        for advance_days in HORIZONS:
            fares = grouped.get((origin, destination, advance_days), [])
            if fares:
                horizons[str(advance_days)] = median(fares)
                all_fares.extend(fares)
        if all_fares:
            route_rows.append({
                "route": f"{origin}-{destination}",
                "horizons": horizons,
                "median_fare": median(all_fares),
                "quote_count": len(all_fares),
            })

    cheapest = min(route_rows, key=lambda row: row["median_fare"]) if route_rows else None
    highest = max(route_rows, key=lambda row: row["median_fare"]) if route_rows else None
    route_weights = [
        {
            "route": f"{origin}-{destination}",
            "weight": ROUTE_WEIGHTS.get((origin, destination), 1.0),
            "weight_percent": ROUTE_WEIGHTS.get((origin, destination), 1.0) * 100,
        }
        for origin, destination in sorted(ROUTES)
    ]

    return {
        "routes": route_rows,
        "route_count": len(route_rows),
        "quote_count": len(rows),
        "horizons": list(HORIZONS),
        "cheapest_route": cheapest,
        "highest_route": highest,
        "weight_status": WEIGHT_STATUS,
        "route_weights": route_weights,
        "basket_reference_period": "2025-01 to 2026-05",
    }, 200


def source_health_payload():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        source_rows = connection.execute(
            """
            SELECT source, COUNT(*) AS quote_count,
                   COUNT(DISTINCT origin || '-' || destination) AS route_count,
                   COUNT(DISTINCT advance_days) AS horizon_count,
                   MAX(observed_at) AS latest_observed,
                   SUM(CASE WHEN total_fare IS NULL OR total_fare <= 0 THEN 1 ELSE 0 END) AS invalid_quotes,
                   SUM(CASE WHEN base_fare IS NULL THEN 1 ELSE 0 END) AS missing_base_fare,
                   SUM(CASE WHEN taxes IS NULL THEN 1 ELSE 0 END) AS missing_taxes
            FROM raw_fare_quotes
            GROUP BY source ORDER BY source
            """
        ).fetchall()
        total = connection.execute("SELECT COUNT(*) FROM raw_fare_quotes").fetchone()[0]
        latest = connection.execute("SELECT MAX(observed_at) FROM raw_fare_quotes").fetchone()[0]
        coverage = connection.execute(
            """
            SELECT origin || '-' || destination AS route, advance_days, COUNT(*) AS quote_count
            FROM raw_fare_quotes GROUP BY route, advance_days ORDER BY route, advance_days
            """
        ).fetchall()
        rows = connection.execute(
            """
            SELECT *
            FROM raw_fare_quotes
            ORDER BY observed_at, source, origin, destination, advance_days
            """
        ).fetchall()

    cleaning_summary = build_cleaning_summary([dict(row) for row in rows])

    return {
        "database": str(DB_PATH),
        "total_quotes": total,
        "latest_observed": latest,
        "sources": [dict(row) for row in source_rows],
        "coverage": [dict(row) for row in coverage],
        "cleaning_summary": cleaning_summary,
    }, 200


def baseline_forecast_payload(advance_days):
    if advance_days not in HORIZONS:
        return {"error": "Unsupported advance horizon"}, 400

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT origin, destination, advance_days, substr(observed_at, 1, 10) AS observed_day, total_fare
            FROM raw_fare_quotes
            WHERE advance_days = ? AND total_fare IS NOT NULL AND total_fare > 0
            ORDER BY observed_day DESC, origin, destination
            """,
            (advance_days,),
        ).fetchall()

    grouped_by_route = {}
    for row in rows:
        route_key = (row["origin"], row["destination"])
        grouped_by_route.setdefault(route_key, {})
        grouped_by_route[route_key].setdefault(row["observed_day"], []).append(float(row["total_fare"]))

    forecast_rows = []
    for route in sorted(ROUTES):
        route_data = grouped_by_route.get(route)
        if not route_data:
            continue
        latest_day = max(route_data)
        fares = route_data[latest_day]
        forecast_rows.append({
            "route": f"{route[0]}-{route[1]}",
            "advance_days": advance_days,
            "latest_observed_day": latest_day,
            "forecast_value": median(fares),
            "quote_count": len(fares),
            "model": "Recent median baseline",
            "prediction_source": "baseline",
        })

    forecast_rows.sort(key=lambda item: item["route"])

    return {
        "advance_days": advance_days,
        "weight_status": WEIGHT_STATUS,
        "model": "Recent median baseline",
        "model_available": False,
        "generated_at": max((row["observed_day"] for row in rows), default=None),
        "routes": forecast_rows,
    }, 200


def model_forecast_payload(advance_days):
    payload, status = baseline_forecast_payload(advance_days)
    if status != 200:
        return payload, status

    predictions = run_model_forecast(advance_days)
    if predictions is None:
        payload["model_available"] = False
        payload["model"] = "Recent median baseline"
        return payload, 200

    prediction_lookup = {row["route"]: row for row in predictions}
    payload["model_available"] = True
    payload["model"] = "Trained fare model"

    for row in payload["routes"]:
        model_row = prediction_lookup.get(row["route"])
        if model_row:
            row["forecast_value"] = model_row["forecast_value"]
            row["model"] = model_row["model"]
            row["prediction_source"] = model_row["prediction_source"]
        else:
            row["model"] = "Recent median baseline"
            row["prediction_source"] = "baseline"

    return payload, 200


def index_payload(advance_days):
    if advance_days not in HORIZONS:
        return {"error": "Unsupported advance horizon"}, 400

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT origin, destination, substr(observed_at, 1, 10) AS observed_day,
                   total_fare
            FROM raw_fare_quotes
            WHERE advance_days = ? AND total_fare IS NOT NULL AND total_fare > 0
            ORDER BY observed_day
            """,
            (advance_days,),
        ).fetchall()

    by_day_route = {}
    for origin, destination, observed_day, fare in rows:
        by_day_route.setdefault((observed_day, origin, destination), []).append(float(fare))
    days = sorted({key[0] for key in by_day_route})
    if not days:
        return {
            "error": "No valid fare observations are available",
            "status": "no_data",
            "index_value": None,
            "route_count": 0,
            "required_observation_periods": 1,
            "available_observation_periods": 0,
        }, 422

    # The first successful live collection is the official base period.
    # Therefore the first live index is 100.00 rather than being shown as NaN
    # or blocked behind a second run. Subsequent runs compare against this
    # same base-day route median.
    base_day, current_day = days[0], days[-1]
    route_values = []
    for route, weight in ROUTE_WEIGHTS.items():
        origin, destination = route
        base_values = by_day_route.get((base_day, origin, destination), [])
        current_values = by_day_route.get((current_day, origin, destination), [])
        if not base_values or not current_values:
            continue
        base_fare = median(base_values)
        current_fare = median(current_values)
        route_values.append({
            "route": f"{origin}-{destination}",
            "weight": weight,
            "base_fare": base_fare,
            "current_fare": current_fare,
            "price_relative": current_fare / base_fare,
            "base_quote_count": len(base_values),
            "current_quote_count": len(current_values),
        })

    if not route_values:
        return {"error": "No complete route basket is available"}, 422
    weight_total = sum(item["weight"] for item in route_values)
    index_value = 100 * sum(
        item["weight"] * item["price_relative"] for item in route_values
    ) / weight_total
    return {
        "index_name": "UDAANKOSH Airfare Price Index",
        "method": "Laspeyres price index using route median fares",
        "weight_status": WEIGHT_STATUS,
        "base_period": base_day,
        "current_period": current_day,
        "advance_days": advance_days,
        "base_value": 100.0,
        "index_value": index_value,
        "status": "base_day" if base_day == current_day else "live",
        "available_observation_periods": len(days),
        "route_count": len(route_values),
        "routes": route_values,
    }, 200


def index_series_payload(advance_days):
    if advance_days not in HORIZONS:
        return {"error": "Unsupported advance horizon"}, 400

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT origin, destination, substr(observed_at, 1, 10) AS observed_day,
                   total_fare
            FROM raw_fare_quotes
            WHERE advance_days = ? AND total_fare IS NOT NULL AND total_fare > 0
            ORDER BY observed_day
            """,
            (advance_days,),
        ).fetchall()

    grouped = {}
    for origin, destination, observed_day, fare in rows:
        grouped.setdefault((observed_day, origin, destination), []).append(float(fare))
    days = sorted({day for day, _, _ in grouped})
    if not days:
        return {"error": "No index observations available"}, 422

    base_day = days[0]
    base_medians = {
        (origin, destination): median(fares)
        for (day, origin, destination), fares in grouped.items()
        if day == base_day
    }
    points = []
    for day in days:
        weighted_relatives = []
        for (observed_day, origin, destination), fares in grouped.items():
            if observed_day != day:
                continue
            base_fare = base_medians.get((origin, destination))
            if not base_fare:
                continue
            current_fare = median(fares)
            route_weight = ROUTE_WEIGHTS.get((origin, destination), 1.0)
            weighted_relatives.append((route_weight, current_fare / base_fare))

        if weighted_relatives:
            weight_total = sum(weight for weight, _ in weighted_relatives)
            weighted_average = sum(weight * relative for weight, relative in weighted_relatives) / weight_total
            points.append({"observed_day": day, "index_value": 100 * weighted_average})

    return {
        "advance_days": advance_days,
        "base_period": base_day,
        "method": "Laspeyres price index using route median fares",
        "weight_status": WEIGHT_STATUS,
        "points": points,
    }, 200


def metadata_payload():
    with sqlite3.connect(DB_PATH) as connection:
        latest_observed = connection.execute(
            "SELECT MAX(substr(observed_at, 1, 10)) FROM raw_fare_quotes"
        ).fetchone()[0]
    return {
        "latest_observation_date": latest_observed,
        "horizons": list(HORIZONS),
    }, 200


def build_csv_response(headers, rows):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(header, "") for header in headers])
    return buffer.getvalue()


def market_overview_csv_payload():
    payload, _ = market_overview_payload()
    headers = ["route", "T+1", "T+7", "T+15", "T+30", "T+45", "quotes"]
    rows = []
    for row in payload.get("routes", []):
        rows.append({
            "route": row.get("route", ""),
            "T+1": row.get("horizons", {}).get("1", ""),
            "T+7": row.get("horizons", {}).get("7", ""),
            "T+15": row.get("horizons", {}).get("15", ""),
            "T+30": row.get("horizons", {}).get("30", ""),
            "T+45": row.get("horizons", {}).get("45", ""),
            "quotes": row.get("quote_count", ""),
        })
    return build_csv_response(headers, rows), 200


def source_health_csv_payload():
    payload, _ = source_health_payload()
    headers = ["route", "horizon", "quote_count"]
    rows = []
    for item in payload.get("coverage", []):
        rows.append({
            "route": item.get("route", ""),
            "horizon": f"T+{item.get('advance_days', '')}",
            "quote_count": item.get("quote_count", ""),
        })
    return build_csv_response(headers, rows), 200


def baseline_forecast_csv_payload(advance_days):
    payload, status = baseline_forecast_payload(advance_days)
    if status != 200:
        return payload, status
    headers = ["route", "horizon", "latest_observed_day", "forecast_value", "quote_count", "model", "prediction_source"]
    rows = []
    for row in payload.get("routes", []):
        rows.append({
            "route": row.get("route", ""),
            "horizon": f"T+{row.get('advance_days', '')}",
            "latest_observed_day": row.get("latest_observed_day", ""),
            "forecast_value": row.get("forecast_value", ""),
            "quote_count": row.get("quote_count", ""),
            "model": row.get("model", ""),
            "prediction_source": row.get("prediction_source", ""),
        })
    return build_csv_response(headers, rows), 200


def model_forecast_csv_payload(advance_days):
    payload, status = model_forecast_payload(advance_days)
    if status != 200:
        return payload, status
    headers = ["route", "horizon", "latest_observed_day", "forecast_value", "quote_count", "model", "prediction_source"]
    rows = []
    for row in payload.get("routes", []):
        rows.append({
            "route": row.get("route", ""),
            "horizon": f"T+{row.get('advance_days', '')}",
            "latest_observed_day": row.get("latest_observed_day", ""),
            "forecast_value": row.get("forecast_value", ""),
            "quote_count": row.get("quote_count", ""),
            "model": row.get("model", ""),
            "prediction_source": row.get("prediction_source", ""),
        })
    return build_csv_response(headers, rows), 200


def all_flights_csv_payload(origin=None, destination=None, advance_days=None, departure_date=None):
    filters = []
    params = []

    if origin:
        filters.append("origin = ?")
        params.append(origin.upper())
    if destination:
        filters.append("destination = ?")
        params.append(destination.upper())
    if advance_days is not None:
        filters.append("advance_days = ?")
        params.append(int(advance_days))
    if departure_date:
        filters.append("replace(departure_date, '-', '') = ?")
        params.append(departure_date.replace('-', ''))

    query = """
        SELECT *
        FROM raw_fare_quotes
    """
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY observed_at, source, origin, destination, advance_days"

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

    headers = [
        "source", "origin", "destination", "departure_date", "advance_days",
        "airline", "flight_number", "departure_time", "arrival_time",
        "total_fare", "currency", "availability", "scrape_status",
        "observed_at", "base_fare", "taxes"
    ]
    return build_csv_response(headers, [dict(row) for row in rows]), 200


def cpi_comparison_payload(advance_days):
    if advance_days not in HORIZONS:
        return {"error": "Unsupported advance horizon"}, 400

    index_response = index_series_payload(advance_days)
    if index_response[1] != 200:
        return index_response

    all_series = index_response[0]
    api_points = all_series.get("points", [])

    def month_to_number(month_str):
        year, month = month_str.split("-")
        return int(year) * 12 + int(month)

    def number_to_month(number):
        year = (number - 1) // 12
        month = (number - 1) % 12 + 1
        return f"{year}-{month:02d}"

    api_monthly = {}
    for point in api_points:
        observed_day = (point.get("observed_day") or "")[:7]
        if not observed_day:
            continue
        api_monthly.setdefault(observed_day, []).append(float(point.get("index_value", 0)))

    api_series = []
    for month in sorted(api_monthly):
        values = api_monthly[month]
        api_series.append({
            "month": month,
            "api_value": sum(values) / len(values),
        })

    cpi_series = []
    for item in load_mospi_cpi_reference():
        cpi_series.append({
            "month": item["month"],
            "cpi_value": item["cpi_value"],
        })

    api_lookup = {month_to_number(item["month"]): item for item in api_series}
    cpi_lookup = {month_to_number(item["month"]): item for item in cpi_series}

    if api_series:
        base_api_value = api_series[0]["api_value"]
        for item in api_series:
            item["api_rebased"] = 100 * item["api_value"] / base_api_value

    if cpi_series:
        base_cpi_value = cpi_series[0]["cpi_value"]
        for item in cpi_series:
            item["cpi_rebased"] = 100 * item["cpi_value"] / base_cpi_value

    for item in api_series:
        current_num = month_to_number(item["month"])
        previous_num = current_num - 1
        previous_item = api_lookup.get(previous_num)
        if previous_item:
            item["api_inflation"] = 100 * (item["api_value"] - previous_item["api_value"]) / previous_item["api_value"]
        else:
            item["api_inflation"] = None
        previous_year_num = current_num - 12
        previous_year_item = api_lookup.get(previous_year_num)
        if previous_year_item:
            item["api_yoy"] = 100 * (item["api_value"] - previous_year_item["api_value"]) / previous_year_item["api_value"]
        else:
            item["api_yoy"] = None

    for item in cpi_series:
        current_num = month_to_number(item["month"])
        previous_num = current_num - 1
        previous_item = cpi_lookup.get(previous_num)
        if previous_item:
            item["cpi_inflation"] = 100 * (item["cpi_value"] - previous_item["cpi_value"]) / previous_item["cpi_value"]
        else:
            item["cpi_inflation"] = None
        previous_year_num = current_num - 12
        previous_year_item = cpi_lookup.get(previous_year_num)
        if previous_year_item:
            item["cpi_yoy"] = 100 * (item["cpi_value"] - previous_year_item["cpi_value"]) / previous_year_item["cpi_value"]
        else:
            item["cpi_yoy"] = None

    months = sorted(set(api_lookup) | set(cpi_lookup))
    table = []
    for month_number in months:
        month = number_to_month(month_number)
        api_item = api_lookup.get(month_number)
        cpi_item = cpi_lookup.get(month_number)
        table.append({
            "month": month,
            "api_index": api_item["api_rebased"] if api_item else None,
            "cpi_index": cpi_item["cpi_rebased"] if cpi_item else None,
            "api_inflation": api_item["api_inflation"] if api_item else None,
            "cpi_inflation": cpi_item["cpi_inflation"] if cpi_item else None,
            "api_yoy": api_item["api_yoy"] if api_item else None,
            "cpi_yoy": cpi_item["cpi_yoy"] if cpi_item else None,
        })

    return {
        "advance_days": advance_days,
        "weight_status": WEIGHT_STATUS,
        "comparison_label": "APIx vs MoSPI CPI proxy reference",
        "api_series": api_series,
        "cpi_series": cpi_series,
        "table": table,
        "notes": [
            "APIx values are computed from the live database using the traffic-weighted route basket.",
            "The MoSPI CPI series is a CSV reference file included in the workspace and should be treated as a proxy reference, not as an official airfare CPI series.",
            "Comparison accuracy depends on the overlap between observed APIx periods and the available CPI months.",
        ],
    }, 200


class ApiHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            try:
                with sqlite3.connect(DB_PATH) as connection:
                    total = connection.execute("SELECT COUNT(*) FROM raw_fare_quotes").fetchone()[0]
                    runs = connection.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
                    latest = connection.execute("SELECT MAX(substr(observed_at, 1, 10)) FROM raw_fare_quotes").fetchone()[0]
                    days = connection.execute("SELECT COUNT(DISTINCT substr(observed_at, 1, 10)) FROM raw_fare_quotes WHERE total_fare IS NOT NULL AND total_fare > 0").fetchone()[0]
                self.send_json({"status":"ok","database":"connected","db_path":str(DB_PATH),"total_quotes":total,"scrape_runs":runs,"observation_days":days,"latest_observed":latest}, 200)
            except Exception as exc:
                self.send_json({"status":"error","database":"error","error":str(exc)}, 500)
            return
        if parsed.path == "/api/route":
            query = parse_qs(parsed.query)
            try:
                origin = query.get("origin", [""])[0].upper()
                destination = query.get("destination", [""])[0].upper()
                advance_days = int(query.get("advance_days", [1])[0])
                departure_date = query.get("departure_date", [None])[0] or None
            except ValueError:
                self.send_json({"error": "Invalid route query"}, 400)
                return
            payload, status = route_payload(origin, destination, advance_days, departure_date)
            self.send_json(payload, status)
            return
        if parsed.path == "/api/route-horizons":
            query = parse_qs(parsed.query)
            payload, status = route_horizons_payload(
                query.get("origin", [""])[0].upper(),
                query.get("destination", [""])[0].upper(),
            )
            self.send_json(payload, status)
            return
        if parsed.path == "/api/market-overview":
            payload, status = market_overview_payload()
            self.send_json(payload, status)
            return
        if parsed.path == "/api/source-health":
            payload, status = source_health_payload()
            self.send_json(payload, status)
            return
        if parsed.path == "/api/export/all-flights.csv":
            query = parse_qs(parsed.query)
            payload, status = all_flights_csv_payload(
                query.get("origin", [None])[0],
                query.get("destination", [None])[0],
                query.get("advance_days", [None])[0],
                query.get("departure_date", [None])[0],
            )
            self.send_csv("all-flights.csv", payload if isinstance(payload, str) else json.dumps(payload))
            return
        if parsed.path == "/api/export/market-overview.csv":
            payload, status = market_overview_csv_payload()
            self.send_csv("market-overview.csv", payload if isinstance(payload, str) else json.dumps(payload))
            return
        if parsed.path == "/api/export/source-health.csv":
            payload, status = source_health_csv_payload()
            self.send_csv("source-health.csv", payload if isinstance(payload, str) else json.dumps(payload))
            return
        if parsed.path == "/api/model-forecast":
            query = parse_qs(parsed.query)
            try:
                advance_days = int(query.get("advance_days", [7])[0])
            except ValueError:
                self.send_json({"error": "Invalid advance horizon"}, 400)
                return
            payload, status = model_forecast_payload(advance_days)
            self.send_json(payload, status)
            return
        if parsed.path == "/api/baseline-forecast":
            query = parse_qs(parsed.query)
            try:
                advance_days = int(query.get("advance_days", [7])[0])
            except ValueError:
                self.send_json({"error": "Invalid advance horizon"}, 400)
                return
            payload, status = baseline_forecast_payload(advance_days)
            self.send_json(payload, status)
            return
        if parsed.path == "/api/export/model-forecast.csv":
            query = parse_qs(parsed.query)
            try:
                advance_days = int(query.get("advance_days", [7])[0])
            except ValueError:
                self.send_json({"error": "Invalid advance horizon"}, 400)
                return
            payload, status = model_forecast_csv_payload(advance_days)
            self.send_csv("model-forecast.csv", payload if isinstance(payload, str) else json.dumps(payload))
            return
        if parsed.path == "/api/export/baseline-forecast.csv":
            query = parse_qs(parsed.query)
            try:
                advance_days = int(query.get("advance_days", [7])[0])
            except ValueError:
                self.send_json({"error": "Invalid advance horizon"}, 400)
                return
            payload, status = baseline_forecast_csv_payload(advance_days)
            self.send_csv("baseline-forecast.csv", payload if isinstance(payload, str) else json.dumps(payload))
            return
        if parsed.path == "/api/index":
            query = parse_qs(parsed.query)
            try:
                advance_days = int(query.get("advance_days", [1])[0])
            except ValueError:
                self.send_json({"error": "Invalid advance horizon"}, 400)
                return
            payload, status = index_payload(advance_days)
            self.send_json(payload, status)
            return
        if parsed.path == "/api/index-series":
            query = parse_qs(parsed.query)
            try:
                advance_days = int(query.get("advance_days", [1])[0])
            except ValueError:
                self.send_json({"error": "Invalid advance horizon"}, 400)
                return
            payload, status = index_series_payload(advance_days)
            self.send_json(payload, status)
            return
        if parsed.path == "/api/meta":
            payload, status = metadata_payload()
            self.send_json(payload, status)
            return
        if parsed.path == "/api/cpi-comparison":
            query = parse_qs(parsed.query)
            try:
                advance_days = int(query.get("advance_days", [1])[0])
            except ValueError:
                self.send_json({"error": "Invalid advance horizon"}, 400)
                return
            payload, status = cpi_comparison_payload(advance_days)
            self.send_json(payload, status)
            return
        super().do_GET()

    def send_json(self, payload, status):
        body = json.dumps(payload, default=as_number).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_csv(self, filename, content):
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


if __name__ == "__main__":
    print(f"UDAANKOSH API: http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), ApiHandler).serve_forever()
