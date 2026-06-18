#!/usr/bin/env python3
"""
run_planning_forecast.py — CLI to generate forward-looking baseline forecasts.

Usage:
  python scripts/run_planning_forecast.py --model seasonal_naive --horizon-days 28
  python scripts/run_planning_forecast.py --model moving_average_7d --horizon-days 14

This generates future forecast rows for the next horizon_days beyond the latest
canonical date in the feature_matrix. These rows are tagged mode=forward_planning
and are preferred by run_stockout_risk.py when computing inventory risk.

NOTE: This uses a flat (constant) projection from the last available feature
values — it does NOT apply an ML model to future dates.
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.db.session import SessionLocal, init_db
from app.services.forecasting_service import ForecastingService, VALID_MODEL_TYPES


def main():
    parser = argparse.ArgumentParser(
        description="Generate forward-planning forecast rows for DemandOS."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="seasonal_naive",
        choices=sorted(VALID_MODEL_TYPES),
        help=f"Baseline model type (default: seasonal_naive)",
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=28,
        help="Number of future days to forecast (default: 28)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, validate inputs but do not persist results",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] Would run planning forecast with:")
        print(f"  model={args.model}")
        print(f"  horizon_days={args.horizon_days}")
        return

    print("Initializing database...")
    init_db()

    print(f"Running planning forecast (model={args.model}, horizon={args.horizon_days}d)...")
    db = SessionLocal()
    try:
        svc = ForecastingService(db)
        result = svc.run_planning_forecast(
            model_type=args.model,
            horizon_days=args.horizon_days,
        )
    finally:
        db.close()

    print("\nResult:")
    print(json.dumps(result, indent=2, default=str))

    if result.get("status") == "completed":
        print(f"\nRows created: {result.get('rows_created', 0)}")
        print(f"Run ID      : {result.get('run_id')}")
        print(f"Forecast window: {result.get('forecast_window', {})}")
        sys.exit(0)
    else:
        print(f"\nError: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
