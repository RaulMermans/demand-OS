# DemandOS — Case Study Notes

## Target Use Case: Mid-Market E-Commerce Brand

**Profile:**
- 200–500 active SKUs
- 2–5 sales channels (own website, Amazon, wholesale)
- €2M–€20M annual revenue
- Inventory planning done manually in spreadsheets
- Stockouts cost 5–15% of potential revenue annually
- Overstock ties up 20–40% of working capital

**Pain points addressed by DemandOS:**
1. No systematic demand forecasting — planners rely on gut feel and prior-year sales
2. Stockout detection is reactive (customer complaints, out-of-stock notices)
3. Reorder decisions don't account for supplier lead time variability
4. Promotional demand lifts are not modeled — post-promo crash is frequently missed
5. No visibility into which SKUs are highest risk at any given time

**Expected outcomes:**
- 20–30% reduction in stockout events (measured by stockout days / total days)
- 10–15% reduction in overstock inventory value
- Planner time savings: 4–8 hours/week from manual spreadsheet work

## Validation Scenarios (for Demo)

### Scenario A — Pre-Christmas Stockout
- High-demand SKU sells out 14 days before Christmas
- DemandOS should flag as critical risk 21 days prior (within lead time window)
- Recommendation: reorder at T-35 days

### Scenario B — Post-Promotion Crash
- Flash sale drives 5× normal demand for 3 days
- Post-promo demand drops 40% for 7 days
- DemandOS forecast should reflect both the lift and the crash
- Inventory planning should not over-order based on promo-inflated baseline

### Scenario C — Slow-Mover with Long Lead Time
- Low-volume SKU, 45-day supplier lead time
- Days-of-supply calculation shows stockout risk in 30 days
- Traditional reorder-point systems miss this (designed for fast-movers)
- DemandOS EOQ + ROP flags this correctly

## Competitive Landscape Notes

- **Inventory Planner (Shopify app)**: simple reorder alerts, no ML forecasting
- **Flieber**: demand forecasting for Amazon sellers, no multi-channel
- **Streamline by Intuendi**: full planning suite, priced for enterprise
- **DemandOS differentiation**: open-core, connector-first, ML-native, developer-friendly

These notes are for product context only. No competitive analysis for marketing purposes.
