
import argparse
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scraper.canonical_db import (
    init_db, start_run, finish_run, start_source, finish_source,
    insert_quotes, summary
)
from scraper.browser import launch_browser
from scraper.sources import easemytrip, yatra, cleartrip

ROUTES = [
    ("DEL", "BOM"),
    ("DEL", "BLR"),
    ("DEL", "CCU"),
    ("DEL", "HYD"),
    ("DEL", "GOI"),
    ("DEL", "PAT"),
    ("BOM", "BLR"),
    ("MAA", "DEL"),
]
HORIZONS = {"T1": 1, "T7": 7, "T15": 15, "T30": 30, "T45": 45}

def duration_minutes(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).lower()
    h = re.search(r"(\d+)\s*h", s)
    m = re.search(r"(\d+)\s*m", s)
    if h or m:
        return int(h.group(1) if h else 0) * 60 + int(m.group(1) if m else 0)
    return None

def clock_duration(dep, arr):
    if not dep or not arr:
        return None
    try:
        h1, m1 = map(int, dep.split(":"))
        h2, m2 = map(int, arr.split(":"))
        n = h2 * 60 + m2 - (h1 * 60 + m1)
        return n if n >= 0 else n + 1440
    except Exception:
        return None

def yatra_duration(row):
    # Yatra's tested DB does not expose a duration field; calculate it from
    # departure/arrival clocks, correctly handling overnight flights.
    return clock_duration(row.get("departure_time"), row.get("arrival_time"))

def emt_quote(offer, days):
    return {
        "source": "easemytrip", "source_type": "ota",
        "origin": offer.origin, "destination": offer.destination,
        "departure_date": offer.departure_date, "advance_days": days,
        "airline": offer.airline, "airline_code": None,
        "flight_number": offer.flight_number,
        "departure_time": offer.departure_time,
        "arrival_time": offer.arrival_time,
        "duration_minutes": duration_minutes(offer.duration),
        "stops": offer.stops,
        "fare_class": offer.cabin or "Economy",
        "base_fare": None, "taxes": None, "convenience_fee": None,
        "total_fare": offer.price, "currency": offer.currency or "INR",
        "availability": "available" if offer.price and offer.price > 0 else "unknown",
        "scrape_status": offer.scrape_status,
        "provider": "EaseMyTrip",
        "source_record_id": offer.flight_number,
        "observed_at": offer.observed_at,
    }

def yatra_quote(row, days):
    route = row["route"].split("-")
    return {
        "source": "yatra", "source_type": "ota",
        "origin": route[0], "destination": route[1],
        "departure_date": row["flight_date"], "advance_days": days,
        "airline": row.get("airline_name"),
        "airline_code": row.get("airline_code"),
        "flight_number": row.get("flight_ids"),
        "departure_time": row.get("departure_time"),
        "arrival_time": row.get("arrival_time"),
        "duration_minutes": yatra_duration(row),
        "stops": row.get("num_stops"),
        "fare_class": row.get("cabin") or "Economy",
        "base_fare": row.get("base_fare"),
        "taxes": None, "convenience_fee": None,
        "total_fare": row.get("total_fare"), "currency": "INR",
        "availability": "available",
        "scrape_status": "SUCCESS", "provider": "Yatra",
        "source_record_id": row.get("flight_ids"),
        "observed_at": row.get("scraped_at"),
    }

def cleartrip_quote(row, days):
    return {
        "source": "cleartrip", "source_type": "ota",
        "origin": row["origin"], "destination": row["destination"],
        "departure_date": row["date_ymd"], "advance_days": days,
        "airline": row.get("airline_name"),
        "airline_code": row.get("airline_code"),
        "flight_number": row.get("flight_numbers"),
        "departure_time": row.get("dep_time"),
        "arrival_time": row.get("arr_time"),
        "duration_minutes": row.get("duration_min"),
        "stops": row.get("stops"),
        "fare_class": row.get("cabin") or "Economy",
        "base_fare": row.get("base_fare"),
        "taxes": row.get("tax"),
        "convenience_fee": None,
        "total_fare": row.get("total_fare"), "currency": "INR",
        "availability": "available",
        "scrape_status": "SUCCESS", "provider": "Cleartrip",
        "source_record_id": row.get("travel_option_id") or row.get("fare_id"),
    }

def run_easemytrip(run_id, headed=True, route_limit=0, horizon_limit=0):
    start_source(run_id, "easemytrip")
    written = 0
    try:
        routes = ROUTES[:route_limit] if route_limit else ROUTES
        horizons = list(HORIZONS.items())[:horizon_limit] if horizon_limit else list(HORIZONS.items())
        with launch_browser(headless=not headed) as page:
            for origin, destination in routes:
                for name, days in horizons:
                    travel = (date.today() + timedelta(days=days)).isoformat()
                    print(f"[EaseMyTrip] {origin}->{destination} {name} {travel}")
                    try:
                        easemytrip.search(page, origin, destination, travel)
                        offers = easemytrip.extract_offers(
                            page, origin, destination, travel, "Economy"
                        )
                        n = insert_quotes(run_id, [emt_quote(x, days) for x in offers])
                        written += n
                        print(f"  [OK] {n} rows")
                    except Exception as exc:
                        print(f"  [!] {type(exc).__name__}: {exc}")
                    time.sleep(3)
        finish_source(run_id, "easemytrip", "SUCCESS", written)
    except Exception as exc:
        finish_source(run_id, "easemytrip", "FAILED", written, str(exc))
        print(f"[EaseMyTrip] FAILED: {type(exc).__name__}: {exc}")
    return written

