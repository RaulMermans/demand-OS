# DemandOS — Roadmap

## Phase 1: MVP (Sprints 0–6)

| Sprint | Theme | Key Deliverables |
|--------|-------|-----------------|
| 0 | Scaffold | Monorepo, connectors, schemas, ORM, API skeleton, dashboard shell, tests |
| 1 | Mock Data | Synthetic data generator (50 SKUs × 5 stores × 2 years), ingestion pipeline |
| 2 | Aggregation | Daily sales/inventory aggregation, data health dashboard |
| 3 | Features | Lag + rolling + calendar + promo feature engineering |
| 4 | Forecasting | LightGBM global model, 28-day horizon, prediction intervals |
| 5 | Risk + Reorder | Stockout risk scoring (safety stock, ROP), EOQ recommendations |
| 6 | Evaluation | WRMSSE/SMAPE metrics, model versioning, observability |

**MVP Definition of Done:**
- End-to-end pipeline runs on mock data without manual intervention
- All 6 dashboard pages show live computed data (no placeholders)
- 95% test coverage on pipeline services
- SMAPE < 25% on held-out test set
- Zero hardcoded business metrics in frontend

---

## Phase 2: Real Connectors (Sprints 7–9)

| Sprint | Theme |
|--------|-------|
| 7 | CsvCommerceConnector + Shopify connector |
| 8 | WooCommerce connector + BigCommerce connector |
| 9 | Auth (API keys / OAuth), multi-tenant DB isolation |

---

## Phase 3: Advanced ML (Sprints 10–11)

| Sprint | Theme |
|--------|-------|
| 10 | Hierarchical forecasting (product → category → total), conformal intervals |
| 11 | Optional deep learning (N-BEATS / DLinear via darts), model comparison |

---

## Phase 4: Production Operations (Post-MVP)

- Alerting: Slack / email notifications for critical stockout risks
- Scenario planning: what-if analysis (new promo, supplier delay, demand shock)
- Model monitoring: drift detection, automatic retraining trigger
- Deployment: Vercel (frontend) + Railway/Fly (API) + managed Postgres
- SSO and role-based access control (planners, managers, read-only)
- White-label / multi-tenant SaaS mode

---

## Not On Roadmap (Deliberately)

- Automatic purchase order creation (too risky without human review)
- LLM-based demand prediction (LightGBM outperforms LLMs on structured time-series)
- Blockchain / NFT supply chain (out of scope)
- Consumer-facing demand forecasting (B2B only)
