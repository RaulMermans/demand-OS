"""
AggregationService — builds daily sales and inventory aggregate tables.

Input:  raw_orders, raw_inventory_snapshots (from DB, not from connector)
Output: sales_daily, inventory_daily tables

Sprint 2 TODO: Implement using pandas groupby:
  - Sum order lines per (product_id, store_id, order_date)
  - Join promotion flags from raw_promotions
  - Compute days_of_supply from inventory snapshots and rolling demand averages
  - Handle missing dates by forward-filling inventory snapshots
  - Write to sales_daily and inventory_daily tables

Reference: M5 competition methodology for daily aggregation framing.
"""


class AggregationService:
    def run(self, start_date=None, end_date=None) -> dict:
        """
        Scaffold: returns not-implemented status.
        Sprint 2 TODO: implement full aggregation pipeline.
        """
        return {
            "status": "scaffold_ready",
            "message": "AggregationService not yet implemented — Sprint 2.",
            "records_produced": 0,
        }
