from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from math import ceil, floor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "airfare_intelligence.db"
OUTPUT_PATH = ROOT / "data" / "data_readiness_summary.json"
TRAINING_READY_CSV = ROOT / "data" / "training_ready.csv"
TRAINING_QUARANTINE_CSV = ROOT / "data" / "training_ready_quarantine.csv"
TRAINING_SUMMARY_PATH = ROOT / "data" / "training_ready_summary.json"

DUPLICATE_KEY_FIELDS = (
    "source",
    "origin",
    "destination",
    "departure_date",
    "advance_days",
    "airline",
    "flight_number",
    "departure_time",
    "arrival_time",
    "total_fare",
    "observed_at",
    "availability",
    "scrape_status",
    "base_fare",
    "taxes",
)


def percentile(values, pct):
    values = sorted(values)
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])

    idx = (len(values) - 1) * pct
    lo = floor(idx)
    hi = ceil(idx)
    if lo == hi:
        return float(values[lo])

    lower = values[lo]
    upper = values[hi]
    return float(lower + (upper - lower) * (idx - lo))


def query_all_rows(connection):
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(
        """
        SELECT id, run_id, observed_at, source, source_type, origin, destination,
               departure_date, advance_days, airline, airline_code,
               flight_number, departure_time, arrival_time,
               duration_minutes, stops, fare_class, base_fare, taxes,
               convenience_fee, total_fare, currency, availability,
               scrape_status, error_message, provider, source_record_id,
               scraped_at
        FROM raw_fare_quotes
        ORDER BY observed_at DESC, origin, destination, advance_days, id
        """
    )]


def compute_duplicate_rows(rows):
    counts = Counter()
    for row in rows:
        key = tuple((row.get(field) if row.get(field) is not None else "__NULL__") for field in DUPLICATE_KEY_FIELDS)
        counts[key] += 1
    return sum(count - 1 for count in counts.values() if count > 1)


def compute_invalid_rows(rows):
    invalid = 0
    missing_base_fare = 0
    missing_taxes = 0

    for row in rows:
        total_fare = row.get("total_fare")
        if total_fare is None:
            invalid += 1
            continue

        try:
            fare_value = float(total_fare)
        except (TypeError, ValueError):
            invalid += 1
            continue

        if fare_value <= 0:
            invalid += 1

        if row.get("base_fare") is None:
            missing_base_fare += 1
        if row.get("taxes") is None:
            missing_taxes += 1

    return invalid, missing_base_fare, missing_taxes


def compute_outliers(rows):
    grouped = defaultdict(list)
    for row in rows:
        total_fare = row.get("total_fare")
        if total_fare is None:
            continue
        try:
            fare_value = float(total_fare)
        except (TypeError, ValueError):
            continue
        if fare_value <= 0:
            continue
        route_key = (row.get("origin"), row.get("destination"))
        grouped[route_key].append(fare_value)

    outlier_rows = 0
    route_groups_with_outliers = 0

    for route_key, fares in grouped.items():
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
            outlier_rows += group_outliers
            route_groups_with_outliers += 1

    return {
        "outlier_rows": outlier_rows,
        "route_groups_with_outliers": route_groups_with_outliers,
    }


def build_summary():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        total_rows = connection.execute("SELECT COUNT(*) FROM raw_fare_quotes").fetchone()[0]
        latest_observed = connection.execute(
            "SELECT MAX(observed_at) FROM raw_fare_quotes"
        ).fetchone()[0]

        by_source = [
            {"source": row[0], "quote_count": row[1]}
            for row in connection.execute(
                "SELECT source, COUNT(*) FROM raw_fare_quotes GROUP BY source ORDER BY source"
            )
        ]

        by_route = [
            {"route": f"{row[0]}-{row[1]}", "quote_count": row[2]}
            for row in connection.execute(
                "SELECT origin, destination, COUNT(*) FROM raw_fare_quotes GROUP BY origin, destination ORDER BY origin, destination"
            )
        ]

        by_horizon = [
            {"advance_days": row[0], "quote_count": row[1]}
            for row in connection.execute(
                "SELECT advance_days, COUNT(*) FROM raw_fare_quotes GROUP BY advance_days ORDER BY advance_days"
            )
        ]

        coverage = [
            {"route": f"{row[0]}-{row[1]}", "advance_days": row[2], "quote_count": row[3]}
            for row in connection.execute(
                """
                SELECT origin, destination, advance_days, COUNT(*)
                FROM raw_fare_quotes
                GROUP BY origin, destination, advance_days
                ORDER BY origin, destination, advance_days
                """
            )
        ]

        rows = query_all_rows(connection)

    duplicate_rows = compute_duplicate_rows(rows)
    invalid_rows, missing_base_fare, missing_taxes = compute_invalid_rows(rows)
    outlier_stats = compute_outliers(rows)

    coverage_count = len(coverage)
    route_count = len(by_route)
    source_count = len(by_source)

    summary = {
        "database": str(DB_PATH),
        "generated_at": latest_observed,
        "total_quotes": total_rows,
        "source_count": source_count,
        "route_count": route_count,
        "coverage_cells": coverage_count,
        "duplicate_rows": duplicate_rows,
        "invalid_quotes": invalid_rows,
        "missing_base_fare_rows": missing_base_fare,
        "missing_taxes_rows": missing_taxes,
        "outlier_rows": outlier_stats["outlier_rows"],
        "route_groups_with_outliers": outlier_stats["route_groups_with_outliers"],
        "sources": by_source,
        "routes": by_route,
        "horizons": by_horizon,
        "coverage": coverage,
    }

    return summary


