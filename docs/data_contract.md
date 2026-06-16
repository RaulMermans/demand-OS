# DemandOS — Data Contract

## Principle: Raw Data Only

Connectors must supply only raw operational records.
The pipeline computes all derived values.

**Connectors MAY supply:**
- Product identifiers, names, categories, costs, prices, lead times
- Store identifiers, regions, channels
- Order line items: product, store, timestamp, quantity, price, status
- Inventory snapshots: product, store, date, quantity on hand/on order
- Promotion definitions: date range, discount %, applicable SKUs
- Supplier info: lead times, reliability scores (as-measured, not modeled)
- Purchase orders: product, supplier, quantity, status, expected delivery

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

## Raw Schema Field Guard

`apps/api/app/schemas/raw.py` defines `FORBIDDEN_DERIVED_FIELDS`.
`tests/test_raw_data_rule.py` enforces this automatically via pytest.

## Source Connector Field

Every raw record carries `source_connector: str` identifying its origin.
This enables:
- Audit trails for every data point
- Multi-connector data merging
- Debugging data quality issues by source

## Accepted Data Formats

| Source | Format | Sprint |
|--------|--------|--------|
| MockCommerceConnector | Python objects (generated) | 1 |
| CsvCommerceConnector | CSV files in data/sample_uploads/ | 2 |
| ShopifyConnector | Shopify Admin REST API | 3 |
| WooCommerceConnector | WooCommerce REST API | 4 |
| ERPConnector | TBD | 5+ |

## Schema Versioning

Raw schemas are versioned via `source_connector` and `ingested_at`.
`raw_payload` stores the original record as JSON for replay/debugging.
