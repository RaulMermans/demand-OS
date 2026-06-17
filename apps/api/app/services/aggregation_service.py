"""
AggregationService — converts raw operational records into canonical daily tables.

Pipeline (per run):
  1. Clean pass  : filter/deduplicate raw records → *_clean tables (audit trail)
  2. sales_daily : sum fulfilled orders per (product, store, date)
  3. inventory_daily : latest snapshot per (product, store, date) + days_of_supply
  4. promotion_daily : flag active promotions per (product, store, date)
  5. product_store_daily : denormalized join of all three tables

Idempotency: _clear_range() deletes canonical rows for [start_date, end_date] before
re-inserting, so running twice with the same window gives identical rows.
"""

import logging
from collections import defaultdict
from datetime import datetime, date, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import (
    RawOrder, RawInventorySnapshot, RawPromotion, RawProduct, RawStore,
    RawPurchaseOrder, RawSupplier,
    OrdersClean, InventoryClean, PromotionsClean, ProductsClean,
    StoresClean, SuppliersClean, PurchaseOrdersClean,
    SalesDaily, InventoryDaily, PromotionDaily, ProductStoreDaily,
    AggregationRun,
)

logger = logging.getLogger(__name__)

_SALES_STATUSES = {"fulfilled"}
_EXCLUDED_STATUSES = {"cancelled", "returned"}
_PO_INBOUND_STATUSES = {"confirmed", "received"}


def _date_range(start: date, end: date) -> list[date]:
    days: list[date] = []
    d = start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days


