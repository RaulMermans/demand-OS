# DemandOS — Product Definition

## What is DemandOS?

DemandOS is a demand forecasting and inventory risk platform for e-commerce and omnichannel retailers.

It answers three operational questions:
1. **How much will I sell?** — 28-day demand forecasts per SKU per store/channel
2. **What will run out?** — Stockout risk scores with days-until-stockout
3. **What should I order?** — Reorder recommendations with EOQ and supplier selection

## Target Users

- Inventory planners at mid-market e-commerce brands (€1M–€50M revenue)
- Operations managers at omnichannel retailers
- Supply chain analysts at brands with 50–2,000 active SKUs

## MVP Scope

MVP uses synthetic mock data to demonstrate the full platform workflow.
Real connector integrations (Shopify, WooCommerce, ERP) are added in later sprints.

### In MVP:
- Full pipeline: raw data → forecast → stockout risk → reorder recommendation
- Dashboard with 6 views
- REST API for all outputs
- Synthetic e-commerce dataset (50 SKUs × 5 stores × 2 years)

### Out of MVP:
- Real Shopify/WooCommerce/ERP integration
- Authentication and multi-tenancy
- Automated purchase order creation
- Email/Slack alerting
- Scenario planning (what-if analysis)

## Non-Negotiable Rules

1. DemandOS ingests raw operational records; it never accepts precomputed features as input.
2. All forecasts, risk scores, and recommendations are computed by the pipeline.
3. No automatic purchase orders — recommendations are human-approved.
4. No hardcoded business metrics in the dashboard.

## Connector Roadmap

| Connector | Data Source | Sprint |
|-----------|------------|--------|
| MockCommerceConnector | Synthetic generator | 1 |
| CsvCommerceConnector | CSV file upload | 2 |
| ShopifyConnector | Shopify Admin REST API | 3 |
| WooCommerceConnector | WooCommerce REST API | 4 |
| BigCommerceConnector | BigCommerce API | 5 |
| ERPConnector | Generic ERP (TBD) | 6+ |
