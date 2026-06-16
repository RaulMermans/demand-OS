#!/usr/bin/env python3
"""
seed_demo_data.py — Generate synthetic demo data and persist via IngestionService.

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --seed 42 --products 50 --stores 5 --days 730
    python scripts/seed_demo_data.py --dry-run
"""

import sys
import argparse
import time
from pathlib import Path

# Add apps/api to path so app modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from datetime import date, timedelta

from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.db.session import init_db, SessionLocal
from app.services.ingestion_service import IngestionService


def main():
    parser = argparse.ArgumentParser(description="Seed DemandOS with synthetic demo data.")
    parser.add_argument("--seed",     type=int, default=42,   help="Random seed (default: 42)")
    parser.add_argument("--products", type=int, default=50,   help="Number of products (default: 50)")
    parser.add_argument("--stores",   type=int, default=5,    help="Number of stores (default: 5)")
    parser.add_argument("--days",     type=int, default=730,  help="Days of history (default: 730)")
    parser.add_argument("--reset",    action="store_true",    help="Clear existing data before seeding.")
    parser.add_argument("--dry-run",  action="store_true",    help="Validate without writing to DB.")
    args = parser.parse_args()

    print("DemandOS — Seed Demo Data")
    print("=" * 50)
    print(f"Seed:     {args.seed}")
    print(f"Products: {args.products}")
    print(f"Stores:   {args.stores}")
    print(f"Days:     {args.days}")
    print(f"Reset:    {args.reset}")
    print(f"Dry run:  {args.dry_run}")
    print()

    end_date   = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=args.days - 1)
    print(f"Date range: {start_date} → {end_date}")
    print()

    print("Generating synthetic data...")
    t0 = time.time()
    config = MockConfig(
        seed=args.seed,
        product_count=args.products,
        store_count=args.stores,
        history_days=args.days,
        start_date=start_date,
        end_date=end_date,
    )
    connector = MockCommerceConnector(config)
    t1 = time.time()
    print(f"  Generation complete in {t1-t0:.1f}s")
    print(f"  Products:             {len(connector.fetch_products())}")
    print(f"  Stores:               {len(connector.fetch_stores())}")
    print(f"  Suppliers:            {len(connector.fetch_suppliers())}")
    print(f"  Promotions:           {len(connector.fetch_promotions(start_date, end_date))}")
    print(f"  Order lines:          {len(connector.fetch_orders(start_date, end_date))}")
    print(f"  Inventory snapshots:  {len(connector.fetch_inventory_snapshots(start_date, end_date))}")
    print(f"  Purchase orders:      {len(connector.fetch_purchase_orders(start_date, end_date))}")
    print()

    if args.dry_run:
        print("DRY RUN — no data written to DB.")
        sys.exit(0)

    print("Initialising database...")
    init_db()

    print("Persisting records...")
    t2 = time.time()
    db = SessionLocal()
    try:
        service = IngestionService(connector, db)
        if args.reset:
            result = service.reset_and_seed(start_date, end_date)
        else:
            result = service.run(start_date, end_date)
    finally:
        db.close()
    t3 = time.time()

    print(f"  Persistence complete in {t3-t2:.1f}s")
    print()
    print("Summary:")
    for k, v in result["counts"].items():
        print(f"  {k:<30} {v:>8}")
    print(f"  {'total':<30} {result['records_ingested']:>8}")
    print()
    print(f"Run ID:  {result['run_id']}")
    print(f"Status:  {result['status']}")
    print()
    print("✅ Done. Run the API and check GET /api/data-health")


if __name__ == "__main__":
    main()
