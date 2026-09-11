# UDAANKOSH / SKYLITICS PROJECT HANDOFF

## 1. Project Goal

Build a real-time Indian airfare price intelligence platform for SIH Problem Statement SIH0264.

The platform should collect online domestic airfare observations and support an experimental Airfare Price Index (APIx) that can augment CPI analysis. It is not an official CPI replacement.

Required source categories:

- Airlines: IndiGo, Air India, Air India Express, Akasa Air, SpiceJet
- OTAs: Cleartrip, EaseMyTrip, Yatra, and future OTA additions
- Cabin scope for prototype: Economy only
- Future cabin scope: Premium Economy, Business, First Class
- Routes currently configured:
  - DEL-BOM
  - DEL-BLR
  - DEL-CCU
  - DEL-HYD
  - DEL-GOI
  - DEL-PAT
  - BOM-BLR
  - MAA-DEL
- Advance windows:
  - T+1
  - T+7
  - T+15
  - T+30
  - T+45

## 2. Important Frozen-Data Rule

The scraper and database are currently treated as frozen.

Do not modify scraper behavior unless explicitly requested.

Do not modify:

- scraper/
- run_all.py
- scraper/models.py
- data/airfare_intelligence.db

The frontend/API must read existing SQLite values only. Never fabricate fares, taxes, airlines, OTAs, flights, or historical observations.

Current scraper execution order:

1. Cleartrip
2. EaseMyTrip
3. Yatra

## 3. Current Database

Database file:

data/airfare_intelligence.db

Main table:

raw_fare_quotes

Important fields:

- source
- origin
- destination
- departure_date
- advance_days
- airline
- flight_number
- departure_time
- arrival_time
- total_fare
- base_fare
- taxes
- availability
- scrape_status
- observed_at
- scraped_at

Current verified database state during development:

- About 6,048 quote rows
- 8 configured routes
- All five horizons represented
- Collection observations on 2026-09-09 and 2026-09-10
- Economy fare data available
- Base fare and tax are often NULL because the source listing does not expose an official breakdown

Interpretation of dates:

- observed_at = date when the scraper collected/observed the fare
- departure_date = actual flight travel date
- advance_days = difference between collection date and travel date

If collection date is 2026-09-10:

- T+1  -> departure 2026-09-11
- T+7  -> departure 2026-09-17
- T+15 -> departure 2026-09-25
- T+30 -> departure 2026-10-10
- T+45 -> departure 2026-10-25

The user selects the collection date represented by the latest database collection. The frontend calculates the departure date from the selected horizon. The user should not manually enter the future departure date.

## 4. Completed Files and Responsibilities

### api_server.py

Read-only local HTTP server and API layer.

Runs the frontend and reads SQLite values.

Current endpoints:

- GET /api/meta
  - latest collection/observation date
  - supported horizons
- GET /api/route?origin=DEL&destination=BOM&advance_days=7&departure_date=2026-09-17
  - selected route data
  - quote count
  - median/minimum/maximum total fare
  - airline and OTA summaries
  - observed-date series
  - stored quote rows
- GET /api/route-horizons?origin=DEL&destination=BOM
  - route lead-time data for T+1 through T+45
  - airline series
  - OTA series
- GET /api/index?advance_days=7
  - current Laspeyres-style value
  - base period
  - current period
  - route coverage
- GET /api/index-series?advance_days=7
  - daily index observations by collection date
- GET /api/market-overview
  - all route medians by horizon
  - total quote count
  - cheapest route
  - highest route
  - route basket summary

### index.html

Home/query page.

Current intended home contents:

- Compact database summary:
  - Airfare Index
  - Observations
  - Tracked routes
  - Active sources
- Origin selector with full city name and airport code
- Destination selector with full city name and airport code
- Derived departure date field
- Horizon selector
- Economy cabin selector
- Disabled future cabin options
- Input Route button
- Compute Fare Intelligence button
- Separate Explore all-route market overview entry

No detailed graph or Market Radar should be on the home page.

### script.js

Home page behavior.

