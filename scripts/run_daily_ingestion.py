#!/usr/bin/env python3
"""
run_daily_ingestion.py — Run the daily ingestion pipeline for yesterday's data.

Sprint 1 TODO: Implement after IngestionService is complete.

Usage:
    python scripts/run_daily_ingestion.py
    python scripts/run_daily_ingestion.py --date 2024-01-15
    python scripts/run_daily_ingestion.py --connector shopify
"""

import sys
import argparse
from datetime import date, timedelta


def main():
    parser = argparse.ArgumentParser(description="Run DemandOS daily ingestion.")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD). Default: yesterday.")
    parser.add_argument("--connector", type=str, default="mock", help="Connector: mock|csv|shopify")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to DB.")
    args = parser.parse_args()

    target_date = (
        date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
    )

    print("DemandOS — Daily Ingestion")
    print("=" * 40)
    print(f"Date: {target_date}")
    print(f"Connector: {args.connector}")
    print(f"Dry run: {args.dry_run}")
    print()
    print("Status: NOT IMPLEMENTED — Sprint 1")
    print()
    print("Sprint 1 TODO:")
    print("  1. Resolve connector from --connector flag")
    print("  2. Call IngestionService.run(start_date=target_date, end_date=target_date)")
    print("  3. Call ValidationService.validate()")
    print("  4. Call AggregationService.run() for the same date")
    print("  5. Log IngestionRun to DB")
    print("  6. Print summary with record counts")
    sys.exit(0)


if __name__ == "__main__":
    main()
