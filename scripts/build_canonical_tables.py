#!/usr/bin/env python3
"""
build_canonical_tables.py — run the AggregationService against the dev database.

Usage:
  python scripts/build_canonical_tables.py
  python scripts/build_canonical_tables.py --start 2024-01-01 --end 2024-12-31
  python scripts/build_canonical_tables.py --dry-run

Options:
  --start DATE   Start date (default: earliest order in DB)
  --end   DATE   End date   (default: latest  order in DB)
  --dry-run      Print the date range that would be aggregated; do not run.
"""

import sys
import argparse
import time
from datetime import date
from pathlib import Path

# Add apps/api to sys.path so we can import the app
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))


def parse_args():
    p = argparse.ArgumentParser(description="Build DemandOS canonical daily tables.")
    p.add_argument("--start", type=date.fromisoformat, default=None, metavar="DATE",
                   help="Start date (YYYY-MM-DD). Default: earliest raw order date.")
    p.add_argument("--end",   type=date.fromisoformat, default=None, metavar="DATE",
                   help="End date (YYYY-MM-DD). Default: latest raw order date.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be done without executing.")
    return p.parse_args()


def main():
    args = parse_args()

    from app.db.session import SessionLocal, init_db
    from app.db.models import RawOrder
    from app.services.aggregation_service import AggregationService
    from sqlalchemy import func

    init_db()
    db = SessionLocal()

    try:
        row = db.query(func.min(RawOrder.order_date), func.max(RawOrder.order_date)).first()
        if row is None or row[0] is None:
            print("ERROR: No raw orders found in the database.")
            print("       Run scripts/seed_demo_data.py first.")
            sys.exit(1)

        start = args.start or row[0]
        end   = args.end   or row[1]

        print(f"DemandOS — Build Canonical Tables")
        print(f"  Date range : {start}  →  {end}")
        print(f"  Days       : {(end - start).days + 1}")

        if args.dry_run:
            print("\n[dry-run] No changes made.")
            return

        print("\nRunning AggregationService...")
        t0 = time.time()
        svc = AggregationService(db)
        result = svc.run_full_aggregation(start, end)
        elapsed = time.time() - t0

        if result["status"] == "success":
            print(f"\n✅ Aggregation complete in {elapsed:.1f}s")
            print(f"   Run ID : {result['run_id']}")
            for table, count in result["counts"].items():
                print(f"   {table:<30} {count:>8,}")
        else:
            print(f"\n❌ Aggregation FAILED")
            print(f"   Error: {result.get('error', 'unknown')}")
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
