# ML Implementation Plan for UDAANKOSH

## Goal

Move from the current recent-median baseline to a real machine-learning fare prediction workflow only when the data quality and historical depth requirements are satisfied.

## Current project state

- The app already has live route, horizon, market overview, source health, APIx, CPI, and baseline forecast functionality.
- The forecast page currently uses a recent-median baseline and clearly labels it as a forecast.
- The project is ready for a structured ML transition plan, but should not begin full model training until the readiness checklist thresholds are met.

## Phase 0: Freeze the baseline and set monitoring

### Deliverables

- Keep the recent-median baseline as the production fallback.
- Define a baseline comparator for all future ML experiments.
- Log base metrics and data coverage every day.

### Tasks

1. Lock the current baseline endpoint as the default fallback for all route/horizon predictions.
2. Add a simple daily monitoring job that records:
   - total raw rows
   - route coverage
   - source coverage
   - duplicate rate
   - invalid fare rate
   - outlier rate
3. Define a target: the model must beat baseline on a held-out validation slice.

### Exit criteria

- Baseline endpoint remains stable.
- Daily data quality stats are available in one place.
- Each new training cycle can compare against the baseline.

## Phase 1: Data readiness and quality gates

### Deliverables

- Clean, consistent raw quote dataset
- A documented schema for training data
- Data quality checks that block bad training runs

### Tasks

1. Keep raw flight table as the source of truth.
2. Add a data-quality validation job that checks:
   - duplicate row count
   - invalid or non-positive fares
   - missing required fields
   - outlier severity by route and horizon
   - source completeness issues
3. Create a quarantine workflow for rows failing quality checks.
4. Store a curated training dataset view with only validated rows.

### Recommended training schema

Required fields:

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

Derived features to generate:

- route
- route_horizon_key
- day_of_week
- week_of_year
- month
- holiday_flag
- rolling_median_by_route_horizon
- rolling_volatility_by_route_horizon
- source_confidence
- price_gap_to_route_median
- quote_count

### Exit criteria

- Duplicate rate is near zero.
- Invalid and non-positive fares are removed or flagged.
- A clean training view has been created and validated.

## Phase 2: Feature engineering and dataset split design

### Deliverables

- A reusable feature generation module
- Date-aware train/validation/test splits
- Stable feature definitions for each route and horizon

### Tasks

1. Build feature engineering for:
   - route and airline embeddings or category encoding
   - rolling historical fare statistics
   - calendar features
   - recent volatility
   - source quality signals
2. Split data by time, not randomly.
3. Use a backtesting approach such as:
   - train on earlier periods
   - validate on the next recent period
   - test on the most recent window
4. Keep the baseline median available as a benchmark feature in all experiments.

### Suggested split logic

- Train: earliest 60% of dates
- Validation: next 20%
- Test: final 20%

For repeated retraining, use rolling windows so the model always learns from recent history.

### Exit criteria

- Features are reproducible.
- No leakage exists between train and validation/test.
- Baseline and ML experiments are evaluated on the same split.

## Phase 3: Model candidates and benchmarking

### Deliverables

- At least two candidate models
- Benchmark report vs baseline
- Model selection criteria

### Recommended first candidates

1. CatBoost Regressor
   - strong on mixed categorical + numeric data
   - good default starting point for airfare prediction
2. LightGBM Regressor
   - efficient and robust on tabular data
   - fast retraining cycles
3. XGBoost Regressor
   - strong baseline tree model
   - useful comparison point

### Benchmark metrics

- MAE
- RMSE
- MAPE
- median absolute error
- improvement over recent-median baseline

### Exit criteria

- A candidate model clearly beats the baseline on validation data.
- Training and inference are reproducible.
- Model scorecards are recorded for each experiment.

## Phase 4: API and UI integration

### Deliverables

- Model-backed forecast endpoint
- Clear UI labeling for predicted values
- Safe fallback to baseline when model confidence is low

### Tasks

1. Add a model-backed forecast endpoint next to the current baseline endpoint.
2. Keep the current baseline response available as a fallback.
3. Add UI labels such as:
   - Model forecast
   - Baseline forecast
   - Confidence / quality note
4. If a model is unavailable or coverage is poor, automatically revert to the baseline.

### Exit criteria

- Forecast page distinguishes baseline and ML predictions clearly.
- Users can see when the app is using fallback logic.
- API responses stay stable and documented.

## Phase 5: Monitoring, retraining, and governance

### Deliverables

- Scheduled retraining pipeline
- Performance monitoring
- Drift detection and retraining triggers

### Tasks

1. Add scheduled retraining on a fixed cadence, for example weekly or monthly.
2. Record evaluation metrics for each retrain.
3. Monitor for:
   - rising error
   - source drift
   - route coverage changes
   - holiday-related anomalies
4. Maintain model registry metadata:
   - training date
   - dataset version
   - feature version
   - validation score
   - fallback status

### Exit criteria

- The system can retrain without manual data cleanup.
- Performance drift is visible.
- Low-confidence predictions automatically fall back to baseline.

## Practical rollout timeline

### Milestone 1: Data readiness

- historical depth reaches required range
- source coverage stabilizes
- quality checks pass reliably

### Milestone 2: Benchmarking

- baseline and candidate models compare on the same date split
- one model consistently outperforms baseline

### Milestone 3: Production model

- model API is deployed
- UI is updated with clear labels
- fallback and monitoring are live

## Recommended next action now

Continue collecting and validating data until the dataset reaches the readiness thresholds. At that point, move to a formal ML branch with:

1. curated training data generation
2. feature-store ready schema
3. candidate model benchmarking
4. a monitored production forecast endpoint

## Final recommendation

Do not start a full ML rollout yet. The current recent-median baseline is the correct production choice until the project has enough historical data, stable coverage, and verified quality gates. Once that is true, the implementation plan above gives a clear path to move from baseline forecasting to a real ML system.
