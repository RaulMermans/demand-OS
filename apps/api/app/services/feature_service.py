"""
FeatureService — engineers leakage-safe features from product_store_daily.

Pipeline:
  product_store_daily → lag / rolling / calendar / price / inventory / lifecycle
                     → feature_matrix

Leakage-safety rules:
  Lag and rolling features use dates strictly before D (shift=1 before rolling).
  Calendar, promotion, and inventory features use state known on D.
  target_units_sold is the historical supervised label for D.
  Pre-launch rows (days_since_launch < 0) are excluded.

Approach inspired by Nixtla/mlforecast lag/rolling patterns and M5-style
retail feature design. All features are computed internally — never accepted
as connector input.
"""

import logging
import math
from datetime import datetime, date
from uuid import uuid4

import pandas as pd

from sqlalchemy.orm import Session

from app.db.models import (
    ProductStoreDaily, RawProduct, FeatureMatrix, FeatureRun,
)

logger = logging.getLogger(__name__)

_FORBIDDEN_FEATURE_COLS = {
    "forecast", "forecast_7d", "forecast_28d", "forecast_90d",
    "p10", "p50", "p90", "risk_score", "stockout_risk",
    "recommended_units", "reorder_quantity", "future_demand", "future_units_sold",
}

_AGE_BUCKETS = [
    (30, "new_0_30"),
    (90, "ramp_31_90"),
    (365, "mature_91_365"),
]


def _age_bucket(days: int) -> str:
    for threshold, label in _AGE_BUCKETS:
        if days <= threshold:
            return label
    return "established_365_plus"