Responsibilities:

- Populate supported origin/destination options
- Validate route selection
- Fetch latest collection date
- Calculate departure date from horizon
- Navigate to route.html
- Navigate to market-overview.html
- Load compact home summary values

### style.css

Shared styling for home and dedicated pages.

### route.html

Dedicated selected-route page.

Expected content:

- Selected route context
- Collection date
- Calculated departure date
- Horizon
- Economy cabin
- Median fare
- Lowest fare
- Quote count
- Route-level APIx
- Airline comparison
- OTA comparison
- T+1, T+7, T+15, T+30, T+45 controls
- All horizons control
- Recent stored flight table

### route-page.js

Reads route page URL parameters:

- origin
- destination
- collection_date
- advance_days

Calls the read-only route/index APIs and renders route values.

### market-overview.html

Dedicated all-route page. It must not depend on a selected route.

Expected content:

- All 8 routes
- T+1 through T+45 median fare table
- Total observations
- Cheapest route
- Highest route
- Basket metadata

### overview-page.js

Loads /api/market-overview and renders the all-route page.

## 5. Current Navigation

Home:

- Compute Fare Intelligence -> route.html with query parameters
- Explore all-route market overview -> market-overview.html

The dedicated pages are real HTML pages, not only hidden sections in index.html.

## 6. Current Index Formula

Prototype uses route median fares and provisional equal route weights.

For route item i:

R(i,t) = P(i,t) / P(i,0)

APIx(t) = 100 * [sum(w(i) * R(i,t))] / [sum(w(i))]

Where:

- P(i,t) = current route median fare
- P(i,0) = route median fare in the base period
- w(i) = route weight
- base period index = 100

Current provisional weighting:

- Every route weight is equal to 1.0
- This must be clearly labelled provisional
- Do not claim official DGCA or NSO weighting yet

Current daily index uses collection/observed dates. It must not create fake dates. With only two collection dates, only two daily index points should appear.

## 7. What Must Still Be Built

### A. Government traffic weights

Replace equal route weights with official traffic-based weights.

Needed data:

- Route-wise domestic passenger traffic
- Reporting period
- Passenger counts
- Airport/city mapping
- Any DGCA route classification used

Suggested formula:

route_weight(i) = route_passengers(i) / total_passengers_in_basket

Where to look:

1. Visit https://www.dgca.gov.in/
2. Search for:
   - Domestic passenger traffic route-wise
   - Airport-wise passenger traffic
   - Traffic data domestic air transport
   - Monthly domestic passenger statistics
3. Also check https://data.gov.in/ for DGCA datasets.
4. Download an official CSV/XLS/PDF for a clearly named period.
5. Record:
   - Exact dataset title
   - URL
   - Publication date
   - Reference period
   - Units
   - Route/airport definitions
6. If only airport traffic is available, document the proxy methodology instead of pretending it is route traffic.

Create a local reference file later, for example:

data/dgca_route_weights.csv

Suggested columns:

route,passengers,reference_period,source_url,source_title

Do not add weights until the source and period are documented.

### B. MoSPI CPI comparison

Needed data:

- Official CPI series relevant to transport/communication or air travel
- Monthly values
- Base year
- Series/code/classification
- Reference period

Where to look:

1. Visit https://www.mospi.gov.in/
2. Search for Consumer Price Index datasets and CPI time series.
3. Check https://data.gov.in/ and search:
   - CPI Transport and Communication
   - CPI air transport
   - CPI passenger transport by air
   - CPI urban/rural/combined transport communication
4. Download the official CSV/XLS/API response.
5. Record the exact series name and classification.
6. Do not use a broad transport index as airfare CPI without clearly labelling it as a proxy.

Create a local reference file later, for example:

data/mospi_cpi_reference.csv

Suggested columns:

month,cpi_value,series_name,base_year,frequency,source_url,source_title

Rebase both APIx and CPI before comparing:

RebasedSeries(t) = 100 * Series(t) / Series(base_month)

Monthly APIx aggregation:

APIx(month) = average of daily APIx values in that month

