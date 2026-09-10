# Udaankosh — Airfare Price Index (APIx)

## 1. Project Information

- **Project Title:** Udaankosh — Airfare Price Index (APIx): Measuring India's Domestic Airfare Movement
- **PS ID:** 26056
- **PS Title:** Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)
- **Category:** Software
- **Theme:** Smart Automation
- **Team Name (Registered on portal):** SKYLYTICS

## 2. Problem Statement

Airfare movement in India is fragmented across airlines and online travel aggregator (OTA) portals, with dynamic, individually-varying ticket prices. There is no centralized, standardized indicator of how domestic airfares move over time — something that could otherwise augment official inflation/CPI analysis with an airfare-specific market indicator.

## 3. Proposed Solution

**Udaankosh** collects real-time fare data from multiple online travel sources (airline/OTA portals), standardizes the raw observations into route-level statistics, and calculates a **Route- & Market-level Airfare Price Index (APIx)**. The platform delivers interactive route and market intelligence through a live multi-page dashboard, turning fragmented individual ticket quotes into a standardized, comparable indicator of domestic airfare movement.

**How it works:**
Multiple Fare Sources → Structured Fare Database → Route Intelligence → Airfare Price Index → Market-Level Insights

| Problem | Solution |
|---|---|
| Fragmented fares | Centralized structured dataset |
| Dynamic prices | Multi-horizon tracking |
| Individual ticket ≠ market movement | Aggregated route & market index |
| Limited historical insight | Continuous data collection |

## 4. Key Features

- Multi-source fare collection (airline & OTA portals) via automated scrapers
- Structured SQLite fare database
- Route- and market-level Airfare Price Index (APIx) calculation
- Multi-horizon fare tracking (T+1, T+7, T+15, T+30, T+45)
- Multi-page dashboard: Home, APIx, CPI, Route, Market Overview, Prediction, Source Health
- Read-only API layer serving collected and processed data
- Scheduled/automated data collection via Windows Task Scheduler scripts
- ML readiness pipeline for future airfare forecasting

## 5. Technology Stack

- **Frontend:** HTML, CSS, JavaScript (multi-page: `index.html`, `apix.html`, `cpi.html`, `route.html`, `market-overview.html`, `prediction.html`, `source-health.html`)
- **Backend:** Python (`api_server.py`)
- **Data Layer:** SQLite (`data/`)
- **Scraping:** Python-based scrapers (`scraper/`) for Cleartrip, EaseMyTrip, Yatra
- **ML / Forecasting:** `ml_data_readiness.py`, `train_ml_model.py`
- **Automation:** Windows Task Scheduler batch scripts (`run_scheduler.bat`, `setup_scheduler.bat`, `remove_scheduler.bat`)
- **Testing:** `tests/`, `validate_db.py`

## 6. Architecture

See [docs/architecture.md](docs/architecture.md) *(or `PROJECT_HANDOFF.md` for a full technical handoff)*.

```text
Multiple Fare Sources (Cleartrip, EaseMyTrip, Yatra)
        |
        v
scraper/  →  Automated fare collection
        |
        v
data/  →  Structured SQLite fare database
        |
        v
api_server.py  →  Backend API
        |
        v
Analytics  →  Route Intelligence + APIx Index Methodology
        |
        v
Frontend Dashboard — Udaankosh
(index.html, apix.html, cpi.html, route.html,
 market-overview.html, prediction.html, source-health.html)
```

### Index Methodology

**APIx,t = 100 × [ Σ wᵢ (Pᵢ,t / Pᵢ,0) ] / Σ wᵢ**

Conceptually based on the classical **Laspeyres Price Index**:
L = Σ(P₁ᵢ × Q₀ᵢ) / Σ(P₀ᵢ × Q₀ᵢ) × 100

- **Current weighting:** Provisional equal route weights (pending DGCA traffic data)
- **Base period:** Earliest available observation date
- **Base index:** 100

## 7. Repository Structure

