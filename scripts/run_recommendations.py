"""
Run the DemandOS Reorder Recommendation Engine.

Usage:
  python scripts/run_recommendations.py
  python scripts/run_recommendations.py --risk-run-id risk-run-<uuid>
  python scripts/run_recommendations.py --include-low-risk
  python scripts/run_recommendations.py --dry-run

The script reads the latest completed forward_planning stockout risk run
and generates recommendation rows for each (product, store) pair.

Recommendation-only: no purchase orders created, no external calls made.
"""

import argparse
import sys
import os

# Resolve path so script works from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.db.session import SessionLocal, init_db
from app.services.recommendation_service import RecommendationService


def main():
    parser = argparse.ArgumentParser(
        description="Generate reorder recommendations from stockout risk rows."
    )
    parser.add_argument(
        "--risk-run-id",
        default=None,
        help="Specific stockout risk run ID to use. Defaults to latest completed forward_planning run.",
    )
    parser.add_argument(
        "--include-low-risk",
        action="store_true",
        default=False,
        help="Include low-risk rows in recommendations (excluded by default).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be done without writing to DB.",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] Recommendation engine — no DB writes will occur.")
        print(f"  risk_run_id:      {args.risk_run_id or '(latest forward_planning run)'}")
        print(f"  include_low_risk: {args.include_low_risk}")
        print("  Would call: RecommendationService.run_reorder_recommendations()")
        return

    print("DemandOS — Reorder Recommendation Engine")
    print("==========================================")
    print(f"  risk_run_id:      {args.risk_run_id or '(latest forward_planning run)'}")
    print(f"  include_low_risk: {args.include_low_risk}")
    print()

    init_db()
    db = SessionLocal()
    try:
        svc = RecommendationService(db)
        result = svc.run_reorder_recommendations(
            risk_run_id=args.risk_run_id,
            include_low_risk=args.include_low_risk,
        )

        if result["status"] == "failed":
            print(f"[FAILED] {result.get('error', 'Unknown error')}")
            sys.exit(1)

        summary = result.get("summary", {})
        print(f"Status:           {result['status']}")
        print(f"Run ID:           {result['recommendation_run_id']}")
        print(f"Source risk run:  {result['source_risk_run_id']}")
        print(f"Rows created:     {result['rows_created']}")
        print()
        print("Urgency breakdown:")
        print(f"  Critical: {summary.get('critical', 0)}")
        print(f"  High:     {summary.get('high', 0)}")
        print(f"  Medium:   {summary.get('medium', 0)}")
        print(f"  Low:      {summary.get('low', 0)}")
        print()
        print(f"Total recommended units: {summary.get('total_recommended_units', 0):.0f}")
        print(f"Total estimated cost:    {summary.get('total_estimated_order_cost', 0):.2f}")
        print()
        print("Note: These are recommendations only.")
        print("No purchase orders were created. No external systems were contacted.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
