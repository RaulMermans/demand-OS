# DemandOS Roadmap

See [docs/roadmap.md](docs/roadmap.md) for the full roadmap with details.

## Quick Summary

| Sprint | Theme | Status |
|--------|-------|--------|
| 0 | Scaffold | ✅ Done |
| 1 | Mock data generator | 🔜 Next |
| 2 | Aggregation pipeline | 🔜 |
| 3 | Feature engineering | 🔜 |
| 4 | LightGBM forecasting | 🔜 |
| 5 | Stockout risk + EOQ reorder | 🔜 |
| 6 | Model evaluation + observability | 🔜 |
| 7 | CSV + Shopify connectors | 🔜 |
| 8 | WooCommerce + BigCommerce connectors | 🔜 |
| 9 | Auth + multi-tenant | 🔜 |
| 10 | Hierarchical forecasting | 🔜 |
| 11 | Deep learning (optional) | 🔜 |

## MVP Definition of Done

- [ ] Full pipeline runs on mock data end-to-end without errors
- [ ] All 6 dashboard routes show live computed data (no placeholders)
- [ ] No hardcoded business metrics in frontend
- [ ] SMAPE < 25% on held-out test set
- [ ] WRMSSE logged per model version
- [ ] 95%+ test coverage on pipeline services
- [ ] docker-compose up starts everything
- [ ] scripts/verify.sh passes
