# data/

This directory holds local data files for DemandOS.

## Structure

```
data/
├── raw/              — Raw ingested records (CSV exports, JSON dumps)
├── processed/        — Intermediate processed files (if needed outside DB)
└── sample_uploads/   — Sample CSV files for CsvCommerceConnector testing
```

## Rules

1. Never commit real customer data here.
2. All files in raw/ and processed/ are gitignored.
3. sample_uploads/ is gitignored except for .gitkeep.
4. Use scripts/seed_demo_data.py to populate raw/ with synthetic data.
5. The database is the source of truth for pipeline state — these files are transient.

## Sample Upload Format (Sprint 2)

CsvCommerceConnector expects these files in data/sample_uploads/:
- products.csv
- stores.csv
- orders.csv
- inventory_snapshots.csv
- promotions.csv
- suppliers.csv
- purchase_orders.csv

Column specs will be documented in docs/data_contract.md after Sprint 2.
