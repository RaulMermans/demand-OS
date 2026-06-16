"""
StockoutService — computes stockout risk scores from forecasts + inventory.

Input:  forecasts, inventory_daily, raw_suppliers (for lead times)
Output: stockout_risks table

Algorithm plan (Sprint 5):
  For each (product, store) combination:
    1. Sum cumulative forecasted demand over lead time window
    2. Compare against current quantity_on_hand
    3. Compute safety stock: Z-score × σ(demand) × √lead_time
       (virbahu/inventory-optimization: safety stock formula)
    4. Estimate days_until_stockout = on_hand / avg_daily_demand
    5. Assign risk_tier:
         critical  → days_until_stockout ≤ lead_time_days
         high      → days_until_stockout ≤ lead_time_days × 1.5
         medium    → days_until_stockout ≤ lead_time_days × 2
         low       → otherwise

Reference: virbahu/inventory-optimization for safety stock, reorder point formulas.
"""


class StockoutService:
    def run(self) -> dict:
        """
        Scaffold: returns not-implemented status.
        Sprint 5 TODO: implement stockout risk scoring.
        """
        return {
            "status": "scaffold_ready",
            "message": "StockoutService not yet implemented — Sprint 5.",
            "risks_computed": 0,
        }