Monthly inflation:

inflation(month) = 100 * [APIx(month) - APIx(previous_month)] / APIx(previous_month)

Year-on-year:

YoY(month) = 100 * [APIx(month) - APIx(month-12)] / APIx(month-12)

Show APIx and CPI as separate labelled series. Do not call APIx official CPI.

### C. Data cleaning pipeline

Add analytical, not destructive, cleaning.

Keep raw values and flags:

- raw_fare
- cleaned_fare
- duplicate_flag
- outlier_flag
- availability
- scrape_status
- cleaning_reason

Recommended rules:

1. Remove invalid/zero total fares from analytical calculations.
2. Deduplicate by source, route, travel date, airline, flight number, and observation.
3. Use median fare for route aggregation.
4. Use IQR outlier detection:

IQR = Q3 - Q1

valid range = [Q1 - 1.5*IQR, Q3 + 1.5*IQR]

5. Keep sold-out/no-result records as status information.
6. Never silently delete raw rows.

### D. Data quality/source health page

Build a dedicated page showing:

- Last scrape run
- Last successful scrape per source
- Rows written per source
- Failed sources
- Missing route/horizon combinations
- Total valid/invalid quotes
- Missing base/tax percentage

### E. Better index page

Add a dedicated index page later with:

- Daily APIx trend
- Weekly APIx
- Monthly APIx
- Horizon selector
- Base period display
- Route coverage
- Weight methodology
- CPI comparison once official data is available

### F. ML/prediction page

Do this only after more daily observations exist.

Minimum useful data:

- Multiple weeks or months of collection dates
- Repeated route/horizon/airline observations
- Holiday/calendar features
- Historical fare volatility

Start with a baseline:

prediction = recent median for same route and horizon

Possible features:

- route
- airline
- source
- advance_days
- day_of_week
- month
- holiday_flag
- recent_median
- recent_volatility
- quote_count

Any prediction line must be clearly labelled forecast/predicted and never mixed with observed fare lines.

### G. API/export

Later add:

- Documented JSON API
- CSV export
- Downloadable index data
- Route/horizon filters
- Source metadata

## 8. Recommended Next Order

1. Verify the new dedicated route and market overview pages manually.
2. Restore/confirm All horizons on route page.
3. Collect official DGCA traffic data and document it.
4. Add data/dgca_route_weights.csv.
5. Replace equal weights with documented route weights.
6. Add data cleaning tables/flags.
7. Build dedicated APIx index page.
8. Obtain and document MoSPI CPI data.
9. Add CPI comparison.
10. Build source health page.
11. Build ML baseline only after enough historical observations exist.
12. Add exports and final dashboard polish.

## 9. Manual Verification

Start the local server from the project directory:

```powershell
python api_server.py
```

Open:

```text
http://127.0.0.1:8000/
```

Home test:

1. Select Delhi (DEL).
2. Select Mumbai (BOM).
3. Select Economy.
4. Select a horizon.
5. Confirm departure date is calculated automatically.
6. Click Input Route.
7. Click Compute Fare Intelligence.
8. Confirm route.html opens.

Market overview test:

1. Return to home.
2. Click Explore all-route market overview.
3. Confirm market-overview.html opens.
4. Confirm all 8 routes and five horizon columns appear.

Useful API checks:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/market-overview"
Invoke-RestMethod "http://127.0.0.1:8000/api/index?advance_days=1"
Invoke-RestMethod "http://127.0.0.1:8000/api/route-horizons?origin=DEL&destination=BOM"
```

## 10. Non-Negotiable Accuracy Rules

- Do not fabricate missing fares.
- Do not fabricate missing airlines or OTAs.
- Do not fabricate tax/base fare breakdowns.
- Do not create fake historical index points.
- Do not claim provisional equal weights are official.
- Do not call APIx official CPI.
- Keep observed and predicted values separate.
- Preserve raw database values.
- Keep scraper changes separate from frontend/API changes.
- Respect robots.txt, terms of service, rate limits, and anti-bot safeguards.
