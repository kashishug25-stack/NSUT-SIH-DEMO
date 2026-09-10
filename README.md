# Skylytics — Unified 3-Source Scraper

This package combines the three live OTA collectors used by Skylytics:

- EaseMyTrip
- Yatra
- Cleartrip

All successful observations are normalized into ONE authoritative SQLite database:

    data/airfare_intelligence.db

Canonical table:

    raw_fare_quotes

## Routes

DEL-BOM, DEL-BLR, DEL-CCU, DEL-HYD, DEL-GOI, DEL-PAT, BOM-BLR, MAA-DEL

## Horizons

T+1, T+7, T+15, T+30, T+45

## Install — Windows CMD

    py -m pip install -r requirements.txt
    py -m playwright install chromium

## Database smoke test

    py validate_db.py
    py -m pytest -q

## One route + one horizon per source

    py run_all.py --source easemytrip --headed --route-limit 1 --horizon-limit 1
    py run_all.py --source yatra --headed --route-limit 1 --horizon-limit 1
    py run_all.py --source cleartrip --headed --route-limit 1 --horizon-limit 1

## Full collection

    py run_all.py --source all --headed

The unified runner is sequential and rate-limited.

## Important

- The unified runner keeps the browser visible.
- CAPTCHA/Cloudflare checks are not programmatically bypassed. If a normal human
  verification appears, use the open browser's normal manual interaction.
- No login credentials or private cookies are included in this package.
- Total fare is the primary price field. Base fare/tax are only populated where
  the source actually provides them.
- The three OTA sources remain source-attributed; do not treat them as three
  independent airline-direct observations.
- The source implementations are live-site scrapers and can break when websites
  change. Always run the one-route/one-horizon smoke test first.

## Architecture

    EaseMyTrip ─┐
    Yatra ──────┼──> canonical normalization ──> raw_fare_quotes
    Cleartrip ──┘

The source-specific SQLite databases used during earlier testing are NOT required
by the unified runner.

## Automatic 6-Hour Scheduling (Windows)

1. Install dependencies and Playwright Chromium as described above.
2. Run `run_scheduler.bat` for a manual full 3-source scrape.
3. Double-click `setup_scheduler.bat` once to install the Windows Task Scheduler job.
4. The job is named `Skylytics Scraper - Every 6 Hours` and runs the full scraper every 6 hours.
5. Use `remove_scheduler.bat` to remove the scheduled job.

The scheduler is independent of the frontend. The scraper writes observations to the SQLite database even when the frontend is closed.

Because the current scrapers use headed Chrome, the Windows account needs to be logged in when the scheduled run occurs.
