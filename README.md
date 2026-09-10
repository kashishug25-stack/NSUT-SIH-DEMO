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

**Udaankosh** collects real-time fare data from multiple online travel sources (airline/OTA portals), standardizes the raw observations into route-level statistics, and calculates a **Route- & Market-level Airfare Price Index (APIx)**. The platform delivers interactive route and market intelligence through a live dashboard, turning fragmented individual ticket quotes into a standardized, comparable indicator of domestic airfare movement.

**How it works:**
Multiple Fare Sources → Structured Fare Database → Route Intelligence → Airfare Price Index → Market-Level Insights

| Problem | Solution |
|---|---|
| Fragmented fares | Centralized structured dataset |
| Dynamic prices | Multi-horizon tracking |
| Individual ticket ≠ market movement | Aggregated route & market index |
| Limited historical insight | Continuous data collection |

## 4. Key Features

- Multi-source fare collection (airline & OTA portals)
- Structured SQLite fare database
- Route- and market-level Airfare Price Index calculation
- Multi-horizon fare tracking (T+1, T+7, T+15, T+30, T+45)
- Interactive dashboard: Route Intelligence, Airline Comparison, OTA Comparison, Market Overview, Horizon Analysis
- Read-only API layer serving collected and processed data
- Deduplication, outlier detection, and sold-out/missing-data handling

## 5. Technology Stack

- **Frontend:** React, Tailwind CSS
- **Backend:** Python, FastAPI (read-only API server)
- **Data Layer:** SQLite (structured fare observations)
- **Scraping:** Playwright (Cleartrip, EaseMyTrip, Yatra)
- **Analytics:** Route median fare → price index computation
- **Deployment:** Docker / Cloud

## 6. Architecture

See [docs/architecture.md](docs/architecture.md).

```text
Multiple Fare Sources (Cleartrip, EaseMyTrip, Yatra)
        |
        v
Data Collection (Playwright scrapers)
        |
        v
Structured Fare Database (SQLite)
        |
        v
Backend API (Python + FastAPI)
        |
        v
Analytics (Route Intelligence + Index Methodology)
        |
        v
Frontend Dashboard — Udaankosh (React + Tailwind CSS)
```

### API Endpoints (read-only)

- `/api/route`
- `/api/route-horizons`
- `/api/index`
- `/api/index-series`
- `/api/market-overview`

### Index Methodology

**APIx,t = 100 × [ Σ wᵢ (Pᵢ,t / Pᵢ,0) ] / Σ wᵢ**

Conceptually based on the classical **Laspeyres Price Index**:
L = Σ(P₁ᵢ × Q₀ᵢ) / Σ(P₀ᵢ × Q₀ᵢ) × 100

- **Current weighting:** Provisional equal route weights (pending DGCA traffic data)
- **Base period:** Earliest available observation date
- **Base index:** 100

## 7. Repository Structure

```text
UDAANKOSH-APIX/
├── README.md
├── SUBMISSION_GUIDE.md
├── submission/
│   ├── PRESENTATION.md
│   └── DEMO.md
├── src/
│   ├── scraper/          # Playwright scrapers (Cleartrip, EaseMyTrip, Yatra)
│   ├── api/              # FastAPI backend
│   └── frontend/         # React + Tailwind dashboard (Udaankosh)
├── data/
│   └── fares.db          # SQLite canonical fare database
├── docs/
│   └── architecture.md
├── assets/
│   └── screenshots/
│       └── README.md
├── requirements.txt
├── .gitignore
└── LICENSE
```

### What goes where?

| Item | Location |
|---|---|
| Scrapers (Cleartrip, EaseMyTrip, Yatra) | `src/scraper/` |
| Backend API | `src/api/` |
| Udaankosh dashboard frontend | `src/frontend/` |
| SQLite fare database | `data/` |
| Architecture / technical documentation | `docs/` |
| Project screenshots | `assets/screenshots/` |
| Final PPT / presentation | `submission/` |
| Demo video link | `submission/DEMO.md` |
| Project overview | `README.md` |

## 8. Final Presentation

Keep your final SIH presentation in the repository whenever the file size allows it.

See [submission/PRESENTATION.md](submission/PRESENTATION.md) for the required format.

If the PPT is too large for GitHub, use Google Drive/OneDrive and put the accessible viewer link in `submission/PRESENTATION.md`.

## 9. Demo Video

Add the YouTube/Google Drive link in [submission/DEMO.md](submission/DEMO.md).

## 10. Screenshots / Prototype Photos

Add dashboard screenshots (Route Intelligence, Airline Comparison, OTA Comparison, Market Overview, Horizon Analysis) to:

`assets/screenshots/`

See [assets/screenshots/README.md](assets/screenshots/README.md) for examples and naming conventions.

## 11. Installation

```bash
git clone <YOUR_REPOSITORY_URL>
cd UDAANKOSH-APIX
pip install -r requirements.txt
```

## 12. Run

```bash
uvicorn src.api.main:app --reload
```

## 13. Current Data Snapshot

- **8** routes tracked
- **5** booking horizons (T+1, T+7, T+15, T+30, T+45)
- **14,000+** fare observations
- **3** fare sources: Cleartrip, EaseMyTrip, Yatra

## 14. Future Scope

- Integrate official DGCA passenger traffic data for accurate route weights
- Integrate MoSPI CPI data for cross-referencing with official inflation indicators
- Build a robust data-quality pipeline (deduplication, outlier detection, completeness checks)
- Extend to a longer time-series dataset for trend robustness
- Add airfare forecasting/ML with confidence intervals
- Scale from 8 routes / 5 horizons / 3 sources → more routes, more sources, a national-level indicator

## Important

Before submission, make sure the repository is accessible to reviewers. Do **not** upload passwords, API keys, access tokens, `.env` files containing secrets, or other confidential credentials.
