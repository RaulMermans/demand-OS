# DemandOS Security

See [docs/security.md](docs/security.md) for full security documentation.

## Key Rules

1. No secrets committed to this repository.
2. MVP uses synthetic/mock data only — no real customer data.
3. No automatic purchase orders or supplier API calls.
4. Connector credentials stored in `.env` only (never in DB or logs).
5. All recommendations require human approval before action.
6. Shopify and WooCommerce connectors are disabled stubs with no live API calls.
7. Scenario planning is simulated and non-mutating.
8. Public releases must pass `python scripts/public_readiness_check.py`.

## Reporting Vulnerabilities

Report security issues privately to the project maintainer.
Do not open public GitHub issues for security vulnerabilities.
