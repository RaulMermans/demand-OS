#!/usr/bin/env python3
"""
run_stockout_risk.py — CLI to run the stockout risk engine.

Usage:
  python scripts/run_stockout_risk.py --horizon-days 28
  python scripts/run_stockout_risk.py --forecast-run-id forecast-run-...
  python scripts/run_stockout_risk.py --mode historical_simulation

The script runs StockoutService.run_stockout_risk() and prints the result.
No DB modifications are made when --dry-run is passed.
"""

import argparse
import json
import sys
import os

# Add the api app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.db.session import SessionLocal, init_db
from app.services.stockout_service import StockoutService


def main():
    parser = argparse.ArgumentParser(description="Run the DemandOS stockout risk engine.")
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=28,
        help="Forecast horizon in days (default: 28)",
    )
    parser.add_argument(
        "--forecast-run-id",
        type=str,
        default=None,
        help="Specific forecast run ID to use (default: latest forward_planning run)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="forward_planning",
        choices=["forward_planning", "historical_simulation"],
        help="Risk mode (default: forward_planning)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, validate inputs but do not persist results",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] Would run stockout risk with:")
        print(f"  horizon_days={args.horizon_days}")
        print(f"  forecast_run_id={args.forecast_run_id}")
        print(f"  mode={args.mode}")
        return

    print("Initializing database...")
    init_db()

    print(f"Running stockout risk engine (mode={args.mode}, horizon={args.horizon_days}d)...")
    db = SessionLocal()
    try:
        svc = StockoutService(db)
        result = svc.run_stockout_risk(
            forecast_run_id=args.forecast_run_id,
            horizon_days=args.horizon_days,
            mode=args.mode,
        )
    finally:
        db.close()

    print("\nResult:")
    print(json.dumps(result, indent=2, default=str))

    if result.get("status") == "completed":
        counts = result.get("risk_counts", {})
        print(f"\nRisk counts:")
        print(f"  critical : {counts.get('critical', 0)}")
        print(f"  high     : {counts.get('high', 0)}")
        print(f"  medium   : {counts.get('medium', 0)}")
        print(f"  low      : {counts.get('low', 0)}")
        print(f"  unknown  : {counts.get('unknown', 0)}")
        print(f"\nRows created: {result.get('rows_created', 0)}")
        print(f"Risk run ID : {result.get('risk_run_id')}")
        sys.exit(0)
    else:
        print(f"\nError: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
