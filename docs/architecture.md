# Architecture — Udaankosh (APIx)

## Data Flow

```
Multiple Fare Sources (Cleartrip, EaseMyTrip, Yatra)
        |
        v
src/scraper/  →  Automated fare collection
        |
        v
src/data/  →  Structured SQLite fare database
        |
        v
src/backend/api_server.py  →  Backend API
        |
        v
Analytics  →  Route Intelligence + APIx Index Methodology
        |
        v
Frontend Dashboard — Udaankosh (src/)
(index.html, apix.html, cpi.html, route.html,
 market-overview.html, prediction.html, source-health.html)
```

## Index Methodology

**APIx,t = 100 × [ Σ wᵢ (Pᵢ,t / Pᵢ,0) ] / Σ wᵢ**

Conceptually based on the classical **Laspeyres Price Index**:

```
L = Σ(P₁ᵢ × Q₀ᵢ) / Σ(P₀ᵢ × Q₀ᵢ) × 100
```

- **Current weighting:** Provisional equal route weights (pending DGCA traffic data)
- **Base period:** Earliest available observation date
- **Base index:** 100

## Components

| Component            | Responsibility                                              | Location              |
| --------------------- | ------------------------------------------------------------ | ---------------------- |
| Scrapers              | Collect raw fare quotes from Cleartrip, EaseMyTrip, Yatra     | `src/scraper/`          |
| Fare Database          | Store structured, deduplicated fare observations              | `src/data/`             |
| Backend API            | Serve processed fare/index data to the dashboard              | `src/backend/api_server.py` |
| ML Readiness Pipeline  | Validate and prep data for forecasting models                 | `src/backend/ml_data_readiness.py`, `train_ml_model.py` |
| Dashboard              | Multi-page UI for APIx, CPI, Route, Market, Prediction, Health | `src/*.html`, `src/*-page.js` |
| Automation             | Scheduled scraping via Windows Task Scheduler                 | `src/automation/*.bat`  |

For full technical handoff notes, see [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md).
