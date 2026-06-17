#!/usr/bin/env python3
"""
run_baseline_forecast.py — Run a baseline demand forecast with backtesting.

Usage:
  python scripts/run_baseline_forecast.py --model seasonal_naive
  python scripts/run_baseline_forecast.py --model moving_average_7d --horizon-days 28 --backtest-days 56
  python scripts/run_baseline_forecast.py --model moving_average_28d --dry-run

Available models: seasonal_naive, moving_average_7d, moving_average_28d
"""

import argparse
import sys
import os

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.db.session import SessionLocal, init_db
from app.services.forecasting_service import ForecastingService, VALID_MODEL_TYPES


def main():
    parser = argparse.ArgumentParser(
        description="Run a DemandOS baseline demand forecast with backtesting."
    )
    parser.add_argument(
        "--model",
        dest="model_type",
        default="seasonal_naive",
        choices=sorted(VALID_MODEL_TYPES),
        help="Baseline model type (default: seasonal_naive)",
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=28,
        help="Forecast horizon in days (default: 28)",
    )
    parser.add_argument(
        "--backtest-days",
        type=int,
        default=56,
        help="Historical backtest window in days (default: 56)",
    )
    parser.add_argument(
        "--feature-run-id",
        default=None,
        help="Source feature run ID (default: all feature_matrix rows)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config without writing to DB",
    )
    args = parser.parse_args()

    print("DemandOS — Baseline Forecast")
    print("============================")
    print(f"  Model type   : {args.model_type}")
    print(f"  Horizon days : {args.horizon_days}")
    print(f"  Backtest days: {args.backtest_days}")

    if args.feature_run_id:
        print(f"  Feature run  : {args.feature_run_id}")

    if args.dry_run:
        print("\n[DRY RUN] — no DB writes.")
        print("Config valid. Pass without --dry-run to execute.")
        return

    print()
    init_db()
    db = SessionLocal()
    try:
        svc = ForecastingService(db)
        result = svc.run_baseline_forecast(
            model_type=args.model_type,
            horizon_days=args.horizon_days,
            backtest_days=args.backtest_days,
            source_feature_run_id=args.feature_run_id,
        )
    finally:
        db.close()

    if result["status"] == "completed":
        print(f"✅ Forecast run complete: {result['run_id']}")
        print(f"   Model type    : {result['model_type']}")
        print(f"   Rows created  : {result['rows_created']}")
        windows = result.get("date_windows", {})
        print(f"   Test window   : {windows.get('test_start')} → {windows.get('test_end')}")
        print(f"   Train window  : {windows.get('train_start')} → {windows.get('train_end')}")
        metrics = result.get("metrics", {}).get("overall", {})
        if metrics:
            print("\nOverall metrics:")
            for k, v in metrics.items():
                if k != "rows_evaluated" and v is not None:
                    print(f"   {k:<8}: {v:.4f}")
            print(f"   rows     : {metrics.get('rows_evaluated', 'N/A')}")
    elif result["status"] == "failed":
        print(f"❌ Forecast run failed: {result.get('error', 'unknown error')}")
        sys.exit(1)
    else:
        print(f"⚠️  Unexpected status: {result['status']}")


if __name__ == "__main__":
    main()
