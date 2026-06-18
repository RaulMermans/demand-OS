# DemandOS — Data Contract

## Principle: Raw Data Only

Connectors must supply only raw operational records.
The pipeline computes all derived values.

**Connectors MAY supply:**
- Product identifiers, names, categories, costs, prices, lead times, brand, tier attributes
- Store identifiers, regions, channels, timezones
- Order line items: product, store, timestamp, quantity, price, discount, currency, status
- Inventory snapshots: product, store, date, quantity on hand / on order / reserved
- Promotion definitions: date range, discount %, type, applicable SKUs/stores
- Supplier info: lead times, reliability scores (as-measured, not modeled)
- Purchase orders: product, supplier, store, quantity, status, expected delivery

**Connectors MUST NOT supply:**
- Lag features (lag_7d, lag_14d, lag_28d)
- Rolling window statistics (rolling_mean_*, rolling_std_*)
- Forecasts or predicted units
- Risk scores or stockout probabilities
- Days-until-stockout calculations
- Reorder recommendations or EOQ values
- Safety stock levels
- Demand signals derived from model outputs
- Anomaly flags computed by ML models
- Internal simulation state (latent demand, reorder thresholds)

## Raw Schema Field Guard

`apps/api/app/schemas/raw.py` defines `FORBIDDEN_DERIVED_FIELDS`.
`tests/test_raw_data_rule.py` enforces this automatically via pytest.

## Source Connector Field

Every raw record carries `source_connector: str` identifying its origin.
This enables:
- Audit trails for every data point
- Multi-connector data merging
- Debugging data quality issues by source

## Canonical Daily Tables (Sprint 2)

Produced by `AggregationService.run_full_aggregation(start_date, end_date)`.
These tables are the input to Sprint 3 FeatureService — never to connectors.

| Table | Key | Key fields |
|-------|-----|-----------|
| `sales_daily` | (product_id, store_id, date) | units_sold, net_revenue, discount_amount, order_count, promotion_active |
| `inventory_daily` | (product_id, store_id, date) | on_hand_units, on_order_units, inbound_units, stockout_flag, days_of_supply |
| `promotion_daily` | (product_id, store_id, date) | is_active, promotion_id, discount_pct |
| `product_store_daily` | (product_id, store_id, date) | full denormalized join of above + sku, category, channel |

**Cleaning rules:**
- `sales_daily`: only `fulfilled` orders count; `cancelled` and `returned` are excluded
- `inventory_daily`: multiple snapshots for (product, store, date) → latest `ingested_at` wins
- `days_of_supply = on_hand / (sum_units_last_7d / 7)` — NULL when no recent demand
- Promotion active when `start_date ≤ date ≤ end_date`, SKU and store constraints satisfied; highest `discount_pct` wins on overlap

**Idempotency:** The service deletes [start_date, end_date] rows before reinserting.

**Forbidden fields in canonical tables** (enforced by `test_aggregation.py`):
`lag_7d`, `lag_14d`, `lag_28d`, `rolling_mean_28d`, `forecast`, `forecast_7d`,
`risk_score`, `stockout_risk`, `recommended_units`, `reorder_quantity`, `target`, `future_demand`

## Feature Matrix (Sprint 3)

Produced by `FeatureService.build_feature_matrix()`. Input: `product_store_daily`. Output: `feature_matrix`.

**Key (product_id, store_id, date)** — one row per eligible day (pre-launch rows excluded).

| Feature group | Columns |
|--------------|---------|
| Target | `target_units_sold` (historical label; NOT a forecast) |
| Lag | `lag_units_1d`, `lag_units_7d`, `lag_units_14d`, `lag_units_28d` |
| Rolling mean | `rolling_units_mean_7d/14d/28d`, `rolling_revenue_mean_7d/28d` |
| Rolling std | `rolling_units_std_7d`, `rolling_units_std_28d` |
| Calendar | `day_of_week` (0=Mon), `week_of_year`, `month`, `quarter`, `is_weekend` |
| Promotion | `promo_active`, `discount_pct` |
| Price/margin | `retail_price`, `unit_cost`, `gross_margin_pct`, `price_change_pct_7d/28d` |
| Inventory | `available_units`, `stockout_flag`, `days_of_supply` |
| Lifecycle | `days_since_launch`, `product_age_bucket` |
| Metadata | `category`, `store_channel`, `supplier_id`, `source_aggregation_run_id`, `feature_run_id` |

