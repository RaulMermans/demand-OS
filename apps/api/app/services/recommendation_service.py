"""
RecommendationService — generates reorder recommendations from stockout risks.

Sprint 7: Full implementation.

Pipeline:
  stockout_risks (from a completed forward_planning risk run)
    + raw_products   (unit_cost, unit_price)
    → RecommendationService.run_reorder_recommendations()
    → recommendation_runs table  (audit record)
    → reorder_recommendations table  (one row per rec_run × product × store)

Key formulas (all deterministic — no LLM):

  inventory_position        = current_available_units + inbound_units_within_horizon
  lead_time_demand_units    = average_daily_forecast × supplier_lead_time_days
  reorder_point_units       = lead_time_demand_units + safety_stock_units
  recommended_units         = max(0, reorder_point_units - inventory_position)
  recommended_units_rounded = ceil(raw / order_multiple) × order_multiple
    clamped to min_order_quantity when recommended_units > 0
  estimated_order_cost      = recommended_units_rounded × unit_cost
  estimated_lost_sales_avoided = min(lost_sales_value_estimate,
                                     recommended_units_rounded × unit_price)
  (estimated_lost_sales_avoided is an approximation, not a guaranteed recovery)

Urgency rules (deterministic):
  critical: risk_tier=critical  OR  days_until_stockout <= 7
  high:     risk_tier=high  OR  days_until_stockout <= supplier_lead_time_days
  medium:   risk_tier=medium  OR  recommended_units_rounded > 0
  low:      otherwise (risk_tier=low and recommended_units_rounded == 0)

Supplier / order constraints:
  min_order_quantity defaults to 1.0 (no separate constraint table in Sprint 7)
  order_multiple defaults to 1.0

Idempotency: clear-before-rewrite for same source_risk_run_id.

No external side effects: no purchase orders, no emails, no external API calls.

Reference: lead-time demand, safety stock, reorder point formulas from standard
inventory planning literature (Silver, Pyke, Thomas 2017; Brown 1959).
"""

import logging
import math
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    StockoutRiskRun, StockoutRisk, RawProduct,
    RecommendationRun, ReorderRecommendation,
)

logger = logging.getLogger(__name__)

# Default order constraints (no supplier-specific table in Sprint 7)
_DEFAULT_ORDER_MULTIPLE = 1.0
_DEFAULT_MIN_ORDER_QTY = 1.0

VALID_URGENCY = {"critical", "high", "medium", "low"}
VALID_STATUS = {"open", "reviewed", "approved_internal", "ignored", "resolved"}

