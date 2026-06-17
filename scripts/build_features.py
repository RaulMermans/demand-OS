#!/usr/bin/env python3
"""
CLI: build the Sprint 3 feature matrix from product_store_daily.

Usage:
  python scripts/build_features.py [--max-lag-days N] [--dry-run]

Options:
  --max-lag-days N    Maximum lag window in days (default: 28)
  --dry-run           Report what would be done without writing to the database
"""

import argparse
import os
import sys

# Allow running from repo root or scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.db.session import SessionLocal, init_db
from app.services.feature_service import FeatureService


def main():
    parser = argparse.ArgumentParser(description="Build the DemandOS feature matrix.")
    parser.add_argument("--max-lag-days", type=int, default=28,
                        help="Maximum lag window in days (default: 28)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report row counts without writing to the database")
    args = parser.parse_args()

    init_db()

    if args.dry_run:
        db = SessionLocal()
        try:
            from sqlalchemy import func
            from app.db.models import ProductStoreDaily
            psd_count = db.query(func.count(ProductStoreDaily.id)).scalar() or 0
            print(f"[dry-run] product_store_daily rows available: {psd_count}")
            print(f"[dry-run] Would build feature matrix with max_lag_days={args.max_lag_days}")
            print("[dry-run] No changes made.")
        finally:
            db.close()
        return

    db = SessionLocal()
    try:
        print(f"Building feature matrix (max_lag_days={args.max_lag_days})...")
        svc = FeatureService(db)
        result = svc.build_feature_matrix(max_lag_days=args.max_lag_days)

        status = result.get("status")
        if status == "no_data":
            print(f"ERROR: {result.get('message')}")
            sys.exit(1)
        elif status == "failed":
            print(f"ERROR: Feature build failed — {result.get('error')}")
            sys.exit(1)
        else:
            rows = result["rows_created"]
            date_min = result.get("date_min")
            date_max = result.get("date_max")
            print(f"  feature_matrix rows written : {rows:,}")
            print(f"  date range                  : {date_min} → {date_max}")
            checks = result.get("checks", [])
            for c in checks:
                mark = "✓" if c["status"] == "passed" else "✗"
                detail = c.get("detail", "")
                print(f"  {mark} {c['name']}" + (f" — {detail}" if detail else ""))
            failed = [c for c in checks if c["status"] != "passed"]
            if failed:
                print(f"\nWARNING: {len(failed)} check(s) failed.")
                sys.exit(2)
            print("\nFeature matrix built successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