def run_yatra(run_id, headed=True, route_limit=0, horizon_limit=0):
    start_source(run_id, "yatra")
    written = 0
    browser = context = page = None
    try:
        routes = ROUTES[:route_limit] if route_limit else ROUTES
        horizons = list(HORIZONS.items())[:horizon_limit] if horizon_limit else list(HORIZONS.items())
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser, context = yatra.build_stealth_context(p)
            page = context.new_page()
            yatra.warmup_session(page)
            for origin, destination in routes:
                for name, days in horizons:
                    travel = date.today() + timedelta(days=days)
                    print(f"[Yatra] {origin}->{destination} {name} {travel.isoformat()}")
                    try:
                        rows = yatra.run_search(page, origin, destination, travel)
                        n = insert_quotes(run_id, [yatra_quote(x, days) for x in rows])
                        written += n
                        print(f"  [OK] {n} rows")
                    except Exception as exc:
                        print(f"  [!] {type(exc).__name__}: {exc}")
                    time.sleep(3)
        finish_source(run_id, "yatra", "SUCCESS", written)
    except Exception as exc:
        finish_source(run_id, "yatra", "FAILED", written, str(exc))
        print(f"[Yatra] FAILED: {type(exc).__name__}: {exc}")
    finally:
        for obj in (page, context, browser):
            try:
                if obj:
                    obj.close()
            except Exception:
                pass
    return written

def run_cleartrip(run_id, headed=True, route_limit=0, horizon_limit=0):
    start_source(run_id, "cleartrip")
    written = 0
    try:
        routes = ROUTES[:route_limit] if route_limit else ROUTES
        horizons = list(HORIZONS.items())[:horizon_limit] if horizon_limit else list(HORIZONS.items())
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            ctx = cleartrip.make_context(p)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(60000)
            try:
                print("[Cleartrip] Warmup")
                page.goto(cleartrip.HOME_URL, wait_until="domcontentloaded", timeout=90000)
                time.sleep(5)
                if cleartrip.page_blocked_by_cf(page):
                    if not cleartrip.solve_cf(page, timeout_s=300):
                        raise RuntimeError("Cleartrip Cloudflare check was not cleared")
                cleartrip.human_scroll(page, rounds=4)
                cleartrip.save_cookies(ctx)
            except Exception as exc:
                print(f"[Cleartrip] warmup warning: {type(exc).__name__}: {exc}")

            for origin, destination in routes:
                for name, days in horizons:
                    travel = date.today() + timedelta(days=days)
                    print(f"[Cleartrip] {origin}->{destination} {name} {travel.isoformat()}")
                    try:
                        rows = cleartrip.scrape_one(
                            page, origin, destination, travel, "Economy", "Economy"
                        )
                        n = insert_quotes(run_id, [cleartrip_quote(x, days) for x in rows])
                        written += n
                        print(f"  [OK] {n} rows")
                    except Exception as exc:
                        print(f"  [!] {type(exc).__name__}: {exc}")
                    time.sleep(5)
            try:
                page.close()
            except Exception:
                pass
            try:
                ctx.close()
            except Exception:
                pass
        finish_source(run_id, "cleartrip", "SUCCESS", written)
    except Exception as exc:
        finish_source(run_id, "cleartrip", "FAILED", written, str(exc))
        print(f"[Cleartrip] FAILED: {type(exc).__name__}: {exc}")
    return written

def main():
    ap = argparse.ArgumentParser(description="Unified Skylytics 3-source OTA collector")
    ap.add_argument("--source", choices=["all", "easemytrip", "yatra", "cleartrip"], default="all")
    ap.add_argument("--headed", action="store_true", help="Show browser windows (recommended)")
    ap.add_argument("--route-limit", type=int, default=0, help="0 = all 8 routes")
    ap.add_argument("--horizon-limit", type=int, default=0, help="0 = all 5 horizons")
    args = ap.parse_args()

    init_db()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    start_run(run_id, "Three-source live OTA collection")

    jobs = []
    # Source execution order is intentional: Cleartrip -> EaseMyTrip -> Yatra.
    if args.source in ("all", "cleartrip"):
        jobs.append(run_cleartrip)
    if args.source in ("all", "easemytrip"):
        jobs.append(run_easemytrip)
    if args.source in ("all", "yatra"):
        jobs.append(run_yatra)

    for job in jobs:
        source_name = {
            run_easemytrip: "EaseMyTrip",
            run_yatra: "Yatra",
            run_cleartrip: "Cleartrip",
        }[job]
        print("\n" + "=" * 70)
        print(f"STARTING SOURCE PHASE: {source_name}")
        print("All configured routes + horizons for this source will finish first.")
        print("=" * 70)
        job(run_id, headed=True, route_limit=args.route_limit, horizon_limit=args.horizon_limit)
        print("\n" + "=" * 70)
        print(f"FINISHED SOURCE PHASE: {source_name}")
        print("Moving to the next source only now.")
        print("=" * 70)

    total, by_source, by_horizon = summary()
    finish_run(run_id, "SUCCESS")
    print("\n" + "=" * 70)
    print("SKYLITICS UNIFIED SCRAPER COMPLETE")
    print("=" * 70)
    print("Canonical DB:", ROOT / "data" / "airfare_intelligence.db")
    print("Total quotes:", total)
    print("By source:", by_source)
    print("By horizon:", by_horizon)

if __name__ == "__main__":
    main()
