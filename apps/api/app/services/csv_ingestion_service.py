"""
CsvIngestionService — parses validated CSV bytes and inserts raw records.

Flow:
  1. Re-validate (fast) to catch any last-minute issues.
  2. Parse rows into raw Pydantic records.
  3. Persist via IngestionService helpers.
  4. Create / update CsvUploadRun audit row.

FK-safe insert order is preserved by calling entity-specific helpers
in the same order as IngestionService.
"""

import csv
import io
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    CsvUploadRun,
    RawProduct as DBProduct,
    RawStore as DBStore,
    RawOrder as DBOrder,
    RawInventorySnapshot as DBInventory,
    RawPromotion as DBPromotion,
    RawSupplier as DBSupplier,
    RawPurchaseOrder as DBPurchaseOrder,
)
from app.utils.ids import new_id
from app.validation.csv_validators import validate_csv_bytes, ENTITY_SCHEMAS


def _parse_date(val: str) -> date | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d",):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            pass
    return None


def _parse_datetime(val: str) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val.strip(), fmt)
        except ValueError:
            pass
    return None


def _float(val: str | None, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


def _int(val: str | None, default: int | None = None) -> int | None:
    try:
        return int(val) if val else default
    except (ValueError, TypeError):
        return default


def _bool(val: str | None, default: bool = True) -> bool:
    if not val:
        return default
    return val.strip().lower() not in ("false", "0", "no", "f")


class CsvIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest(
        self,
        raw_bytes: bytes,
        entity_type: str,
        filename: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Validate and ingest CSV bytes for the given entity type.

        Returns a result dict with upload_id, status, counts, and errors.
        If dry_run=True, no DB writes are performed.
        """
        upload_id = new_id()
        started = datetime.utcnow()

        # Validate first
        v = validate_csv_bytes(raw_bytes, entity_type)

        if not v["is_valid"]:
            if not dry_run:
                run = CsvUploadRun(
                    id=upload_id,
                    entity_type=entity_type,
                    filename=filename,
                    status="failed",
                    row_count=v["row_count"],
                    valid_row_count=v["valid_row_count"],
                    invalid_row_count=v["invalid_row_count"],
                    error_summary=v["errors"][:50],
                    created_at=started,
                    completed_at=datetime.utcnow(),
                )
                self.db.add(run)
                self.db.commit()
            return {
                "upload_id": upload_id,
                "entity_type": entity_type,
                "filename": filename,
                "status": "failed",
                "row_count": v["row_count"],
                "valid_row_count": v["valid_row_count"],
                "invalid_row_count": v["invalid_row_count"],
                "records_inserted": 0,
                "error_summary": v["errors"][:50],
                "dry_run": dry_run,
            }

        text = raw_bytes.decode("utf-8-sig", errors="replace")
        rows = list(csv.DictReader(io.StringIO(text)))

        records_inserted = 0
        if not dry_run:
            records_inserted = self._persist(entity_type, rows)

        status = "completed" if not dry_run else "dry_run"
        completed = datetime.utcnow()

        if not dry_run:
            run = CsvUploadRun(
                id=upload_id,
                entity_type=entity_type,
                filename=filename,
                status=status,
                row_count=v["row_count"],
                valid_row_count=v["valid_row_count"],
                invalid_row_count=0,
                error_summary=[],
                created_at=started,
                completed_at=completed,
            )
            self.db.add(run)
            self.db.commit()

        return {
            "upload_id": upload_id,
            "entity_type": entity_type,
            "filename": filename,
            "status": status,
            "row_count": v["row_count"],
            "valid_row_count": v["valid_row_count"],
            "invalid_row_count": 0,
            "records_inserted": records_inserted,
            "error_summary": [],
            "dry_run": dry_run,
        }

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _persist(self, entity_type: str, rows: list[dict]) -> int:
        handlers = {
            "products": self._persist_products,
            "stores": self._persist_stores,
            "suppliers": self._persist_suppliers,
            "promotions": self._persist_promotions,
            "orders": self._persist_orders,
            "inventory_snapshots": self._persist_inventory,
            "purchase_orders": self._persist_pos,
        }
        fn = handlers.get(entity_type)
        if fn is None:
            return 0
        return fn(rows)

    def _existing_ids(self, model_cls, ids: list[str]) -> set[str]:
        pk = list(model_cls.__table__.primary_key.columns)[0]
        existing: set[str] = set()
        for i in range(0, len(ids), 500):
            chunk = ids[i : i + 500]
            rows = self.db.query(pk).filter(pk.in_(chunk)).all()
            existing.update(r[0] for r in rows)
        return existing

    def _persist_products(self, rows: list[dict]) -> int:
        existing = self._existing_ids(DBProduct, [r.get("id", "") for r in rows])
        new_rows = [r for r in rows if r.get("id", "") not in existing]
        if not new_rows:
            return 0
        now = datetime.utcnow()
        self.db.bulk_insert_mappings(DBProduct, [
            dict(
                id=r["id"], external_id=r["external_id"], sku=r["sku"],
                name=r["name"], category=r.get("category"),
                brand=r.get("brand"), supplier_id=r.get("supplier_id") or None,
                unit_cost=_float(r.get("unit_cost"), None),
                unit_price=_float(r.get("unit_price"), None),
                lead_time_days=_int(r.get("lead_time_days")),
                is_active=_bool(r.get("is_active")),
                attributes={}, source_connector=r["source_connector"],
                ingested_at=now, raw_payload=None,
            ) for r in new_rows
        ])
        self.db.commit()
        return len(new_rows)

    def _persist_stores(self, rows: list[dict]) -> int:
        existing = self._existing_ids(DBStore, [r.get("id", "") for r in rows])
        new_rows = [r for r in rows if r.get("id", "") not in existing]
        if not new_rows:
            return 0
        now = datetime.utcnow()
        self.db.bulk_insert_mappings(DBStore, [
            dict(
                id=r["id"], external_id=r["external_id"], name=r["name"],
                region=r.get("region"), country=r.get("country"),
                timezone=r.get("timezone"), channel=r.get("channel"),
                is_active=_bool(r.get("is_active")),
                source_connector=r["source_connector"],
                ingested_at=now, raw_payload=None,
            ) for r in new_rows
        ])
        self.db.commit()
        return len(new_rows)

    def _persist_suppliers(self, rows: list[dict]) -> int:
        existing = self._existing_ids(DBSupplier, [r.get("id", "") for r in rows])
        new_rows = [r for r in rows if r.get("id", "") not in existing]
        if not new_rows:
            return 0
        now = datetime.utcnow()
        self.db.bulk_insert_mappings(DBSupplier, [
            dict(
                id=r["id"], external_id=r["external_id"], name=r["name"],
                country=r.get("country"),
                lead_time_days_min=_int(r.get("lead_time_days_min")),
                lead_time_days_max=_int(r.get("lead_time_days_max")),
                reliability_score=_float(r.get("reliability_score"), None),
                contact_email=r.get("contact_email"),
                source_connector=r["source_connector"],
                ingested_at=now, raw_payload=None,
            ) for r in new_rows
        ])
        self.db.commit()
        return len(new_rows)

    def _persist_promotions(self, rows: list[dict]) -> int:
        existing = self._existing_ids(DBPromotion, [r.get("id", "") for r in rows])
        new_rows = [r for r in rows if r.get("id", "") not in existing]
        if not new_rows:
            return 0
        now = datetime.utcnow()
        self.db.bulk_insert_mappings(DBPromotion, [
            dict(
                id=r["id"], external_id=r["external_id"],
                name=r.get("name"), promotion_type=r.get("promotion_type"),
                discount_pct=_float(r.get("discount_pct"), 0.0),
                start_date=_parse_date(r.get("start_date", "")),
                end_date=_parse_date(r.get("end_date", "")),
                applicable_skus=[], applicable_stores=[],
                source_connector=r["source_connector"],
                ingested_at=now, raw_payload=None,
            ) for r in new_rows
        ])
        self.db.commit()
        return len(new_rows)

    def _persist_orders(self, rows: list[dict]) -> int:
        existing = self._existing_ids(DBOrder, [r.get("id", "") for r in rows])
        new_rows = [r for r in rows if r.get("id", "") not in existing]
        if not new_rows:
            return 0
        now = datetime.utcnow()
        chunk_size = 2000
        inserted = 0
        for i in range(0, len(new_rows), chunk_size):
            chunk = new_rows[i : i + chunk_size]
            self.db.bulk_insert_mappings(DBOrder, [
                dict(
                    id=r["id"], external_order_id=r["external_order_id"],
                    store_id=r.get("store_id") or None,
                    product_id=r.get("product_id") or None,
                    ordered_at=_parse_datetime(r.get("ordered_at", "")) or datetime.utcnow(),
                    order_date=_parse_date(r.get("order_date", "")) or date.today(),
                    quantity=_float(r.get("quantity"), 0.0),
                    unit_price=_float(r.get("unit_price"), 0.0),
                    discount_amount=_float(r.get("discount_amount"), 0.0),
                    currency=r.get("currency", "USD") or "USD",
                    status=r.get("status"),
                    promotion_id=r.get("promotion_id") or None,
                    source_connector=r["source_connector"],
                    ingested_at=now, raw_payload=None,
                ) for r in chunk
            ])
            self.db.commit()
            inserted += len(chunk)
        return inserted

    def _persist_inventory(self, rows: list[dict]) -> int:
        existing = self._existing_ids(DBInventory, [r.get("id", "") for r in rows])
        new_rows = [r for r in rows if r.get("id", "") not in existing]
        if not new_rows:
            return 0
        now = datetime.utcnow()
        chunk_size = 2000
        inserted = 0
        for i in range(0, len(new_rows), chunk_size):
            chunk = new_rows[i : i + chunk_size]
            self.db.bulk_insert_mappings(DBInventory, [
                dict(
                    id=r["id"],
                    store_id=r.get("store_id") or None,
                    product_id=r.get("product_id") or None,
                    snapshot_date=_parse_date(r.get("snapshot_date", "")) or date.today(),
                    quantity_on_hand=_float(r.get("quantity_on_hand"), 0.0),
                    quantity_on_order=_float(r.get("quantity_on_order"), 0.0),
                    quantity_reserved=_float(r.get("quantity_reserved"), 0.0),
                    warehouse_location=r.get("warehouse_location"),
                    source_connector=r["source_connector"],
                    ingested_at=now, raw_payload=None,
                ) for r in chunk
            ])
            self.db.commit()
            inserted += len(chunk)
        return inserted

    def _persist_pos(self, rows: list[dict]) -> int:
        existing = self._existing_ids(DBPurchaseOrder, [r.get("id", "") for r in rows])
        new_rows = [r for r in rows if r.get("id", "") not in existing]
        if not new_rows:
            return 0
        now = datetime.utcnow()
        self.db.bulk_insert_mappings(DBPurchaseOrder, [
            dict(
                id=r["id"], external_po_id=r["external_po_id"],
                supplier_id=r.get("supplier_id") or None,
                product_id=r.get("product_id") or None,
                store_id=r.get("store_id") or None,
                ordered_at=_parse_datetime(r.get("ordered_at", "")) or datetime.utcnow(),
                expected_delivery_date=_parse_date(r.get("expected_delivery_date", "")),
                quantity_ordered=_float(r.get("quantity_ordered"), 0.0),
                unit_cost=_float(r.get("unit_cost"), None),
                status=r.get("status"),
                source_connector=r["source_connector"],
                ingested_at=now, raw_payload=None,
            ) for r in new_rows
        ])
        self.db.commit()
        return len(new_rows)