```text
NSUT_SIH_SKYLYTICS/
├── README.md
├── DATA_REQUIRED_FROM_USER.md
├── PROJECT_HANDOFF.md
├── ML_EXECUTION_CHECKLIST.md
├── ML_IMPLEMENTATION_PLAN.md
├── ML_READINESS_CHECKLIST.md
├── requirements.txt
├── .gitignore
│
├── api_server.py              # Backend API server
├── run_all.py                 # Runs the full pipeline
├── ml_data_readiness.py       # ML data readiness checks
├── train_ml_model.py          # Model training
├── validate_db.py             # Database validation
│
├── index.html / script.js / style.css     # Home page
├── apix.html / apix-page.js                # APIx index page
├── cpi.html / cpi-page.js                  # CPI comparison page
├── route.html / route-page.js              # Route Intelligence page
├── market-overview.html / overview-page.js # Market Overview page
├── prediction.html / prediction-page.js    # Forecasting page
├── source-health.html / source-health.js   # Source Health monitor
│
├── plane.png / hero-bg.mp4 / hero-poster.jpg.jpeg   # UI assets
│
├── start_udaankosh.bat        # Launches the Udaankosh website
├── run_scheduler.bat          # Runs the scheduled scraper job
├── setup_scheduler.bat        # Sets up Windows Task Scheduler job
├── remove_scheduler.bat       # Removes the scheduled job
│
├── data/                      # SQLite fare database
├── scraper/                   # Playwright/Python scrapers (Cleartrip, EaseMyTrip, Yatra)
└── tests/                     # Test suite
```

### What goes where?

| Item | Location |
|---|---|
| Scrapers (Cleartrip, EaseMyTrip, Yatra) | `scraper/` |
| Backend API | `api_server.py` |
| Udaankosh dashboard pages | root (`*.html`, `*-page.js`) |
| SQLite fare database | `data/` |
| Automation / scheduling | `*.bat` scripts |
| ML pipeline | `ml_data_readiness.py`, `train_ml_model.py` |
| Tests / validation | `tests/`, `validate_db.py` |
| Project handoff & planning docs | `PROJECT_HANDOFF.md`, `ML_*.md` |
| Project overview | `README.md` |

## 8. Final Presentation

https://drive.google.com/drive/folders/1RJizTzI2wcJcFSHOuUjSkCLpNCqo9eEn?usp=sharing

## 9. Demo Video
https://drive.google.com/drive/folders/1d6qg0TSqGZVLeYEBzR4QczcbVH8UClt2

## 10. Installation

```bash
git clone <YOUR_REPOSITORY_URL>
cd NSUT_SIH_SKYLYTICS
pip install -r requirements.txt
```

## 11. Run

**Quick start (Windows):**
Double-click `start_udaankosh.bat` — this launches the backend API server and opens the Udaankosh website (`index.html`) with all pages (APIx, CPI, Route, Market Overview, Prediction, Source Health) connected and ready.

**Manual start:**
```bash
python api_server.py
```
Then open `index.html` in a browser.

**Optional — scheduled data collection:**
```bash
setup_scheduler.bat   # sets up automated scraping via Task Scheduler
run_scheduler.bat      # runs a scrape job on demand
remove_scheduler.bat   # removes the scheduled job
```

## 12. Current Data Snapshot

- **8** routes tracked
- **5** booking horizons (T+1, T+7, T+15, T+30, T+45)
- **14,000+** fare observations
- **3** fare sources: Cleartrip, EaseMyTrip, Yatra

## 13. Future Scope

- Integrate official DGCA passenger traffic data for accurate route weights
- Integrate MoSPI CPI data for cross-referencing with official inflation indicators
- Complete ML readiness pipeline and train forecasting models (see `ML_IMPLEMENTATION_PLAN.md`)
- Extend to a longer time-series dataset for trend robustness
- Add airfare forecasting/ML with confidence intervals (`prediction.html`)
- Migrate from SQLite to PostgreSQL to support a national-scale deployment with larger, concurrent data volumes across more routes and sources
- Expand data collection to include more granular airline-level details (carrier, aircraft type, fare class, baggage/refund policy) alongside route-level fares, for deeper airline-wise comparison
- Scale from 8 routes / 5 horizons / 3 sources → more routes, more sources, a national-level indicator

