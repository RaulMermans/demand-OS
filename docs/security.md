# DemandOS — Security

## Secrets

- No secrets, API keys, or credentials are committed to this repository.
- All secrets are stored in `.env` files (gitignored) or a secrets manager (prod).
- `.env.example` shows variable names only, never real values.
- GitHub Actions / CI never logs secret values.

## Mock Data Only (MVP)

- The MVP uses synthetic/mock data only. No real customer data is processed.
- No personal data, order data, or financial data from real individuals is stored.
- See DATA_POLICY.md for full data policy.

## Connector Credentials (Sprint 3+)

- Shopify access tokens stored as environment variables only.
- Credentials are never stored in the database or logged.
- Each connector validates credential presence at initialization, not at import time.
- Credentials are scoped to minimum permissions required (read-only access to orders and inventory).

## No Automatic Purchases

- DemandOS computes reorder recommendations only.
- No automatic purchase orders, emails, or API calls to suppliers are made.
- All recommendations require explicit human approval before any action is taken.

## API Security (Sprint 7)

- All API endpoints will require authentication (API key or JWT).
- CORS is restricted to known frontend origins.
- Rate limiting on ingestion endpoints.
- Input validation via Pydantic on all request bodies.

## Data Minimization

- Raw records store `raw_payload` (original JSON) for debugging only.
- In production, consider stripping PII from `raw_payload` before storage.
- Log records by ID and count only; never log raw record field values.

## Dependency Security

- Dependencies pinned in pyproject.toml and package.json.
- `pip audit` and `npm audit` run in CI (Sprint 7).
- No transitive dependency on packages with known CVEs at time of install.

## Vulnerability Reporting

Report security issues to the project maintainer via private email.
Do not open public GitHub issues for security vulnerabilities.