**Leakage-safety rules:**
- All lag and rolling features use dates **strictly before D** (shift=1 applied before rolling)
- Rolling window of width W at date D covers [D-W .. D-1], computed via `x.shift(1).rolling(W, min_periods=1).mean()`
- Pre-launch rows (`days_since_launch < 0`) are **excluded** from feature_matrix entirely
- `target_units_sold` is the historical units for D — the supervised learning label

**Forbidden columns** (enforced by `test_features.py::test_no_forbidden_fields_in_feature_matrix_schema`):
`forecast`, `forecast_7d`, `forecast_28d`, `forecast_90d`, `p10`, `p50`, `p90`,
`risk_score`, `stockout_risk`, `recommended_units`, `reorder_quantity`, `future_demand`, `future_units_sold`

**Idempotency:** Full rebuild — DELETE ALL rows, then reinsert. Unlike aggregation (date-range delete), features
always rebuild completely because lag/rolling depend on full history.

**Product age buckets:**
- `new_0_30`: days_since_launch ≤ 30
- `ramp_31_90`: 31–90
- `mature_91_365`: 91–365
- `established_365_plus`: > 365

## Forecast Tables (Sprint 4)

Produced by `ForecastingService.run_baseline_forecast()`. Input: `feature_matrix`. Output: `forecast_runs`, `forecasts`, `model_metrics`.

### forecast_runs
One row per forecast run.

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Primary key (`forecast-run-<uuid>`) |
| `model_name` | String | Model identifier (same as model_type for baselines) |
| `model_type` | String | `seasonal_naive` / `moving_average_7d` / `moving_average_28d` |
| `horizon_days` | Int | Intended forecast horizon (default 28) |
| `backtest_mode` | Bool | True for Sprint 4 (all runs are backtests) |
| `train_start_date` | Date | Earliest date in feature_matrix (informational) |
| `train_end_date` | Date | Day before test window starts |
| `test_start_date` | Date | max_date − backtest_days + 1 |
| `test_end_date` | Date | max_date in feature_matrix |
| `status` | String | `running` / `completed` / `failed` |
| `rows_created` | Int | Number of Forecast rows written |
| `config_json` | JSON | backtest_days, source_feature_run_id |

### forecasts
One row per (run_id × forecast_date × product_id × store_id).

| Field | Type | Description |
|-------|------|-------------|
| `p50_units` | Float | Point forecast (required) |
| `p10_units` | Float | Lower band: max(0, p50 − σ) — heuristic only |
| `p90_units` | Float | Upper band: p50 + σ — heuristic only |
| `actual_units` | Float | Historical actuals joined for backtest evaluation |
| `absolute_error` | Float | `|actual − p50|` |
| `squared_error` | Float | `(actual − p50)²` |
| `absolute_percentage_error` | Float | SMAPE per-row: `2·|f−a|/(|a|+|f|)`; 0 when denominator=0 |

**p10/p90 bands** are computed as p50 ± 1 standard deviation of recent demand (rolling_units_std_7d or std_28d). These are uncertainty heuristics. Coverage guarantees are not provided for baseline models.

### model_metrics
One row per (run_id × level × level_value).

| Field | Type | Description |
|-------|------|-------------|
| `level` | String | `overall` / `category` / `store` |
| `level_value` | String | `"all"` for overall; category name / store_id otherwise |
| `mae` | Float | Mean Absolute Error |
| `rmse` | Float | Root Mean Squared Error |
| `wape` | Float | Weighted APE = sum(|a-f|)/sum(a); **None** when sum(actual)=0 |
| `smape` | Float | Mean symmetric APE; zero-denominator rows contribute 0 |
| `bias` | Float | (sum(f)−sum(a))/sum(a); **None** when sum(actual)=0 |

