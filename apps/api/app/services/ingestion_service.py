"""
IngestionService — fetches raw records from a connector and persists them to the DB.

Flow:
  1. Create an IngestionRun record (status=running)
  2. Fetch all record types from the connector
  3. Validate via ValidationService
  4. Bulk-persist new records (skip existing by primary key)
  5. Emit PipelineEvents for validation issues
  6. Update IngestionRun to success/failed with final counts
"""

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.connectors.base import BaseCommerceConnector
from app.db.models import (
    RawProduct as DBProduct,
    RawStore as DBStore,
    RawOrder as DBOrder,
    RawInventorySnapshot as DBInventory,
    RawPromotion as DBPromotion,
    RawSupplier as DBSupplier,
    RawPurchaseOrder as DBPurchaseOrder,
    IngestionRun,
    PipelineEvent,
)
from app.schemas.raw import (
    RawProduct, RawStore, RawOrderLine, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
)
from app.services.validation_service import ValidationService
from app.utils.ids import new_id


class IngestionService:
    def __init__(self, connector: BaseCommerceConnector, db: Session) -> None:
        self.connector = connector
        self.db        = db
        self._validator = ValidationService()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        start_date: date,
        end_date: date,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Run a full ingestion for the given date range.

        Returns a summary dict with run_id, status, and per-type record counts.
        If dry_run=True, validation is performed but nothing is written to the DB.
        """
        run_id     = new_id()
        started_at = datetime.utcnow()

        if not dry_run:
            run_record = IngestionRun(
                id=run_id,
                connector=self.connector.connector_name,
                started_at=started_at,
                status="running",
                records_ingested=0,
            )
            self.db.add(run_record)
            self.db.commit()

        counts: dict[str, int] = {}
        validation_issues: list[dict] = []

        try:
            # --- Fetch ---
            products   = self.connector.fetch_products()
            stores     = self.connector.fetch_stores()
            suppliers  = self.connector.fetch_suppliers()
            promotions = self.connector.fetch_promotions(start_date, end_date)
            orders     = self.connector.fetch_orders(start_date, end_date)
            snapshots  = self.connector.fetch_inventory_snapshots(start_date, end_date)
            pos        = self.connector.fetch_purchase_orders(start_date, end_date)

            # --- Validate ---
            v_result = self._validator.validate_batch(
                products=products,
                stores=stores,
                suppliers=suppliers,
                promotions=promotions,
                orders=orders,
                snapshots=snapshots,
                purchase_orders=pos,
            )
            validation_issues = v_result.get("issues", [])

            # --- Persist ---
            if not dry_run:
                counts["products"]            = self._persist_products(products)
                counts["stores"]              = self._persist_stores(stores)
                counts["suppliers"]           = self._persist_suppliers(suppliers)
                counts["promotions"]          = self._persist_promotions(promotions)
                counts["orders"]              = self._persist_orders(orders)
                counts["inventory_snapshots"] = self._persist_inventory(snapshots)
                counts["purchase_orders"]     = self._persist_pos(pos)

                # Emit pipeline events for validation warnings/errors
                for issue in validation_issues:
                    self.db.add(PipelineEvent(
                        id=new_id(),
                        ingestion_run_id=run_id,
                        event_type="validation_issue",
                        severity=issue.get("severity", "warning"),
                        message=issue.get("message", ""),
                        entity_type=issue.get("entity_type"),
                        entity_id=issue.get("entity_id"),
                    ))

                # Finalize run record
                total = sum(counts.values())
                self.db.query(IngestionRun).filter(IngestionRun.id == run_id).update({
                    "status": "success",
                    "finished_at": datetime.utcnow(),
                    "records_ingested": total,
                    "run_metadata": {
                        "counts": counts,
                        "validation_issues": len(validation_issues),
                    },
                })
                self.db.commit()
            else:
                counts = {
                    "products":            len(products),
                    "stores":              len(stores),
                    "suppliers":           len(suppliers),
                    "promotions":          len(promotions),
                    "orders":              len(orders),
                    "inventory_snapshots": len(snapshots),
                    "purchase_orders":     len(pos),
                }

        except Exception as exc:
            if not dry_run:
                self.db.rollback()
                self.db.query(IngestionRun).filter(IngestionRun.id == run_id).update({
                    "status": "failed",
                    "finished_at": datetime.utcnow(),
                    "error_message": str(exc)[:500],
                })
                self.db.commit()
            raise

        return {
            "status":            "ok" if not dry_run else "dry_run",
            "run_id":            run_id,
            "connector":         self.connector.connector_name,
            "start_date":        str(start_date),
            "end_date":          str(end_date),
            "records_ingested":  sum(counts.values()),
            "counts":            counts,
            "validation_issues": len(validation_issues),
            "dry_run":           dry_run,
        }

    # ------------------------------------------------------------------
    # Reset helper — clears all raw tables then runs fresh ingestion
    # ------------------------------------------------------------------

    def reset_and_seed(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Clear all raw tables and re-seed from the connector."""
        self._clear_raw_tables()
        return self.run(start_date, end_date, dry_run=False)

    def _clear_raw_tables(self) -> None:
        # Delete in FK-safe order (children before parents)
        self.db.query(DBOrder).delete()
        self.db.query(DBInventory).delete()
        self.db.query(DBPurchaseOrder).delete()
        self.db.query(DBPromotion).delete()
        self.db.query(DBProduct).delete()
        self.db.query(DBStore).delete()
        self.db.query(DBSupplier).delete()
        self.db.query(PipelineEvent).delete()
        self.db.query(IngestionRun).delete()
        self.db.commit()

    # ------------------------------------------------------------------
    # Bulk persistence helpers
    # ------------------------------------------------------------------

    def _existing_ids(self, model_cls, ids: list[str]) -> set[str]:
        """Return set of IDs already present in the table, batched to avoid huge IN clauses."""
        existing: set[str] = set()
        batch = 500
        pk = list(model_cls.__table__.primary_key.columns)[0]
        for i in range(0, len(ids), batch):
            chunk = ids[i : i + batch]
            rows = self.db.query(pk).filter(pk.in_(chunk)).all()
            existing.update(r[0] for r in rows)
        return existing

    def _persist_products(self, records: list[RawProduct]) -> int:
        if not records:
            return 0
        existing = self._existing_ids(DBProduct, [r.id for r in records])
        new_rows = [r for r in records if r.id not in existing]
        if new_rows:
            self.db.bulk_insert_mappings(DBProduct, [
                dict(
                    id=r.id, external_id=r.external_id, sku=r.sku,
                    name=r.name, category=r.category, brand=r.brand,
                    supplier_id=r.supplier_id, unit_cost=r.unit_cost,
                    unit_price=r.unit_price, lead_time_days=r.lead_time_days,
                    is_active=r.is_active, attributes=r.attributes,
                    source_connector=r.source_connector,
                    ingested_at=r.ingested_at, raw_payload=r.raw_payload,
                ) for r in new_rows
            ])
            self.db.commit()
        return len(new_rows)

    def _persist_stores(self, records: list[RawStore]) -> int:
        if not records:
            return 0
        existing = self._existing_ids(DBStore, [r.id for r in records])
        new_rows = [r for r in records if r.id not in existing]
        if new_rows:
            self.db.bulk_insert_mappings(DBStore, [
                dict(
                    id=r.id, external_id=r.external_id, name=r.name,
                    region=r.region, country=r.country, timezone=r.timezone,
                    channel=r.channel, is_active=r.is_active,
                    source_connector=r.source_connector,
                    ingested_at=r.ingested_at, raw_payload=r.raw_payload,
                ) for r in new_rows
            ])
            self.db.commit()
        return len(new_rows)

    def _persist_suppliers(self, records: list[RawSupplier]) -> int:
        if not records:
            return 0
        existing = self._existing_ids(DBSupplier, [r.id for r in records])
        new_rows = [r for r in records if r.id not in existing]
        if new_rows:
            self.db.bulk_insert_mappings(DBSupplier, [
                dict(
                    id=r.id, external_id=r.external_id, name=r.name,
                    country=r.country,
                    lead_time_days_min=r.lead_time_days_min,
                    lead_time_days_max=r.lead_time_days_max,
                    reliability_score=r.reliability_score,
                    contact_email=r.contact_email,
                    source_connector=r.source_connector,
                    ingested_at=r.ingested_at, raw_payload=r.raw_payload,
                ) for r in new_rows
            ])
            self.db.commit()
        return len(new_rows)

    def _persist_promotions(self, records: list[RawPromotion]) -> int:
        if not records:
            return 0
        existing = self._existing_ids(DBPromotion, [r.id for r in records])
        new_rows = [r for r in records if r.id not in existing]
        if new_rows:
            self.db.bulk_insert_mappings(DBPromotion, [
                dict(
                    id=r.id, external_id=r.external_id, name=r.name,
                    promotion_type=r.promotion_type, discount_pct=r.discount_pct,
                    start_date=r.start_date, end_date=r.end_date,
                    applicable_skus=r.applicable_skus,
                    applicable_stores=r.applicable_stores,
                    source_connector=r.source_connector,
                    ingested_at=r.ingested_at, raw_payload=r.raw_payload,
                ) for r in new_rows
            ])
            self.db.commit()
        return len(new_rows)

    def _persist_orders(self, records: list[RawOrderLine]) -> int:
        if not records:
            return 0
        existing = self._existing_ids(DBOrder, [r.id for r in records])
        new_rows = [r for r in records if r.id not in existing]
        # Bulk insert in chunks to avoid large transactions
        chunk_size = 2000
        inserted = 0
        for i in range(0, len(new_rows), chunk_size):
            chunk = new_rows[i : i + chunk_size]
            self.db.bulk_insert_mappings(DBOrder, [
                dict(
                    id=r.id, external_order_id=r.external_order_id,
                    store_id=r.store_id, product_id=r.product_id,
                    ordered_at=r.ordered_at, order_date=r.order_date,
                    quantity=r.quantity, unit_price=r.unit_price,
                    discount_amount=r.discount_amount, currency=r.currency,
                    status=r.status, promotion_id=r.promotion_id,
                    source_connector=r.source_connector,
                    ingested_at=r.ingested_at, raw_payload=r.raw_payload,
                ) for r in chunk
            ])
            self.db.commit()
            inserted += len(chunk)
        return inserted

    def _persist_inventory(self, records: list[RawInventorySnapshot]) -> int:
        if not records:
            return 0
        existing = self._existing_ids(DBInventory, [r.id for r in records])
        new_rows = [r for r in records if r.id not in existing]
        chunk_size = 2000
        inserted = 0
        for i in range(0, len(new_rows), chunk_size):
            chunk = new_rows[i : i + chunk_size]
            self.db.bulk_insert_mappings(DBInventory, [
                dict(
                    id=r.id, store_id=r.store_id, product_id=r.product_id,
                    snapshot_date=r.snapshot_date,
                    quantity_on_hand=r.quantity_on_hand,
                    quantity_on_order=r.quantity_on_order,
                    quantity_reserved=r.quantity_reserved,
                    warehouse_location=r.warehouse_location,
                    source_connector=r.source_connector,
                    ingested_at=r.ingested_at, raw_payload=r.raw_payload,
                ) for r in chunk
            ])
            self.db.commit()
            inserted += len(chunk)
        return inserted

    def _persist_pos(self, records: list[RawPurchaseOrder]) -> int:
        if not records:
            return 0
        existing = self._existing_ids(DBPurchaseOrder, [r.id for r in records])
        new_rows = [r for r in records if r.id not in existing]
        if new_rows:
            self.db.bulk_insert_mappings(DBPurchaseOrder, [
                dict(
                    id=r.id, external_po_id=r.external_po_id,
                    supplier_id=r.supplier_id, product_id=r.product_id,
                    store_id=r.store_id, ordered_at=r.ordered_at,
                    expected_delivery_date=r.expected_delivery_date,
                    quantity_ordered=r.quantity_ordered,
                    unit_cost=r.unit_cost, status=r.status,
                    source_connector=r.source_connector,
                    ingested_at=r.ingested_at, raw_payload=r.raw_payload,
                ) for r in new_rows
            ])
            self.db.commit()
        return len(new_rows)
