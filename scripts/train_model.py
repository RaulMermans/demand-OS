#!/usr/bin/env python3
"""
train_model.py — Train the ML demand forecasting model.

Usage:
    python scripts/train_model.py
    python scripts/train_model.py --algorithm hist_gradient_boosting
    python scripts/train_model.py --horizon-days 28 --backtest-days 56
    python scripts/train_model.py --dry-run

The script calls TrainingService — the same service used by POST /api/models/train.
Requires the API package to be installed: pip install -e apps/api[dev]

Feature matrix must be built first:
    python scripts/build_features.py
"""

import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Add apps/api to path for standalone script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train DemandOS ML forecasting model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        default="hist_gradient_boosting",
        choices=["hist_gradient_boosting"],
        help="ML algorithm to use (default: hist_gradient_boosting)",
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
        type=str,
        default=None,
        help="Specific feature_run_id to use (default: all rows)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate setup without training",
    )
    args = parser.parse_args()

    print("DemandOS — Train ML Forecasting Model")
    print("=" * 45)
    print(f"Algorithm:     {args.algorithm}")
    print(f"Horizon days:  {args.horizon_days}")
    print(f"Backtest days: {args.backtest_days}")
    if args.feature_run_id:
        print(f"Feature run:   {args.feature_run_id}")
    print()

    if args.dry_run:
        print("DRY RUN — validating imports only")
        try:
            from app.services.training_service import TrainingService, ALL_FEATURE_COLUMNS
            print(f"✅ TrainingService imported OK")
            print(f"✅ Feature columns ({len(ALL_FEATURE_COLUMNS)}): {ALL_FEATURE_COLUMNS[:5]}...")
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            sys.exit(1)
        print("Dry run complete.")
        return

    try:
        from app.db.session import SessionLocal, init_db
        from app.services.training_service import TrainingService
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("Make sure the API package is installed: pip install -e apps/api/[dev]")
        sys.exit(1)

    init_db()
    db = SessionLocal()
    try:
        svc = TrainingService(db)
        logger.info("Starting ML training...")
        result = svc.train_ml_forecaster(
            algorithm=args.algorithm,
            horizon_days=args.horizon_days,
            backtest_days=args.backtest_days,
            source_feature_run_id=args.feature_run_id,
        )

        if result.get("status") == "failed":
            print(f"❌ Training failed: {result.get('error')}")
            sys.exit(1)

        print(f"✅ Training complete")
        print(f"   Model version: {result['model_version_id']}")
        print(f"   Forecast run:  {result['forecast_run_id']}")
        print(f"   Rows predicted: {result['rows_predicted']}")
        print()

        overall = result.get("metrics", {}).get("overall", {})
        if overall:
            print("Overall metrics:")
            print(f"   MAE:   {overall.get('mae', 'N/A'):.4f}" if overall.get("mae") else "   MAE:   N/A")
            print(f"   RMSE:  {overall.get('rmse', 'N/A'):.4f}" if overall.get("rmse") else "   RMSE:  N/A")
            print(f"   WAPE:  {overall.get('wape', 'N/A'):.4f}" if overall.get("wape") else "   WAPE:  N/A")
            print(f"   SMAPE: {overall.get('smape', 'N/A'):.4f}" if overall.get("smape") else "   SMAPE: N/A")
            print(f"   Bias:  {overall.get('bias', 'N/A'):.4f}" if overall.get("bias") else "   Bias:  N/A")
            print()

        comparison = result.get("baseline_comparison", {})
        if comparison.get("available"):
            print("Baseline comparison:")
            print(f"   Best baseline: {comparison.get('best_baseline_model_type')} (WAPE={comparison.get('best_baseline_wape'):.4f})" if comparison.get("best_baseline_wape") else f"   Best baseline: {comparison.get('best_baseline_model_type')}")
            ml_won = comparison.get("ml_won_against_baseline")
            delta = comparison.get("wape_delta")
            if ml_won is True:
                print(f"   ✅ ML beats baseline by {abs(delta):.4f} WAPE points" if delta else "   ✅ ML beats baseline")
            elif ml_won is False:
                print(f"   ℹ️  Baseline beats ML by {abs(delta):.4f} WAPE points" if delta else "   ℹ️  Baseline beats ML")
            else:
                print("   ℹ️  Comparison unavailable")
        else:
            print(f"   {comparison.get('message', 'No baseline comparison available')}")

        print()
        print(f"Artifact: {result.get('artifact_path', 'N/A')}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