class FeatureService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build_feature_matrix(
        self,
        source_aggregation_run_id: str | None = None,
        max_lag_days: int = 28,
    ) -> dict:
        """Build a complete, leakage-safe feature matrix from product_store_daily."""
        run = FeatureRun(
            id=str(uuid4()),
            source_aggregation_run_id=source_aggregation_run_id,
            status="running",
            started_at=datetime.utcnow(),
            max_lag_days=max_lag_days,
        )
        self.db.add(run)
        self.db.flush()

        try:
            df = self._load_psd_df()
            if df.empty:
                run.status = "failed"
                run.error_message = "product_store_daily is empty — run aggregation first"
                run.completed_at = datetime.utcnow()
                self.db.commit()
                return {"status": "no_data",
                        "message": "No product_store_daily rows. Run POST /api/aggregation/run first.",
                        "run_id": run.id}

            product_meta = self._load_product_meta()
            df = self._merge_product_meta(df, product_meta)
            df = df.sort_values(["product_id", "store_id", "date"]).reset_index(drop=True)

            df = self._add_lag_features(df, max_lag_days)
            df = self._add_rolling_features(df)
            df = self._add_calendar_features(df)
            df = self._add_price_features(df)
            df = self._add_lifecycle_features(df)

            # Exclude pre-launch rows
            df = df[df["days_since_launch"] >= 0].copy()

            checks = self._run_checks(df)
            n = self._clear_and_write(df, run.id, source_aggregation_run_id)

            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.rows_created = n
            run.date_min = df["date"].min() if n > 0 else None
            run.date_max = df["date"].max() if n > 0 else None
            run.checks_json = checks
            self.db.commit()

            return {
                "status": "completed",
                "run_id": run.id,
                "rows_created": n,
                "date_min": str(run.date_min) if run.date_min else None,
                "date_max": str(run.date_max) if run.date_max else None,
                "max_lag_days": max_lag_days,
                "checks": checks,
            }
        except Exception as exc:
            self.db.rollback()
            logger.exception("Feature build %s failed", run.id)
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.error_message = str(exc)
            self.db.add(run)
            self.db.commit()
            return {"status": "failed", "run_id": run.id, "error": str(exc)}

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_psd_df(self) -> pd.DataFrame:
        rows = self.db.query(ProductStoreDaily).all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([{
            "product_id": r.product_id, "store_id": r.store_id, "date": r.date,
            "units_sold": r.units_sold or 0.0, "net_revenue": r.net_revenue or 0.0,
            "discount_amount": r.discount_amount or 0.0,
            "promotion_active": bool(r.promotion_active),
            "discount_pct": r.discount_pct or 0.0,
            "on_hand_units": r.on_hand_units, "stockout_flag": bool(r.stockout_flag),
            "days_of_supply": r.days_of_supply,
            "sku": r.sku, "category": r.category, "channel": r.channel,
            "source_run_id": r.source_run_id,
        } for r in rows])

    def _load_product_meta(self) -> dict:
        """Return {product_id: {unit_price, unit_cost, supplier_id, launch_date}}."""
        products = self.db.query(RawProduct).all()
        meta = {}
        for p in products:
            ld_str = (p.attributes or {}).get("launch_date", "")
            try:
                launch = date.fromisoformat(ld_str) if ld_str else None
            except ValueError:
                launch = None
            meta[p.id] = {
                "unit_price": p.unit_price,
                "unit_cost": p.unit_cost,
                "supplier_id": p.supplier_id,
                "launch_date": launch,
            }
        return meta

    def _merge_product_meta(self, df: pd.DataFrame, meta: dict) -> pd.DataFrame:
        df["unit_price"] = df["product_id"].map(lambda pid: (meta.get(pid) or {}).get("unit_price"))
        df["unit_cost"] = df["product_id"].map(lambda pid: (meta.get(pid) or {}).get("unit_cost"))
        df["supplier_id"] = df["product_id"].map(lambda pid: (meta.get(pid) or {}).get("supplier_id"))
        df["launch_date"] = df["product_id"].map(lambda pid: (meta.get(pid) or {}).get("launch_date"))
        return df

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def _add_lag_features(self, df: pd.DataFrame, max_lag_days: int) -> pd.DataFrame:
        grp = df.groupby(["product_id", "store_id"])["units_sold"]
        for lag in [1, 7, 14, 28]:
            if lag <= max_lag_days:
                df[f"lag_units_{lag}d"] = grp.transform(lambda x: x.shift(lag))
            else:
                df[f"lag_units_{lag}d"] = None
        return df

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        def _rmean(x, w):
            return x.shift(1).rolling(w, min_periods=1).mean()

        def _rstd(x, w):
            return x.shift(1).rolling(w, min_periods=2).std()

        grp_u = df.groupby(["product_id", "store_id"])["units_sold"]
        grp_r = df.groupby(["product_id", "store_id"])["net_revenue"]

        df["rolling_units_mean_7d"] = grp_u.transform(lambda x: _rmean(x, 7))
        df["rolling_units_mean_14d"] = grp_u.transform(lambda x: _rmean(x, 14))
        df["rolling_units_mean_28d"] = grp_u.transform(lambda x: _rmean(x, 28))
        df["rolling_units_std_7d"] = grp_u.transform(lambda x: _rstd(x, 7))
        df["rolling_units_std_28d"] = grp_u.transform(lambda x: _rstd(x, 28))
        df["rolling_revenue_mean_7d"] = grp_r.transform(lambda x: _rmean(x, 7))
        df["rolling_revenue_mean_28d"] = grp_r.transform(lambda x: _rmean(x, 28))
        return df

    def _add_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        dt = pd.to_datetime(df["date"])
        df["day_of_week"] = dt.dt.dayofweek          # 0=Mon … 6=Sun
        df["week_of_year"] = dt.dt.isocalendar().week.astype(int)
        df["month"] = dt.dt.month
        df["quarter"] = dt.dt.quarter
        df["is_weekend"] = dt.dt.dayofweek >= 5
        return df

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        price = df["unit_price"]
        cost = df["unit_cost"]
        df["retail_price"] = price
        df["unit_cost"] = cost
        # gross_margin_pct = (price - cost) / price; None when price is null/zero
        margin = (price - cost) / price.replace(0, float("nan"))
        df["gross_margin_pct"] = margin.where(price.notna() & cost.notna(), other=None)

        # Price changes: compare retail_price at D vs D-7 / D-28
        # For static-price connectors this is always 0; real connectors with price changes get real values
        grp_p = df.groupby(["product_id", "store_id"])["unit_price"]
        df["price_change_pct_7d"] = grp_p.transform(
            lambda x: ((x - x.shift(7)) / x.shift(7).replace(0, float("nan")))
        )
        df["price_change_pct_28d"] = grp_p.transform(
            lambda x: ((x - x.shift(28)) / x.shift(28).replace(0, float("nan")))
        )
        return df

    def _add_lifecycle_features(self, df: pd.DataFrame) -> pd.DataFrame:
        def _days(row):
            if row["launch_date"] is None:
                return 0
            return (row["date"] - row["launch_date"]).days

        df["days_since_launch"] = df.apply(_days, axis=1)
        df["product_age_bucket"] = df["days_since_launch"].apply(
            lambda d: _age_bucket(d) if d >= 0 else "pre_launch"
        )
        return df

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _clear_and_write(self, df: pd.DataFrame, run_id: str, source_run_id: str | None) -> int:
        self.db.query(FeatureMatrix).delete(synchronize_session=False)
        self.db.flush()

        now = datetime.utcnow()
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "id": f"fm_{r['product_id']}_{r['store_id']}_{r['date']}",
                "date": r["date"], "product_id": r["product_id"], "store_id": r["store_id"],
                "target_units_sold": _flt(r.get("units_sold")),
                "lag_units_1d": _flt(r.get("lag_units_1d")),
                "lag_units_7d": _flt(r.get("lag_units_7d")),
                "lag_units_14d": _flt(r.get("lag_units_14d")),
                "lag_units_28d": _flt(r.get("lag_units_28d")),
                "rolling_units_mean_7d": _flt(r.get("rolling_units_mean_7d")),
                "rolling_units_mean_14d": _flt(r.get("rolling_units_mean_14d")),
                "rolling_units_mean_28d": _flt(r.get("rolling_units_mean_28d")),
                "rolling_units_std_7d": _flt(r.get("rolling_units_std_7d")),
                "rolling_units_std_28d": _flt(r.get("rolling_units_std_28d")),
                "rolling_revenue_mean_7d": _flt(r.get("rolling_revenue_mean_7d")),
                "rolling_revenue_mean_28d": _flt(r.get("rolling_revenue_mean_28d")),
                "day_of_week": _int(r.get("day_of_week")),
                "week_of_year": _int(r.get("week_of_year")),
                "month": _int(r.get("month")),
                "quarter": _int(r.get("quarter")),
                "is_weekend": bool(r.get("is_weekend", False)),
                "promo_active": bool(r.get("promotion_active", False)),
                "discount_pct": _flt(r.get("discount_pct")),
                "retail_price": _flt(r.get("retail_price")),
                "unit_cost": _flt(r.get("unit_cost")),
                "gross_margin_pct": _flt(r.get("gross_margin_pct")),
                "price_change_pct_7d": _flt(r.get("price_change_pct_7d")),
                "price_change_pct_28d": _flt(r.get("price_change_pct_28d")),
                "available_units": _flt(r.get("on_hand_units")),
                "stockout_flag": bool(r.get("stockout_flag", False)),
                "days_of_supply": _flt(r.get("days_of_supply")),
                "category": r.get("category"),
                "store_channel": r.get("channel"),
                "supplier_id": r.get("supplier_id"),
                "days_since_launch": _int(r.get("days_since_launch")),
                "product_age_bucket": r.get("product_age_bucket"),
                "source_aggregation_run_id": source_run_id,
                "feature_run_id": run_id,
                "created_at": now,
            })

        chunk = 2000
        for i in range(0, len(rows), chunk):
            self.db.bulk_insert_mappings(FeatureMatrix, rows[i:i + chunk])
        self.db.flush()
        return len(rows)

    # ------------------------------------------------------------------
    # Validation checks
    # ------------------------------------------------------------------

    def _run_checks(self, df: pd.DataFrame) -> list[dict]:
        checks = []

        # No duplicate (product, store, date) tuples
        n_dupes = df.duplicated(["product_id", "store_id", "date"]).sum()
        checks.append({
            "name": "no_duplicate_feature_rows",
            "status": "passed" if n_dupes == 0 else "failed",
            "detail": f"{n_dupes} duplicates",
        })

        # Rolling features are shifted (mean_7d at D should not equal units_sold at D)
        # Spot-check: rolling_units_mean_7d must differ from units_sold in most rows
        shifted_ok = True
        if "rolling_units_mean_7d" in df.columns:
            both_valid = df["rolling_units_mean_7d"].notna() & (df["units_sold"] > 0)
            if both_valid.sum() > 0:
                leaking = (df.loc[both_valid, "rolling_units_mean_7d"] == df.loc[both_valid, "units_sold"]).mean()
                shifted_ok = leaking < 0.05  # allow < 5% coincidental equality
        checks.append({"name": "rolling_features_shifted", "status": "passed" if shifted_ok else "failed"})

        # No forbidden forecast/risk columns in DataFrame
        bad_cols = set(df.columns) & _FORBIDDEN_FEATURE_COLS
        checks.append({
            "name": "no_forbidden_fields",
            "status": "passed" if not bad_cols else "failed",
            "detail": str(bad_cols) if bad_cols else "clean",
        })

        # Pre-launch rows excluded
        pre_launch = (df["days_since_launch"] < 0).sum()
        checks.append({
            "name": "pre_launch_excluded",
            "status": "passed" if pre_launch == 0 else "failed",
            "detail": f"{pre_launch} pre-launch rows remaining",
        })

        return checks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flt(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _int(v) -> int | None:
    f = _flt(v)
    return None if f is None else int(f)