# Tier ordering for urgency ranking (lower = more urgent)
_URGENCY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_reorder_recommendations(
        self,
        risk_run_id: Optional[str] = None,
        include_low_risk: bool = False,
    ) -> dict:
        """
        Generate reorder recommendations from a completed stockout risk run.

        Selects the latest completed forward_planning risk run when risk_run_id
        is not provided. Persists a RecommendationRun and ReorderRecommendation
        rows. Returns a dict summary suitable for API response serialization.

        Recommendation-only: no purchase orders, no external calls.
        """
        run_id = f"rec-run-{uuid.uuid4()}"
        rec_run = RecommendationRun(
            id=run_id,
            mode="recommendation_only",
            status="running",
            started_at=datetime.utcnow(),
            config_json={
                "requested_risk_run_id": risk_run_id,
                "include_low_risk": include_low_risk,
            },
        )
        self.db.add(rec_run)
        self.db.flush()

        try:
            # 1. Select risk run
            risk_run = self._select_risk_run(risk_run_id)
            if risk_run is None:
                rec_run.status = "failed"
                rec_run.error_message = (
                    "No usable stockout risk run found. "
                    "Run POST /api/risks/run before recommendations."
                )
                rec_run.completed_at = datetime.utcnow()
                self.db.commit()
                return {
                    "status": "failed",
                    "recommendation_run_id": run_id,
                    "error": rec_run.error_message,
                }

            rec_run.source_risk_run_id = risk_run.id
            rec_run.source_forecast_run_id = risk_run.source_forecast_run_id
            rec_run.as_of_date = risk_run.as_of_date
            rec_run.horizon_days = risk_run.risk_horizon_days
            self.db.flush()

            # 2. Load risk rows
            risk_rows = self._load_risk_rows(risk_run, include_low_risk)

            # 3. Load product info
            product_map = self._load_product_info()

            # 4. Idempotency: clear previous recommendation runs for this risk run
            self._clear_previous_runs(risk_run.id, current_run_id=run_id)

            # 5. Compute recommendation rows
            rec_rows, urgency_counts = self._compute_all_recommendations(
                risk_rows=risk_rows,
                product_map=product_map,
                rec_run_id=run_id,
            )

            # 6. Persist
            self.db.bulk_insert_mappings(ReorderRecommendation, rec_rows)
            self.db.flush()

            # 7. Aggregate totals
            total_recommended_units = sum(
                r.get("recommended_units_rounded") or 0.0 for r in rec_rows
            )
            total_estimated_value = sum(
                r.get("estimated_order_cost") or 0.0 for r in rec_rows
            )

            # 8. Update run record
            rec_run.status = "completed"
            rec_run.completed_at = datetime.utcnow()
            rec_run.rows_created = len(rec_rows)
            rec_run.critical_count = urgency_counts.get("critical", 0)
            rec_run.high_count = urgency_counts.get("high", 0)
            rec_run.medium_count = urgency_counts.get("medium", 0)
            rec_run.low_count = urgency_counts.get("low", 0)
            rec_run.total_recommended_units = total_recommended_units
            rec_run.total_estimated_value = total_estimated_value
            rec_run.checks_json = self._build_checks(len(rec_rows), urgency_counts)
            self.db.commit()

            return {
                "status": "completed",
                "recommendation_run_id": run_id,
                "source_risk_run_id": risk_run.id,
                "rows_created": len(rec_rows),
                "summary": {
                    "critical": urgency_counts.get("critical", 0),
                    "high": urgency_counts.get("high", 0),
                    "medium": urgency_counts.get("medium", 0),
                    "low": urgency_counts.get("low", 0),
                    "total_recommended_units": total_recommended_units,
                    "total_estimated_order_cost": total_estimated_value,
                },
            }

        except Exception as exc:
            logger.exception("Recommendation run %s failed", run_id)
            self.db.rollback()
            rec_run = RecommendationRun(
                id=run_id,
                mode="recommendation_only",
                status="failed",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                error_message=str(exc),
            )
            self.db.add(rec_run)
            self.db.commit()
            raise

    # ------------------------------------------------------------------
    # Risk run selection
    # ------------------------------------------------------------------

    def _select_risk_run(self, risk_run_id: Optional[str]) -> Optional[StockoutRiskRun]:
        if risk_run_id:
            return (
                self.db.query(StockoutRiskRun)
                .filter(
                    StockoutRiskRun.id == risk_run_id,
                    StockoutRiskRun.status == "completed",
                )
                .first()
            )
        # Prefer latest completed forward_planning run
        run = (
            self.db.query(StockoutRiskRun)
            .filter(
                StockoutRiskRun.status == "completed",
                StockoutRiskRun.mode == "forward_planning",
            )
            .order_by(StockoutRiskRun.started_at.desc())
            .first()
        )
        if run:
            return run
        # Fall back to any completed risk run
        return (
            self.db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.started_at.desc())
            .first()
        )

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_risk_rows(
        self, risk_run: StockoutRiskRun, include_low_risk: bool
    ) -> list[StockoutRisk]:
        query = (
            self.db.query(StockoutRisk)
            .filter(StockoutRisk.risk_run_id == risk_run.id)
        )
        if not include_low_risk:
            query = query.filter(
                StockoutRisk.risk_tier.in_(["critical", "high", "medium"])
            )
        return query.all()

    def _load_product_info(self) -> dict:
        """Returns {product_id: {unit_cost, unit_price}} from raw_products."""
        rows = self.db.query(RawProduct).all()
        return {
            r.id: {
                "unit_cost": _safe_float(r.unit_cost) or 0.0,
                "unit_price": _safe_float(r.unit_price) or 0.0,
            }
            for r in rows
        }

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def _compute_all_recommendations(
        self,
        risk_rows: list[StockoutRisk],
        product_map: dict,
        rec_run_id: str,
    ) -> tuple[list[dict], dict]:
        rec_rows = []
        urgency_counts: dict = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        now = datetime.utcnow()

        for risk in risk_rows:
            prod = product_map.get(risk.product_id, {})
            row = self._compute_one_recommendation(risk, prod, rec_run_id, now)
            rec_rows.append(row)
            urgency = row.get("urgency", "low")
            urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1

        return rec_rows, urgency_counts

    def _compute_one_recommendation(
        self,
        risk: StockoutRisk,
        prod: dict,
        rec_run_id: str,
        now: datetime,
    ) -> dict:
        unit_cost = prod.get("unit_cost", 0.0)
        unit_price = prod.get("unit_price", 0.0)

        # Inventory position
        available = _safe_float(risk.current_available_units) or 0.0
        inbound = _safe_float(risk.inbound_units_within_horizon) or 0.0
        inventory_position = available + inbound

        # Lead-time demand
        avg_daily = _safe_float(risk.average_daily_forecast) or 0.0
        lead_time_days = risk.supplier_lead_time_days or 0
        lead_time_demand = avg_daily * lead_time_days

        # Safety stock (from risk row — already computed by StockoutService)
        safety_stock = _safe_float(risk.safety_stock_units) or 0.0

        # Reorder point
        reorder_point = lead_time_demand + safety_stock

        # Recommended units (raw)
        recommended_raw = max(0.0, reorder_point - inventory_position)

        # Round to order multiple; apply min order quantity
        order_multiple = _DEFAULT_ORDER_MULTIPLE
        min_order_qty = _DEFAULT_MIN_ORDER_QTY
        recommended_rounded = self._round_recommended_units(
            recommended_raw, order_multiple, min_order_qty
        )

        # Costs
        estimated_order_cost = recommended_rounded * unit_cost
        lost_sales_value = _safe_float(risk.lost_sales_value_estimate) or 0.0
        estimated_lost_sales_avoided = min(
            lost_sales_value, recommended_rounded * unit_price
        )

        # Urgency
        urgency = self._assign_urgency(
            risk_tier=risk.risk_tier or "unknown",
            days_until_stockout=_safe_float(risk.days_until_stockout),
            lead_time_days=lead_time_days,
            recommended_rounded=recommended_rounded,
        )

        # Reason
        reason = self._generate_reason(
            urgency=urgency,
            risk_tier=risk.risk_tier or "unknown",
            recommended_rounded=recommended_rounded,
            lead_time_days=lead_time_days,
            safety_stock=safety_stock,
            days_until_stockout=_safe_float(risk.days_until_stockout),
        )

        # Confidence
        confidence = self._assign_confidence(risk)

        return {
            "id": str(uuid.uuid4()),
            "recommendation_run_id": rec_run_id,
            "source_risk_run_id": risk.risk_run_id,
            "source_risk_id": risk.id,
            "as_of_date": risk.as_of_date,
            "product_id": risk.product_id,
            "store_id": risk.store_id,
            "category": risk.category,
            "subcategory": risk.subcategory,
            "supplier_id": risk.supplier_id,
            "risk_tier": risk.risk_tier,
            "risk_score": _safe_float(risk.risk_score),
            "expected_stockout_date": risk.expected_stockout_date,
            "days_until_stockout": _safe_float(risk.days_until_stockout),
            "current_available_units": available,
            "inbound_units_within_horizon": inbound,
            "inventory_position": inventory_position,
            "supplier_lead_time_days": lead_time_days,
            "supplier_reliability_score": _safe_float(risk.supplier_reliability_score),
            "forecast_demand_p50": _safe_float(risk.forecast_demand_p50),
            "forecast_demand_p90": _safe_float(risk.forecast_demand_p90),
            "lead_time_demand_units": lead_time_demand,
            "safety_stock_units": safety_stock,
            "reorder_point_units": reorder_point,
            "recommended_units": recommended_raw,
            "recommended_units_rounded": recommended_rounded,
            "min_order_quantity": min_order_qty,
            "order_multiple": order_multiple,
            "estimated_order_cost": estimated_order_cost,
            "estimated_lost_sales_value": lost_sales_value,
            "estimated_lost_sales_avoided": estimated_lost_sales_avoided,
            "urgency": urgency,
            "recommendation_reason": reason,
            "confidence_level": confidence,
            "status": "open",
            "reviewed_at": None,
            "reviewed_by": None,
            "review_note": None,
            "created_at": now,
            "updated_at": now,
        }

    # ------------------------------------------------------------------
    # Formula helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _round_recommended_units(
        raw_units: float,
        order_multiple: float,
        min_order_qty: float,
    ) -> float:
        if raw_units <= 0.0:
            return 0.0
        multiple = order_multiple if order_multiple > 0 else 1.0
        rounded = math.ceil(raw_units / multiple) * multiple
        return max(rounded, min_order_qty)

    @staticmethod
    def _assign_urgency(
        risk_tier: str,
        days_until_stockout: Optional[float],
        lead_time_days: int,
        recommended_rounded: float,
    ) -> str:
        if risk_tier == "critical":
            return "critical"
        if days_until_stockout is not None and days_until_stockout <= 7:
            return "critical"
        if risk_tier == "high":
            return "high"
        if (
            days_until_stockout is not None
            and lead_time_days > 0
            and days_until_stockout <= lead_time_days
        ):
            return "high"
        if risk_tier == "medium":
            return "medium"
        if recommended_rounded > 0:
            return "medium"
        return "low"

    @staticmethod
    def _generate_reason(
        urgency: str,
        risk_tier: str,
        recommended_rounded: float,
        lead_time_days: int,
        safety_stock: float,
        days_until_stockout: Optional[float],
    ) -> str:
        units_str = f"{int(recommended_rounded)}" if recommended_rounded > 0 else "0"
        if urgency == "critical":
            if days_until_stockout is not None:
                return (
                    f"Critical stockout risk: projected demand exceeds inventory in "
                    f"{days_until_stockout:.1f} days, before supplier lead time of "
                    f"{lead_time_days} days. "
                    f"Recommend {units_str} units to cover lead-time demand plus safety stock."
                )
            return (
                f"Critical stockout risk: projected demand exceeds inventory "
                f"before supplier lead time of {lead_time_days} days. "
                f"Recommend {units_str} units to cover lead-time demand plus safety stock."
            )
        if urgency == "high":
            return (
                f"High risk: current inventory position covers expected demand "
                f"but does not meet safety-stock threshold ({safety_stock:.1f} units). "
                f"Recommend {units_str} units."
            )
        if urgency == "medium":
            if recommended_rounded > 0:
                return (
                    f"Medium risk: inventory is below reorder point. "
                    f"Recommend {units_str} units to restore safety buffer."
                )
            return (
                "Medium risk: inventory is near the reorder threshold. "
                "No immediate reorder required but monitor closely."
            )
        return (
            "Low risk: inventory covers forecasted demand and safety stock. "
            "No reorder recommended at this time."
        )

    @staticmethod
    def _assign_confidence(risk: StockoutRisk) -> str:
        has_forecast = risk.forecast_demand_p50 is not None
        has_inventory = risk.current_available_units is not None
        has_supplier = risk.supplier_lead_time_days is not None
        has_p90 = risk.forecast_demand_p90 is not None
        reliability = _safe_float(risk.supplier_reliability_score)
        low_reliability = reliability is not None and reliability < 0.85

        if not has_forecast or not has_inventory:
            return "unknown"
        if has_forecast and has_inventory and has_supplier and risk.risk_tier != "unknown":
            if not has_p90 or low_reliability:
                return "low"
            return "high"
        if has_forecast and has_inventory:
            return "medium"
        return "low"

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def _clear_previous_runs(self, risk_run_id: str, current_run_id: str) -> None:
        prev_runs = (
            self.db.query(RecommendationRun)
            .filter(
                RecommendationRun.source_risk_run_id == risk_run_id,
                RecommendationRun.id != current_run_id,
                RecommendationRun.status == "completed",
            )
            .all()
        )
        for prev in prev_runs:
            self.db.query(ReorderRecommendation).filter(
                ReorderRecommendation.recommendation_run_id == prev.id
            ).delete(synchronize_session=False)
            self.db.delete(prev)
        if prev_runs:
            self.db.flush()

    # ------------------------------------------------------------------
    # Validation checks
    # ------------------------------------------------------------------

    def _build_checks(self, rows_created: int, urgency_counts: dict) -> list:
        return [
            {
                "name": "rows_created",
                "status": "passed" if rows_created > 0 else "warning",
                "detail": f"{rows_created} recommendation rows",
            },
            {
                "name": "critical_count",
                "status": "passed",
                "detail": f"{urgency_counts.get('critical', 0)} critical",
            },
            {
                "name": "high_count",
                "status": "passed",
                "detail": f"{urgency_counts.get('high', 0)} high",
            },
            {
                "name": "no_external_side_effects",
                "status": "passed",
                "detail": "Recommendation-only mode: no purchase orders created.",
            },
        ]
