#!/usr/bin/env python3
"""
run_daily_ingestion.py — Simulate one new day of mock data (append mode).

For Sprint 1, this appends a single day's mock records to the existing DB.
The same seed is used so the connector produces the same historical data,
but only the target date's records are inserted (existing IDs are skipped).

Usage:
    python scripts/run_daily_ingestion.py
    python scripts/run_daily_ingestion.py --date 2024-06-15
    python scripts/run_daily_ingestion.py --dry-run

Sprint 2 note: true daily-append mode (only generating the new day from state)
requires the AggregationService. Currently this generates the full 730-day dataset
but only inserts records for the target date (idempotent by primary key).
"""

import sys
import argparse
import time
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.db.session import init_db, SessionLocal
from app.services.ingestion_service import IngestionService


def main():
    parser = argparse.ArgumentParser(description="Run DemandOS daily ingestion.")
    parser.add_argument("--date",     type=str, help="Target date (YYYY-MM-DD). Default: yesterday.")
    parser.add_argument("--seed",     type=int, default=42)
    parser.add_argument("--dry-run",  action="store_true", help="Validate without writing to DB.")
    args = parser.parse_args()

    target_date = (
        date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
    )

    print("DemandOS — Daily Ingestion")
    print("=" * 40)
    print(f"Target date: {target_date}")
    print(f"Seed:        {args.seed}")
    print(f"Dry run:     {args.dry_run}")
    print()

    # Generate full history so IDs are consistent with the seeded dataset,
    # but IngestionService will skip records that already exist.
    end_date   = target_date
    start_date = end_date - timedelta(days=729)

    config    = MockConfig(seed=args.seed, product_count=50, store_count=5,
                           start_date=start_date, end_date=end_date)
    connector = MockCommerceConnector(config)

    # Only pass the target day to the ingestion service
    init_db()
    db = SessionLocal()
    try:
        service = IngestionService(connector, db)
        result  = service.run(target_date, target_date, dry_run=args.dry_run)
    finally:
        db.close()

    print(f"Status:   {result['status']}")
    print(f"Run ID:   {result['run_id']}")
    print("Counts:")
    for k, v in result["counts"].items():
        print(f"  {k:<30} {v:>6}")
    print()
    print("✅ Done.")


if __name__ == "__main__":
    main()
