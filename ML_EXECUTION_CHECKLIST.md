# ML Execution Checklist for UDAANKOSH

## Immediate next objective

Start the first practical ML-prep phase by building a reliable data readiness and quality baseline. Do not begin model training until this checklist is green.

## Step 1 — Data readiness scorecard

### Goal

Create a single, repeatable snapshot of the current dataset quality and coverage.

### Tasks

1. Count total raw quote rows in `raw_fare_quotes`.
2. Count rows per source, route, and horizon.
3. Record route-horizon coverage completeness.
4. Record duplicate row count, invalid fare count, and outlier count.
5. Store the results in a simple JSON or CSV summary for daily review.

### Output

- `data_readiness_summary.json`
- daily coverage metrics in a machine-readable format

### Acceptance criteria

- summary can be generated automatically
- route coverage percentages are visible
- source coverage percentages are visible
- duplicate / invalid / outlier counts are visible

## Step 2 — Training data quality gate

### Goal

Define a clean training slice that is safe to use for future model experiments.

### Tasks

1. Build a filtered dataset containing only valid quotes.
2. Exclude rows with missing required fields.
3. Exclude non-positive or malformed fares.
4. Mark outliers separately rather than deleting them silently.
5. Create a curated `training_ready` view or export.

### Output

- `training_ready.csv` or equivalent SQL view
- quarantine log for excluded rows

### Acceptance criteria

- each row has required schema fields
- invalid rows are logged separately
- training slice is reproducible

## Step 3 — Feature engineering design

### Goal

Prepare the feature set needed for the first real model benchmark.

### Tasks

1. Add route, airline, source, horizon, day-of-week, month, holiday flags.
2. Add rolling median and rolling volatility by route + horizon.
3. Add recent quote-count and source confidence indicators.
4. Generate a feature dictionary version number.

### Output

- feature schema document
- generated feature dataset preview

### Acceptance criteria

- features are documented
- features are reproducible
- no future leakage is present in feature generation

## Step 4 — Benchmark against the baseline

### Goal

Prove that any model is better than the current recent-median baseline.

### Tasks

1. Keep the recent-median baseline endpoint as the benchmark.
2. Train a first candidate model on the curated training slice.
3. Evaluate on a held-out recent date range.
4. Compare MAE, RMSE, and MAPE against the baseline.

### Output

- benchmark evaluation report
- model scorecard

### Acceptance criteria

- model is evaluated on the same time split as baseline
- leaderboard clearly shows improvement vs baseline
- benchmark result is stored for comparison

## Step 5 — Model API and UI handoff

### Goal

Prepare the product layer for the first real ML model.

### Tasks

1. Add a model-backed forecast endpoint beside the baseline endpoint.
2. Keep baseline as fallback when confidence is low.
3. Update UI labels to distinguish baseline vs ML-predicted values.
4. Add a confidence/status indicator for predictions.

### Output

- `api/model-forecast`
- UI status text for model usage

### Acceptance criteria

- users can see whether the result is baseline or model-based
- API remains backward-compatible
- fallback works safely

## Step 6 — Monitoring and retraining

### Goal

Make the ML system sustainable after launch.

### Tasks

1. Add weekly or monthly retraining.
2. Monitor drift in route coverage, source quality, and error metrics.
3. Trigger retraining when coverage or error thresholds degrade.
4. Keep a model registry with version, score, and training date.

### Output

- retraining scheduler
- monitoring dashboard or summary
- model metadata registry

### Acceptance criteria

- retraining is automated
- model performance is tracked over time
- weak models revert to baseline automatically

## Recommended execution order

1. Data readiness scorecard
2. Training data quality gate
3. Feature engineering design
4. Baseline benchmark
5. Model API/UI handoff
6. Monitoring and retraining

## Current recommendation

Do not jump into full ML training yet. First complete Steps 1 and 2, because they determine whether the data is mature enough for any meaningful model work.
