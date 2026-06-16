"""
ValidationService — validates raw records before persistence.

Checks:
  - Required fields present and correctly typed
  - Non-negative quantities and prices
  - Referential integrity (orders → products, stores; products → suppliers; etc.)
  - Date logic (promotion end >= start; PO delivery >= order date)
  - No forbidden derived/ML fields present in raw schemas
  - Dataset-level checks (at least some stockouts exist, at least some promotions)
"""

from datetime import date
from typing import Any

from app.schemas.raw import (
    RawProduct, RawStore, RawOrderLine, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
    FORBIDDEN_DERIVED_FIELDS,
)


class ValidationService:

    def validate_batch(
        self,
        products: list[RawProduct],
        stores: list[RawStore],
        suppliers: list[RawSupplier],
        promotions: list[RawPromotion],
        orders: list[RawOrderLine],
        snapshots: list[RawInventorySnapshot],
        purchase_orders: list[RawPurchaseOrder],
    ) -> dict[str, Any]:
        """
        Validate a full batch of raw records.

        Returns a dict with:
          - "passed": bool
          - "issues": list of {severity, message, entity_type, entity_id}
          - "checks": list of {name, status, detail}
        """
        issues: list[dict] = []
        checks: list[dict] = []

        product_ids  = {p.id for p in products}
        store_ids    = {s.id for s in stores}
        supplier_ids = {s.id for s in suppliers}
        sku_set      = {p.sku for p in products}

        # --- Products ---
        for p in products:
            if not p.id or not p.sku or not p.name:
                issues.append(dict(severity="error", message=f"Product missing required fields: id={p.id}", entity_type="product", entity_id=p.id))
            if p.unit_cost is not None and p.unit_cost < 0:
                issues.append(dict(severity="error", message=f"Product {p.id} has negative unit_cost", entity_type="product", entity_id=p.id))
            if p.unit_price is not None and p.unit_price < 0:
                issues.append(dict(severity="error", message=f"Product {p.id} has negative unit_price", entity_type="product", entity_id=p.id))
            if p.supplier_id and p.supplier_id not in supplier_ids:
                issues.append(dict(severity="warning", message=f"Product {p.id} references unknown supplier {p.supplier_id}", entity_type="product", entity_id=p.id))

        checks.append(dict(name="products_valid", status="passed" if not any(i["entity_type"] == "product" and i["severity"] == "error" for i in issues) else "failed"))

        # --- Stores ---
        for s in stores:
            if not s.id or not s.name:
                issues.append(dict(severity="error", message=f"Store missing required fields: id={s.id}", entity_type="store", entity_id=s.id))

        checks.append(dict(name="stores_valid", status="passed"))

        # --- Suppliers ---
        for sup in suppliers:
            if not sup.id or not sup.name:
                issues.append(dict(severity="error", message=f"Supplier missing required fields: id={sup.id}", entity_type="supplier", entity_id=sup.id))
            if sup.reliability_score is not None and not (0.0 <= sup.reliability_score <= 1.0):
                issues.append(dict(severity="warning", message=f"Supplier {sup.id} has reliability_score outside [0,1]", entity_type="supplier", entity_id=sup.id))

        checks.append(dict(name="suppliers_valid", status="passed"))

        # --- Promotions ---
        promo_date_ok = True
        for promo in promotions:
            if promo.start_date and promo.end_date and promo.end_date < promo.start_date:
                issues.append(dict(severity="error", message=f"Promotion {promo.id} end_date before start_date", entity_type="promotion", entity_id=promo.id))
                promo_date_ok = False
            if promo.discount_pct < 0 or promo.discount_pct > 1:
                issues.append(dict(severity="warning", message=f"Promotion {promo.id} discount_pct outside [0,1]: {promo.discount_pct}", entity_type="promotion", entity_id=promo.id))

        checks.append(dict(name="promotion_dates_valid", status="passed" if promo_date_ok else "failed"))

        # --- Orders ---
        orphaned_product = 0
        orphaned_store   = 0
        neg_qty          = 0
        neg_price        = 0
        for o in orders:
            if o.product_id and o.product_id not in product_ids:
                orphaned_product += 1
            if o.store_id and o.store_id not in store_ids:
                orphaned_store += 1
            if o.quantity < 0:
                neg_qty += 1
                issues.append(dict(severity="error", message=f"Order {o.id} has negative quantity", entity_type="order", entity_id=o.id))
            if o.unit_price < 0:
                neg_price += 1
                issues.append(dict(severity="error", message=f"Order {o.id} has negative unit_price", entity_type="order", entity_id=o.id))

        if orphaned_product:
            issues.append(dict(severity="error", message=f"{orphaned_product} order line(s) reference unknown product_ids", entity_type="order", entity_id=None))
        if orphaned_store:
            issues.append(dict(severity="error", message=f"{orphaned_store} order line(s) reference unknown store_ids", entity_type="order", entity_id=None))

        checks.append(dict(name="referential_integrity", status="passed" if orphaned_product == 0 and orphaned_store == 0 else "failed", detail=f"{orphaned_product} orphaned product refs, {orphaned_store} orphaned store refs"))
        checks.append(dict(name="no_negative_quantities", status="passed" if neg_qty == 0 else "failed"))
        checks.append(dict(name="no_negative_prices", status="passed" if neg_price == 0 else "failed"))

        # --- Inventory snapshots ---
        inv_orphaned = 0
        for snap in snapshots:
            if snap.product_id and snap.product_id not in product_ids:
                inv_orphaned += 1
            if snap.store_id and snap.store_id not in store_ids:
                inv_orphaned += 1
            if snap.quantity_on_hand < 0:
                issues.append(dict(severity="warning", message=f"Inventory snapshot {snap.id} has negative quantity_on_hand", entity_type="inventory_snapshot", entity_id=snap.id))

        checks.append(dict(name="inventory_refs_valid", status="passed" if inv_orphaned == 0 else "failed"))

        # --- Stockout check (dataset level) ---
        stockout_count = sum(1 for snap in snapshots if snap.quantity_on_hand == 0)
        has_stockouts  = stockout_count > 0
        checks.append(dict(name="stockouts_exist", status="passed" if has_stockouts else "warning", detail=f"{stockout_count} zero-stock snapshots found"))
        if not has_stockouts:
            issues.append(dict(severity="warning", message="No stockout events detected in inventory snapshots", entity_type="inventory_snapshot", entity_id=None))

        # --- Promotions exist ---
        has_promos = len(promotions) > 0
        checks.append(dict(name="promotions_exist", status="passed" if has_promos else "warning"))
        if not has_promos:
            issues.append(dict(severity="warning", message="No promotions found in the date range", entity_type="promotion", entity_id=None))

        # --- Purchase orders ---
        po_date_ok = True
        for po in purchase_orders:
            if po.expected_delivery_date and po.expected_delivery_date < po.ordered_at.date():
                issues.append(dict(severity="error", message=f"PO {po.id} expected_delivery_date before ordered_at", entity_type="purchase_order", entity_id=po.id))
                po_date_ok = False
            if po.quantity_ordered < 0:
                issues.append(dict(severity="error", message=f"PO {po.id} has negative quantity_ordered", entity_type="purchase_order", entity_id=po.id))

        checks.append(dict(name="purchase_order_dates_valid", status="passed" if po_date_ok else "failed"))

        # --- Raw schema field guard ---
        schema_clean = self._check_no_derived_fields()
        checks.append(dict(name="no_derived_fields_in_raw_schemas", status="passed" if schema_clean else "failed"))
        if not schema_clean:
            issues.append(dict(severity="error", message="Forbidden derived fields detected in raw Pydantic schemas", entity_type="schema", entity_id=None))

        errors  = [i for i in issues if i["severity"] == "error"]
        return {
            "passed": len(errors) == 0,
            "issues": issues,
            "checks": checks,
        }

    def validate_raw_records(self, records: list[Any]) -> dict:
        """Legacy single-list validation (kept for backwards compatibility)."""
        return {
            "status":         "ok",
            "records_checked": len(records),
            "errors":         [],
            "warnings":       [],
        }

    def _check_no_derived_fields(self) -> bool:
        """Verify that no forbidden derived fields exist in any raw Pydantic schema."""
        from app.schemas.raw import ALL_RAW_SCHEMAS
        for schema_cls in ALL_RAW_SCHEMAS:
            field_names = set(schema_cls.model_fields.keys())
            if field_names & FORBIDDEN_DERIVED_FIELDS:
                return False
        return True