REQUIRED_TRAINING_FIELDS = (
    "source",
    "origin",
    "destination",
    "departure_date",
    "advance_days",
    "airline",
    "flight_number",
    "departure_time",
    "arrival_time",
    "observed_at",
    "total_fare",
    "base_fare",
    "taxes",
)

TRAINING_READY_FIELD_ORDER = [
    "id",
    "run_id",
    "observed_at",
    "source",
    "source_type",
    "origin",
    "destination",
    "departure_date",
    "advance_days",
    "airline",
    "airline_code",
    "flight_number",
    "departure_time",
    "arrival_time",
    "duration_minutes",
    "stops",
    "fare_class",
    "base_fare",
    "taxes",
    "convenience_fee",
    "total_fare",
    "currency",
    "availability",
    "scrape_status",
    "error_message",
    "provider",
    "source_record_id",
    "scraped_at",
]


def write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(header, "") for header in headers])


def build_training_ready_dataset():
    with sqlite3.connect(DB_PATH) as connection:
        rows = query_all_rows(connection)

    seen_keys = set()
    quarantine_rows = []
    training_candidates = []
    duplicate_rows = 0
    missing_required_fields_rows = 0
    invalid_fare_rows = 0

    for row in rows:
        row_copy = dict(row)
        reasons = []
        key = tuple((row_copy.get(field) if row_copy.get(field) is not None else "__NULL__") for field in DUPLICATE_KEY_FIELDS)

        if key in seen_keys:
            duplicate_rows += 1
            reasons.append("duplicate_row")
        else:
            seen_keys.add(key)

        if not reasons:
            missing_fields = [field for field in REQUIRED_TRAINING_FIELDS if row_copy.get(field) in (None, "")]
            if missing_fields:
                missing_required_fields_rows += 1
                reasons.append("missing_required_fields:" + ",".join(missing_fields))
            else:
                try:
                    total_fare = float(row_copy.get("total_fare", 0) or 0)
                except (TypeError, ValueError):
                    total_fare = -1
                if total_fare <= 0:
                    invalid_fare_rows += 1
                    reasons.append("invalid_total_fare")

        if reasons:
            row_copy["rejection_reasons"] = "; ".join(reasons)
            quarantine_rows.append(row_copy)
            continue

        training_candidates.append(row_copy)

    grouped_by_route = defaultdict(list)
    for row in training_candidates:
        grouped_by_route[(row["origin"], row["destination"])].append(row)

    outlier_rows = 0
    route_groups_with_outliers = 0
    outlier_ids = set()

    for route_key, route_rows in grouped_by_route.items():
        if len(route_rows) < 4:
            continue

        values = sorted([float(row["total_fare"]) for row in route_rows if row.get("total_fare") is not None])
        if len(values) < 4:
            continue

        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        route_outliers = [row for row in route_rows if float(row["total_fare"]) < lower_bound or float(row["total_fare"]) > upper_bound]
        if route_outliers:
            route_groups_with_outliers += 1
            outlier_rows += len(route_outliers)
            outlier_ids.update(row["id"] for row in route_outliers)

    training_ready_rows = []
    for row in training_candidates:
        if row["id"] in outlier_ids:
            row["rejection_reasons"] = "outlier_row"
            quarantine_rows.append(row)
            continue
        training_ready_rows.append(row)

    training_ready_rows.sort(key=lambda row: (row.get("observed_at") or "", row.get("origin") or "", row.get("destination") or "", row.get("advance_days") or 0, row.get("id") or 0))
    quarantine_rows.sort(key=lambda row: (row.get("observed_at") or "", row.get("origin") or "", row.get("destination") or "", row.get("advance_days") or 0, row.get("id") or 0))

    TRAINING_READY_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_csv(TRAINING_READY_CSV, TRAINING_READY_FIELD_ORDER, training_ready_rows)
    write_csv(TRAINING_QUARANTINE_CSV, TRAINING_READY_FIELD_ORDER + ["rejection_reasons"], quarantine_rows)

    latest_observed = max((row.get("observed_at") for row in rows if row.get("observed_at")), default=None)
    summary = {
        "generated_at": latest_observed,
        "total_quotes": len(rows),
        "training_ready_rows": len(training_ready_rows),
        "quarantine_rows": len(quarantine_rows),
        "duplicate_rows": duplicate_rows,
        "missing_required_fields_rows": missing_required_fields_rows,
        "invalid_fare_rows": invalid_fare_rows,
        "outlier_rows": outlier_rows,
        "route_groups_with_outliers": route_groups_with_outliers,
        "required_training_fields": list(REQUIRED_TRAINING_FIELDS),
        "training_ready_csv": str(TRAINING_READY_CSV),
        "training_quarantine_csv": str(TRAINING_QUARANTINE_CSV),
    }
    TRAINING_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    summary = build_summary()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    training_summary = build_training_ready_dataset()

    print(json.dumps({
        "output_file": str(OUTPUT_PATH),
        "total_quotes": summary["total_quotes"],
        "source_count": summary["source_count"],
        "route_count": summary["route_count"],
        "coverage_cells": summary["coverage_cells"],
        "duplicate_rows": summary["duplicate_rows"],
        "invalid_quotes": summary["invalid_quotes"],
        "outlier_rows": summary["outlier_rows"],
        "training_ready_rows": training_summary["training_ready_rows"],
        "quarantine_rows": training_summary["quarantine_rows"],
        "training_ready_csv": training_summary["training_ready_csv"],
        "training_quarantine_csv": training_summary["training_quarantine_csv"],
    }, indent=2))


if __name__ == "__main__":
    main()
