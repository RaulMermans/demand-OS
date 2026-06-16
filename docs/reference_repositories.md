# DemandOS — Reference Repositories

These external repositories guide DemandOS architecture and algorithms.
They are references and inspiration — not dependencies to blindly copy.

---

## 1. Nixtla/mlforecast

**Role in DemandOS:** Forecasting feature engineering, global ML forecasting architecture,
walk-forward cross-validation, prediction intervals.

**Key patterns adopted:**
- Global ML model: train one LightGBM across all (product, store) series simultaneously
  rather than one model per SKU. Avoids sparse-data problems for low-volume SKUs.
- Lag and rolling-window feature engineering pattern (lag_7d, lag_14d, lag_28d,
  rolling_mean_7d, rolling_mean_14d, rolling_mean_28d, rolling_std_7d)
- Walk-forward cross-validation with expanding window
- Quantile regression for prediction intervals (q=0.1, q=0.9)

**Usage note:** DemandOS implements its own FeatureService and ForecastingService.
The mlforecast library may be used as a dependency in Sprint 4+ if it reduces
boilerplate without violating the raw-data-only rule.

**License check required before use.**

---

## 2. Mcompetitions/M5-methods

**Role in DemandOS:** Retail demand forecasting discipline, 28-day forecast horizon,
M5 competition methodology, WRMSSE metric definition.

**Key patterns adopted:**
- 28-day forecast horizon (standard for retail inventory planning)
- WRMSSE (Weighted Root Mean Squared Scaled Error) as primary accuracy metric
- Hierarchical evaluation: aggregate + product-level + store-level accuracy
- Treatment of zero-demand days (zero padding, not NaN)

**Usage note:** DemandOS does not use M5 competition code directly. The evaluation
methodology (WRMSSE, 28-day horizon) and data discipline (no target leakage, strict
train/validation/test splits) are the key adoptions.

**License check required before use.**

---

## 3. G-Schumacher44/ecom_sales_data_generator

**Role in DemandOS:** Realistic synthetic relational e-commerce data patterns for Sprint 1
MockCommerceConnector implementation.

**Key patterns adopted:**
- Relational schema: products → stores → orders → inventory snapshots → promotions
- Temporal demand patterns: weekday effects, seasonal peaks, promotional lifts
- Product category structure (electronics, apparel, home, etc.)
- Multi-store / multi-channel data generation

**Usage note:** DemandOS's MockCommerceConnector must generate raw operational records
only — no precomputed features. Any synthetic data generation patterns adopted from this
reference must not produce lag features, rolling windows, or forecast values as output.

**The raw-data-only rule overrides all reference patterns.**

**License check required before use.**

---

## 4. virbahu/inventory-optimization

**Role in DemandOS:** Safety stock, reorder point, EOQ, and stockout/inventory planning
formulas for StockoutService and RecommendationService.

**Key formulas adopted:**

```
Safety stock = Z × σ(daily_demand) × √(lead_time_days)
  Z = service level z-score (e.g. 1.65 for 95% service level)
  σ = standard deviation of daily demand over lookback window

Reorder Point (ROP) = avg_daily_demand × lead_time_days + safety_stock

Economic Order Quantity (EOQ) = sqrt(2 × D × S / H)
  D = annual demand (units)
  S = ordering cost per order (fixed)
  H = holding cost per unit per year

Days Until Stockout = quantity_on_hand / avg_daily_demand
```

**Usage note:** DemandOS implements its own StockoutService and RecommendationService.
These formulas are the algorithmic reference; the implementation is DemandOS-native.

**License check required before use.**

---

## 5. unit8co/darts

**Role in DemandOS:** Optional later reference for model comparison and broader
time-series tooling (Sprint 7+).

**Key patterns considered:**
- N-BEATS, DLinear, TiDE deep learning models for time-series
- Unified forecasting API across model families
- Backtesting and metric utilities

**Usage note:** Darts is a heavier dependency. Only adopt if LightGBM baseline
underperforms and deep learning provides meaningful lift on held-out test set.
Do not introduce as a dependency until Sprint 7 decision point.

**License check required before use.**

---

## Usage Rules

1. These are references and inspiration, not drop-in dependencies.
2. Do not blindly copy code from any of these repositories.
3. Check licenses before using any code directly (MIT, Apache 2.0, etc.).
4. Prefer implementing DemandOS-native modules unless a dependency provides
   unambiguous, tested value.
5. **The raw-data-only rule overrides all reference patterns.**
   If a reference library assumes precomputed features as input, adapt the pattern
   to fit DemandOS's connector-based ingestion model instead.