class AggregationService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_full_aggregation(self, start_date: date, end_date: date) -> dict:
        """Clean raw records and build canonical daily tables for [start_date, end_date]."""
        run = AggregationRun(
            id=str(uuid4()),
            started_at=datetime.utcnow(),
            start_date=start_date,
            end_date=end_date,
            status="running",
        )
        self.db.add(run)
        self.db.flush()

        try:
            self._clear_range(start_date, end_date)
            counts = self._run_pipeline(start_date, end_date, run.id)
            run.status = "success"
            run.finished_at = datetime.utcnow()
            run.records_produced = counts
            self.db.commit()
            return {"status": "success", "run_id": run.id, "counts": counts}
        except Exception as exc:
            self.db.rollback()
            logger.exception("Aggregation run %s failed", run.id)
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error_message = str(exc)
            self.db.add(run)
            self.db.commit()
            return {"status": "failed", "run_id": run.id, "error": str(exc)}

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def _run_pipeline(self, start_date: date, end_date: date, run_id: str) -> dict:
        raw_orders = self.db.query(RawOrder).filter(
            RawOrder.order_date >= start_date, RawOrder.order_date <= end_date,
        ).all()
        raw_inv = self.db.query(RawInventorySnapshot).filter(
            RawInventorySnapshot.snapshot_date >= start_date,
            RawInventorySnapshot.snapshot_date <= end_date,
        ).all()
        raw_promos = self.db.query(RawPromotion).all()
        raw_products = self.db.query(RawProduct).all()
        raw_stores = self.db.query(RawStore).all()
        raw_pos = self.db.query(RawPurchaseOrder).all()
        raw_suppliers = self.db.query(RawSupplier).all()

        clean_counts = self._write_clean_tables(
            raw_orders, raw_inv, raw_promos, raw_products,
            raw_stores, raw_suppliers, raw_pos, run_id,
        )

        sales_orders = [o for o in raw_orders if (o.status or "").lower() in _SALES_STATUSES]
        promo_lookup = _build_promo_lookup(raw_promos, raw_products, raw_stores, start_date, end_date)

        sales_by_key, n_sales = self._build_sales_daily(sales_orders, promo_lookup, run_id)
        inv_by_key, n_inv = self._build_inventory_daily(raw_inv, raw_pos, sales_by_key, run_id)
        promo_by_key, n_promo = self._build_promotion_daily(
            promo_lookup, raw_products, raw_stores, start_date, end_date, run_id,
        )
        n_psd = self._build_product_store_daily(
            raw_products, raw_stores, start_date, end_date,
            sales_by_key, inv_by_key, promo_by_key, run_id,
        )

        return {**clean_counts, "sales_daily": n_sales, "inventory_daily": n_inv,
                "promotion_daily": n_promo, "product_store_daily": n_psd}

    def _clear_range(self, start_date: date, end_date: date) -> None:
        """Delete canonical daily rows in [start_date, end_date] and rebuild clean tables."""
        for model in [SalesDaily, InventoryDaily, PromotionDaily, ProductStoreDaily]:
            self.db.query(model).filter(
                model.date >= start_date, model.date <= end_date,
            ).delete(synchronize_session=False)
        for model in [OrdersClean, InventoryClean, PromotionsClean,
                      ProductsClean, StoresClean, SuppliersClean, PurchaseOrdersClean]:
            self.db.query(model).delete(synchronize_session=False)
        self.db.flush()

    # ------------------------------------------------------------------
    # Clean layer
    # ------------------------------------------------------------------

    def _write_clean_tables(self, raw_orders, raw_inv, raw_promos,
                             raw_products, raw_stores, raw_suppliers, raw_pos, run_id) -> dict:
        now = datetime.utcnow()

        clean_orders = [o for o in raw_orders if (o.status or "").lower() not in _EXCLUDED_STATUSES]
        self._bulk_insert(OrdersClean, [
            {"id": f"oc_{o.id}", "raw_order_id": o.id, "product_id": o.product_id,
             "store_id": o.store_id, "order_date": o.order_date, "quantity": o.quantity,
             "unit_price": o.unit_price, "discount_amount": o.discount_amount or 0.0,
             "currency": o.currency or "EUR", "promotion_id": o.promotion_id,
             "aggregation_run_id": run_id, "cleaned_at": now}
            for o in clean_orders
        ])

        seen_inv: dict[tuple, str] = {}
        for snap in sorted(raw_inv, key=lambda s: s.ingested_at):
            seen_inv[(snap.product_id, snap.store_id, snap.snapshot_date)] = snap.id
        inv_ids = set(seen_inv.values())
        self._bulk_insert(InventoryClean, [
            {"id": f"ic_{s.id}", "raw_snapshot_id": s.id, "product_id": s.product_id,
             "store_id": s.store_id, "snapshot_date": s.snapshot_date,
             "on_hand": s.quantity_on_hand, "on_order": s.quantity_on_order or 0.0,
             "aggregation_run_id": run_id, "cleaned_at": now}
            for s in raw_inv if s.id in inv_ids
        ])

        self._bulk_insert(PromotionsClean, [
            {"id": f"pc_{p.id}", "raw_promotion_id": p.id, "name": p.name,
             "promotion_type": p.promotion_type, "discount_pct": p.discount_pct or 0.0,
             "start_date": p.start_date, "end_date": p.end_date,
             "applicable_skus": p.applicable_skus or [], "applicable_stores": p.applicable_stores or [],
             "aggregation_run_id": run_id, "cleaned_at": now}
            for p in raw_promos if p.start_date and p.end_date and p.end_date >= p.start_date
        ])

        self._bulk_insert(ProductsClean, [
            {"id": f"prc_{p.id}", "raw_product_id": p.id, "sku": p.sku, "name": p.name,
             "category": p.category, "brand": p.brand, "supplier_id": p.supplier_id,
             "unit_cost": p.unit_cost, "unit_price": p.unit_price, "lead_time_days": p.lead_time_days,
             "aggregation_run_id": run_id, "cleaned_at": now}
            for p in raw_products if p.is_active
        ])

        self._bulk_insert(StoresClean, [
            {"id": f"sc_{s.id}", "raw_store_id": s.id, "name": s.name,
             "region": s.region, "country": s.country, "channel": s.channel,
             "aggregation_run_id": run_id, "cleaned_at": now}
            for s in raw_stores if s.is_active
        ])

        self._bulk_insert(SuppliersClean, [
            {"id": f"supc_{s.id}", "raw_supplier_id": s.id, "name": s.name,
             "country": s.country, "lead_time_days_min": s.lead_time_days_min,
             "lead_time_days_max": s.lead_time_days_max, "reliability_score": s.reliability_score,
             "aggregation_run_id": run_id, "cleaned_at": now}
            for s in raw_suppliers
        ])

        self._bulk_insert(PurchaseOrdersClean, [
            {"id": f"poc_{po.id}", "raw_po_id": po.id, "supplier_id": po.supplier_id,
             "product_id": po.product_id, "store_id": po.store_id,
             "ordered_date": po.ordered_at.date(), "expected_delivery_date": po.expected_delivery_date,
             "quantity_ordered": po.quantity_ordered, "unit_cost": po.unit_cost,
             "status": po.status, "aggregation_run_id": run_id, "cleaned_at": now}
            for po in raw_pos
        ])

        self.db.flush()
        return {
            "orders_clean": len(clean_orders),
            "inventory_clean": len(inv_ids),
            "promotions_clean": sum(1 for p in raw_promos if p.start_date and p.end_date and p.end_date >= p.start_date),
            "products_clean": sum(1 for p in raw_products if p.is_active),
            "stores_clean": sum(1 for s in raw_stores if s.is_active),
            "suppliers_clean": len(raw_suppliers),
            "purchase_orders_clean": len(raw_pos),
        }

    # ------------------------------------------------------------------
    # Canonical: sales_daily
    # ------------------------------------------------------------------

    def _build_sales_daily(self, fulfilled_orders, promo_lookup: dict, run_id: str) -> tuple[dict, int]:
        groups: dict[tuple, dict] = defaultdict(
            lambda: {"units": 0.0, "revenue": 0.0, "discount": 0.0, "count": 0, "prices": []}
        )
        for o in fulfilled_orders:
            key = (o.product_id, o.store_id, o.order_date)
            g = groups[key]
            g["units"] += o.quantity
            g["revenue"] += o.quantity * o.unit_price - (o.discount_amount or 0.0)
            g["discount"] += o.discount_amount or 0.0
            g["count"] += 1
            g["prices"].append(o.unit_price)

        now = datetime.utcnow()
        rows = []
        sales_by_key: dict[tuple, dict] = {}

        for (pid, sid, d), g in groups.items():
            promo_info = promo_lookup.get((pid, sid, d))
            avg_price = sum(g["prices"]) / len(g["prices"]) if g["prices"] else None
            sales_by_key[(pid, sid, d)] = {
                "units_sold": g["units"], "net_revenue": round(g["revenue"], 2),
                "discount_amount": round(g["discount"], 2),
            }
            rows.append({
                "id": f"sd_{pid}_{sid}_{d}",
                "product_id": pid, "store_id": sid, "date": d,
                "units_sold": g["units"], "net_revenue": round(g["revenue"], 2),
                "discount_amount": round(g["discount"], 2),
                "avg_unit_price": round(avg_price, 4) if avg_price is not None else None,
                "order_count": g["count"],
                "promotion_active": promo_info is not None,
                "source_run_id": run_id, "computed_at": now,
            })

        self._bulk_insert(SalesDaily, rows)
        self.db.flush()
        return sales_by_key, len(rows)

    # ------------------------------------------------------------------
    # Canonical: inventory_daily
    # ------------------------------------------------------------------

    def _build_inventory_daily(self, raw_inv, raw_pos, sales_by_key: dict, run_id: str) -> tuple[dict, int]:
        latest: dict[tuple, object] = {}
        for snap in sorted(raw_inv, key=lambda s: s.ingested_at):
            latest[(snap.product_id, snap.store_id, snap.snapshot_date)] = snap

        inbound: dict[tuple, float] = defaultdict(float)
        for po in raw_pos:
            if po.expected_delivery_date and (po.status or "").lower() in _PO_INBOUND_STATUSES:
                inbound[(po.product_id, po.store_id, po.expected_delivery_date)] += po.quantity_ordered

        now = datetime.utcnow()
        rows = []
        inv_by_key: dict[tuple, dict] = {}

        for (pid, sid, d), snap in latest.items():
            on_hand = snap.quantity_on_hand
            dos = _compute_days_of_supply(pid, sid, d, on_hand, sales_by_key)
            inb = inbound.get((pid, sid, d), 0.0)
            inv_by_key[(pid, sid, d)] = {
                "on_hand_units": on_hand, "on_order_units": snap.quantity_on_order or 0.0,
                "inbound_units": inb, "stockout_flag": on_hand == 0, "days_of_supply": dos,
            }
            rows.append({
                "id": f"invd_{pid}_{sid}_{d}",
                "product_id": pid, "store_id": sid, "date": d,
                "on_hand_units": on_hand, "on_order_units": snap.quantity_on_order or 0.0,
                "inbound_units": inb, "stockout_flag": on_hand == 0,
                "days_of_supply": dos, "source_run_id": run_id, "computed_at": now,
            })

        self._bulk_insert(InventoryDaily, rows)
        self.db.flush()
        return inv_by_key, len(rows)

    # ------------------------------------------------------------------
    # Canonical: promotion_daily
    # ------------------------------------------------------------------

    def _build_promotion_daily(self, promo_lookup: dict, raw_products, raw_stores,
                                start_date: date, end_date: date, run_id: str) -> tuple[dict, int]:
        now = datetime.utcnow()
        rows = []
        promo_by_key: dict[tuple, dict] = {}

        for prod in raw_products:
            for store in raw_stores:
                pid, sid = prod.id, store.id
                for d in _date_range(start_date, end_date):
                    info = promo_lookup.get((pid, sid, d))
                    promo_by_key[(pid, sid, d)] = {"is_active": info is not None,
                                                    "discount_pct": info["discount_pct"] if info else 0.0}
                    rows.append({
                        "id": f"prd_{pid}_{sid}_{d}",
                        "product_id": pid, "store_id": sid, "date": d,
                        "is_active": info is not None,
                        "promotion_id": info["promotion_id"] if info else None,
                        "discount_pct": info["discount_pct"] if info else 0.0,
                        "promotion_name": info["name"] if info else None,
                        "source_run_id": run_id, "computed_at": now,
                    })

        self._bulk_insert(PromotionDaily, rows)
        self.db.flush()
        return promo_by_key, len(rows)

    # ------------------------------------------------------------------
    # Canonical: product_store_daily
    # ------------------------------------------------------------------

    def _build_product_store_daily(self, raw_products, raw_stores,
                                    start_date: date, end_date: date,
                                    sales_by_key: dict, inv_by_key: dict,
                                    promo_by_key: dict, run_id: str) -> int:
        now = datetime.utcnow()
        rows = []

        for prod in raw_products:
            for store in raw_stores:
                pid, sid = prod.id, store.id
                for d in _date_range(start_date, end_date):
                    s = sales_by_key.get((pid, sid, d)) or {}
                    iv = inv_by_key.get((pid, sid, d)) or {}
                    pr = promo_by_key.get((pid, sid, d)) or {}
                    rows.append({
                        "id": f"psd_{pid}_{sid}_{d}",
                        "date": d, "product_id": pid, "store_id": sid,
                        "sku": prod.sku, "product_name": prod.name, "category": prod.category,
                        "channel": store.channel,
                        "units_sold": s.get("units_sold", 0.0),
                        "net_revenue": s.get("net_revenue", 0.0),
                        "discount_amount": s.get("discount_amount", 0.0),
                        "on_hand_units": iv.get("on_hand_units"),
                        "on_order_units": iv.get("on_order_units"),
                        "inbound_units": iv.get("inbound_units", 0.0),
                        "stockout_flag": iv.get("stockout_flag", False),
                        "days_of_supply": iv.get("days_of_supply"),
                        "promotion_active": pr.get("is_active", False),
                        "discount_pct": pr.get("discount_pct", 0.0),
                        "source_run_id": run_id, "computed_at": now,
                    })

        self._bulk_insert(ProductStoreDaily, rows)
        self.db.flush()
        return len(rows)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bulk_insert(self, model, rows: list[dict]) -> None:
        chunk = 2000
        for i in range(0, len(rows), chunk):
            self.db.bulk_insert_mappings(model, rows[i:i + chunk])


