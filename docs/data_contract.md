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