**Idempotency:** Re-running the same model_type deletes the prior run, forecasts, and metrics before writing new ones (clear-before-rewrite).

**Forbidden fields in forecast tables:**
`stockout_probability`, `days_until_stockout`, `risk_tier`, `recommended_qty`, `reorder_point`, `economic_order_qty`

## Model Registry (Sprint 5)

Produced by `TrainingService.train_ml_forecaster()`. Input: `feature_matrix`. Output: `model_versions`, `forecast_runs`, `forecasts`, `model_metrics`.

### model_versions
One row per trained model version.

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Primary key (`model-<uuid>`) |
| `model_name` | String | Display name |
| `algorithm` | String | `hist_gradient_boosting` / `seasonal_naive` / etc. |
| `model_type` | String | `ml_global_regressor` / `baseline` |
| `status` | String | `running` / `completed` / `failed` |
| `training_start_date` | Date | Earliest training date |
| `training_end_date` | Date | Last training date (day before test window) |
| `test_start_date` | Date | First test date |
| `test_end_date` | Date | Last test date |
| `feature_columns_json` | JSON | List of input feature column names |
| `target_column` | String | `target_units_sold` |
| `artifact_path` | String | Path to saved .joblib artifact |
| `metrics_summary_json` | JSON | Overall/category/store metrics |
| `config_json` | JSON | Training hyperparameters |

**Artifact format** (`models/forecasting/{model_version_id}.joblib`):
```python
{
    "model": HistGradientBoostingRegressor,  # fitted
    "encoder": OrdinalEncoder,               # fitted on training categoricals
    "numeric_columns": [...],                 # 27 numeric feature names
    "categorical_columns": [...],             # 3 categorical feature names
    "feature_columns": [...],                 # all 30 feature names
    "trained_at": "2024-01-01T00:00:00",
}
```

**Categorical encoding:**
- OrdinalEncoder with categories sorted alphabetically from training set
- Unseen values at inference → encoded as -1 (unknown)
- Columns: category, store_channel, product_age_bucket

**Idempotency:** Re-running same algorithm deletes prior run (clear-before-rewrite).

**Generated artifacts are excluded from git via `.gitignore`.**

## Accepted Data Formats

| Source | Format | Sprint |
|--------|--------|--------|
| MockCommerceConnector | Python objects (generated) | 1 ✅ |
| CsvCommerceConnector | CSV files in data/sample_uploads/ | 2 |
| ShopifyConnector | Shopify Admin REST API | 3 |
| WooCommerceConnector | WooCommerce REST API | 4 |
| ERPConnector | TBD | 5+ |

## MockCommerceConnector (Sprint 1)

**Default generation config** (seed=42):
- 50 products × 5 categories (Tops, Bottoms, Footwear, Accessories, Outerwear)
- 3 tiers: bestseller (20%), standard (60%), slow_mover (20%)
- 5 stores/channels (Online, Madrid Flagship, Barcelona Store, Outlet, Wholesale)
- 10 suppliers with lead times 6–45 days and reliability 0.82–0.99
- 730 days of history with weekday + monthly seasonal patterns
- ~11 promotion templates per year (New Year, Valentine's, Spring, Summer, Black Friday, etc.)
- Daily inventory snapshots with realistic stockout events
- Purchase orders triggered by internal reorder logic (not a derived field)

**Temporal patterns:**
- Day-of-week multipliers: Mon 0.9×, Fri/Sat 1.3–1.4×, Sun 0.7×
- Monthly multipliers: Dec 2.0×, Nov 1.5×, Jul 1.3×, Jan 0.7×
- Promotion uplift: 1.45× (10% off) to 2.57× (35% off)
- Wholesale store gets bulk order lines; online/retail get individual transactions

**Internal simulation state (NOT persisted):**
- Latent demand per product/store/day (Poisson-sampled, capped by stock)
- Running stock levels
- Reorder point thresholds
- In-transit PO tracking

## Schema Versioning

Raw schemas are versioned via `source_connector` and `ingested_at`.
`raw_payload` stores the original record as JSON for replay/debugging.