# ---------------------------------------------------------------------------
# Module-level helpers (pure functions — no DB access)
# ---------------------------------------------------------------------------

def _build_promo_lookup(raw_promos, raw_products, raw_stores,
                         start_date: date, end_date: date) -> dict:
    """Return {(product_id, store_id, date): {promotion_id, discount_pct, name}} for active promotions."""
    sku_by_pid = {p.id: p.sku for p in raw_products}
    all_pids = [p.id for p in raw_products]
    all_sids = [s.id for s in raw_stores]
    all_dates = _date_range(start_date, end_date)

    lookup: dict[tuple, dict] = {}

    for promo in raw_promos:
        if not promo.start_date or not promo.end_date or promo.end_date < promo.start_date:
            continue

        appl_pids = (
            [pid for pid in all_pids if sku_by_pid.get(pid) in set(promo.applicable_skus)]
            if promo.applicable_skus else all_pids
        )
        appl_sids = (
            [sid for sid in all_sids if sid in set(promo.applicable_stores)]
            if promo.applicable_stores else all_sids
        )

        for d in all_dates:
            if not (promo.start_date <= d <= promo.end_date):
                continue
            for pid in appl_pids:
                for sid in appl_sids:
                    key = (pid, sid, d)
                    existing = lookup.get(key)
                    if existing is None or promo.discount_pct > existing["discount_pct"]:
                        lookup[key] = {
                            "promotion_id": promo.id,
                            "discount_pct": promo.discount_pct,
                            "name": promo.name,
                        }
    return lookup


def _compute_days_of_supply(product_id: str, store_id: str, d: date,
                              on_hand: float, sales_by_key: dict) -> float | None:
    """days_of_supply = on_hand / rolling_mean_7d_units_sold (divide by 7)."""
    total = 0.0
    for offset in range(7):
        entry = sales_by_key.get((product_id, store_id, d - timedelta(days=offset)))
        if entry:
            total += entry["units_sold"]
    if total < 0.001:
        return None
    return round(on_hand / (total / 7), 2)
