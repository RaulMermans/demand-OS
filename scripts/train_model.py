#!/usr/bin/env python3
"""
train_model.py — Train the LightGBM demand forecasting model.

Sprint 4 TODO: Implement after feature_matrix is populated.

Usage:
    python scripts/train_model.py
    python scripts/train_model.py --horizon 28 --cv-folds 3
    python scripts/train_model.py --model-type lightgbm
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Train DemandOS forecasting model.")
    parser.add_argument("--horizon", type=int, default=28, help="Forecast horizon in days.")
    parser.add_argument("--cv-folds", type=int, default=3, help="Number of walk-forward CV folds.")
    parser.add_argument(
        "--model-type",
        type=str,
        default="lightgbm",
        choices=["lightgbm", "xgboost", "naive"],
        help="Model type to train.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without training.")
    args = parser.parse_args()

    print("DemandOS — Train Forecasting Model")
    print("=" * 40)
    print(f"Model type: {args.model_type}")
    print(f"Horizon: {args.horizon} days")
    print(f"CV folds: {args.cv_folds}")
    print()
    print("Status: NOT IMPLEMENTED — Sprint 4")
    print()
    print("Sprint 4 TODO:")
    print("  1. Load feature_matrix from DB")
    print("  2. Split into train/validation/test sets (walk-forward CV)")
    print("  3. Train LightGBM global model across all SKU/store series")
    print("  4. Compute SMAPE, RMSE, MAE on validation folds")
    print("  5. Generate 28-day forecasts for all (product, store) pairs")
    print("  6. Write ModelVersion, ForecastRun, Forecast rows to DB")
    print("  7. Save model artifact to models/ directory")
    print()
    print("Reference: Nixtla/mlforecast for global ML forecasting approach.")
    print("Reference: M5 competition for 28-day horizon and WRMSSE metric.")
    sys.exit(0)


if __name__ == "__main__":
    main()
