"""
RecommendationService — generates reorder recommendations from stockout risks.

Input:  stockout_risks, forecasts, raw_suppliers, raw_products
Output: reorder_recommendations table

Algorithm plan (Sprint 5):
  For each (product, store) pair with risk_tier in (critical, high):
    1. Reorder point (ROP) = avg_daily_demand × lead_time + safety_stock
       (virbahu/inventory-optimization: reorder point formula)
    2. Economic Order Quantity (EOQ) = sqrt(2 × D × S / H)
         D = annual demand (units), S = ordering cost, H = holding cost/unit/year
       (virbahu/inventory-optimization: EOQ formula)
    3. recommended_qty = max(EOQ, ROP − on_hand)
    4. expected_delivery_date = today + lead_time_days
    5. estimated_cost = recommended_qty × unit_cost

    Recommendations are suggestions only — no automatic purchase orders are created.

Reference: virbahu/inventory-optimization for EOQ and ROP formulas.
"""


class RecommendationService:
    def run(self) -> dict:
        """
        Scaffold: returns not-implemented status.
        Sprint 5 TODO: implement reorder recommendation engine.
        """
        return {
            "status": "scaffold_ready",
            "message": "RecommendationService not yet implemented — Sprint 5.",
            "recommendations_produced": 0,
        }
