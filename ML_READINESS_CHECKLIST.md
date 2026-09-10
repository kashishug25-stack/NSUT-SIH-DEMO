# ML Readiness Checklist for UDAANKOSH

## Current status

The project is currently in the baseline phase:

- The live app already provides route and horizon analysis.
- The forecast page uses a recent-median baseline estimate.
- This is useful for demo and internal review, but it is not yet a machine-learning prediction system.

## When to move from baseline to ML

Move to a real ML workflow only after the following conditions are met:

### 1. Historical data depth

- At least 8 to 12 weeks of daily/near-daily observations.
- Repeated route × horizon × airline combinations across multiple collection dates.
- Enough repeated examples to learn patterns such as day-of-week effects, month effects, and route volatility.

### 2. Coverage quality

- At least 80% route-horizon coverage across the main eight routes.
- No major gaps in the key advance windows: T+1, T+7, T+15, T+30, T+45.
- Source coverage should be stable enough that the same route-horizon combinations are observable over time.

### 3. Reliable raw quote data

- Raw flight rows should continue to contain:
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
  - observed_at
  - scrape_status
- Missing base fare or taxes should be tracked and documented, not silently ignored.

### 4. Data quality gates

Before model training begins, the dataset should pass these checks:

- Duplicate quote rows reduced to near zero.
- Invalid or non-positive fares removed or quarantined.
- Outliers reviewed and either cleaned or flagged.
- Data splits defined by date, not random row order.

## Recommended feature set for ML

Once the dataset is sufficient, the following features should be prepared:

### Core features

- route
- origin
- destination
- airline
- source
- cabin
- advance_days
- day_of_week
- week_of_year
- month
- observed_date
- holiday_flag
- recent_median
- recent_volatility
- quote_count

### Derived features

- rolling median fare by route and horizon
- rolling volatility by route and horizon
- day-of-week average premium/discount
- route-specific seasonality index
- source confidence score
- price gap vs route median

## Recommended ML workflow

### Phase A: Baseline remains the default

- Keep the current recent-median baseline as the production fallback.
- Use it whenever historical data is too sparse or when quality checks fail.

### Phase B: Structured model training

- Train on a rolling window of recent data.
- Validate on the next time slice.
- Use date-based split logic so no future leakage occurs.

### Phase C: Ensemble or tree-based modeling

Good first candidates:

- CatBoost
- XGBoost
- LightGBM
- Random Forest / Gradient Boosted Trees

These models handle mixed categorical and numerical signals well and are often a strong first step for airfare prediction.

### Phase D: Model monitoring

- Track MAE, RMSE, and MAPE.
- Compare model predictions against the baseline.
- Monitor coverage drift and source drift.
- Flag when performance drops below baseline for a sustained period.

## Success criteria

The ML phase should only begin when the following are true:

- live data availability is consistent
- quality checks are stable
- route-horizon coverage is strong
- baseline performance is well understood
- a proper train/validation/test split exists
- evaluation metrics are defined before model deployment

## Suggested next step

Keep the current baseline page as the official forecast while the team continues collecting data. Once the dataset reaches the thresholds above, move to a structured ML pipeline with:

1. feature engineering from raw flight quotes
2. date-based model evaluation
3. benchmark comparison vs the recent median baseline
4. a monitored model deployment stage

## Practical recommendation

Do not start true ML yet unless the project already has enough daily observations to make the model meaningfully better than the current baseline. Until then, the best production choice is the current recent-median baseline plus strong data-quality monitoring.
