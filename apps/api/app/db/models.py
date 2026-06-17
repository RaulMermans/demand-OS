"""
SQLAlchemy ORM models for DemandOS.

Layer layout
------------
Raw layer       — ingested operational records, never modified after write
Ops layer       — pipeline bookkeeping
Derived layer   — computed by the pipeline (Sprint 2+); tables are defined here
                  but not yet populated.
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Date, DateTime,
    Text, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


# ---------------------------------------------------------------------------
# Raw layer
# ---------------------------------------------------------------------------

class RawProduct(Base):
    __tablename__ = "raw_products"

    id = Column(String, primary_key=True)
    external_id = Column(String, nullable=False, index=True)
    sku = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String)
    brand = Column(String)
    supplier_id = Column(String, ForeignKey("raw_suppliers.id"), nullable=True)
    unit_cost = Column(Float)
    unit_price = Column(Float)
    lead_time_days = Column(Integer)
    is_active = Column(Boolean, default=True)
    attributes = Column(JSON, default=dict)
    source_connector = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    raw_payload = Column(JSON)


class RawStore(Base):
    __tablename__ = "raw_stores"

    id = Column(String, primary_key=True)
    external_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    region = Column(String)
    country = Column(String)
    timezone = Column(String)
    channel = Column(String)          # e.g. online, retail, wholesale
    is_active = Column(Boolean, default=True)
    source_connector = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    raw_payload = Column(JSON)


class RawOrder(Base):
    __tablename__ = "raw_orders"

    id = Column(String, primary_key=True)
    external_order_id = Column(String, nullable=False, index=True)
    store_id = Column(String, ForeignKey("raw_stores.id"), nullable=True)
    product_id = Column(String, ForeignKey("raw_products.id"), nullable=True)
    ordered_at = Column(DateTime, nullable=False, index=True)
    order_date = Column(Date, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    status = Column(String)           # pending / fulfilled / cancelled / returned
    promotion_id = Column(String, ForeignKey("raw_promotions.id"), nullable=True)
    source_connector = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    raw_payload = Column(JSON)


class RawInventorySnapshot(Base):
    __tablename__ = "raw_inventory_snapshots"

    id = Column(String, primary_key=True)
    store_id = Column(String, ForeignKey("raw_stores.id"), nullable=True)
    product_id = Column(String, ForeignKey("raw_products.id"), nullable=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    quantity_on_hand = Column(Float, nullable=False)
    quantity_on_order = Column(Float, default=0.0)
    quantity_reserved = Column(Float, default=0.0)
    warehouse_location = Column(String)
    source_connector = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    raw_payload = Column(JSON)


class RawPromotion(Base):
    __tablename__ = "raw_promotions"

    id = Column(String, primary_key=True)
    external_id = Column(String, nullable=False, index=True)
    name = Column(String)
    promotion_type = Column(String)   # discount / bogo / bundle / flash_sale
    discount_pct = Column(Float, default=0.0)
    start_date = Column(Date)
    end_date = Column(Date)
    applicable_skus = Column(JSON, default=list)
    applicable_stores = Column(JSON, default=list)
    source_connector = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    raw_payload = Column(JSON)


class RawSupplier(Base):
    __tablename__ = "raw_suppliers"

    id = Column(String, primary_key=True)
    external_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    country = Column(String)
    lead_time_days_min = Column(Integer)
    lead_time_days_max = Column(Integer)
    reliability_score = Column(Float)   # 0–1; raw from ERP, not derived
    contact_email = Column(String)
    source_connector = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    raw_payload = Column(JSON)


class RawPurchaseOrder(Base):
    __tablename__ = "raw_purchase_orders"

    id = Column(String, primary_key=True)
    external_po_id = Column(String, nullable=False, index=True)
    supplier_id = Column(String, ForeignKey("raw_suppliers.id"), nullable=True)
    product_id = Column(String, ForeignKey("raw_products.id"), nullable=True)
    store_id = Column(String, ForeignKey("raw_stores.id"), nullable=True)
    ordered_at = Column(DateTime, nullable=False)
    expected_delivery_date = Column(Date)
    quantity_ordered = Column(Float, nullable=False)
    unit_cost = Column(Float)
    status = Column(String)           # draft / submitted / confirmed / received / cancelled
    source_connector = Column(String, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    raw_payload = Column(JSON)


# ---------------------------------------------------------------------------
# Ops layer
# ---------------------------------------------------------------------------

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(String, primary_key=True)
    connector = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    status = Column(String)           # running / success / failed
    records_ingested = Column(Integer, default=0)
    error_message = Column(Text)
    run_metadata = Column(JSON, default=dict)     # renamed: 'metadata' is reserved in SA


class PipelineEvent(Base):
    __tablename__ = "pipeline_events"

    id = Column(String, primary_key=True)
    ingestion_run_id = Column(String, ForeignKey("ingestion_runs.id"), nullable=True)
    event_type = Column(String, nullable=False)   # validation_error / aggregation_done / etc.
    severity = Column(String, default="info")      # info / warning / error
    message = Column(Text)
    entity_type = Column(String)
    entity_id = Column(String)
    occurred_at = Column(DateTime, default=datetime.utcnow)
    event_metadata = Column(JSON, default=dict)   # renamed: 'metadata' is reserved in SA


# ---------------------------------------------------------------------------
# Derived / model / decision layer  (Sprint 2+)
# Tables exist in schema; pipeline does not populate them yet.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Cleaned layer  (Sprint 2)  — filtered / deduplicated copies of raw tables
# ---------------------------------------------------------------------------

class OrdersClean(Base):
    """Fulfilled and pending orders only (cancelled/returned excluded)."""
    __tablename__ = "orders_clean"

    id = Column(String, primary_key=True)
    raw_order_id = Column(String, ForeignKey("raw_orders.id"), nullable=False, index=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    order_date = Column(Date, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    currency = Column(String, default="EUR")
    promotion_id = Column(String, nullable=True)
    aggregation_run_id = Column(String, nullable=True)
    cleaned_at = Column(DateTime, default=datetime.utcnow)


class InventoryClean(Base):
    """Latest snapshot per (product, store, date); duplicates removed."""
    __tablename__ = "inventory_clean"

    id = Column(String, primary_key=True)
    raw_snapshot_id = Column(String, ForeignKey("raw_inventory_snapshots.id"), nullable=False, index=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    on_hand = Column(Float, nullable=False)
    on_order = Column(Float, default=0.0)
    aggregation_run_id = Column(String, nullable=True)
    cleaned_at = Column(DateTime, default=datetime.utcnow)


class PromotionsClean(Base):
    """Promotions with valid date ranges."""
    __tablename__ = "promotions_clean"

    id = Column(String, primary_key=True)
    raw_promotion_id = Column(String, ForeignKey("raw_promotions.id"), nullable=False, index=True)
    name = Column(String)
    promotion_type = Column(String)
    discount_pct = Column(Float, default=0.0)
    start_date = Column(Date)
    end_date = Column(Date)
    applicable_skus = Column(JSON, default=list)
    applicable_stores = Column(JSON, default=list)
    aggregation_run_id = Column(String, nullable=True)
    cleaned_at = Column(DateTime, default=datetime.utcnow)


class ProductsClean(Base):
    """Active products with normalized attributes."""
    __tablename__ = "products_clean"

    id = Column(String, primary_key=True)
    raw_product_id = Column(String, ForeignKey("raw_products.id"), nullable=False, index=True)
    sku = Column(String, nullable=False)
    name = Column(String)
    category = Column(String)
    brand = Column(String)
    supplier_id = Column(String, nullable=True)
    unit_cost = Column(Float)
    unit_price = Column(Float)
    lead_time_days = Column(Integer)
    aggregation_run_id = Column(String, nullable=True)
    cleaned_at = Column(DateTime, default=datetime.utcnow)


class StoresClean(Base):
    """Active stores with normalized channel."""
    __tablename__ = "stores_clean"

    id = Column(String, primary_key=True)
    raw_store_id = Column(String, ForeignKey("raw_stores.id"), nullable=False, index=True)
    name = Column(String)
    region = Column(String)
    country = Column(String)
    channel = Column(String)
    aggregation_run_id = Column(String, nullable=True)
    cleaned_at = Column(DateTime, default=datetime.utcnow)


class SuppliersClean(Base):
    """Suppliers with valid reliability scores."""
    __tablename__ = "suppliers_clean"

    id = Column(String, primary_key=True)
    raw_supplier_id = Column(String, ForeignKey("raw_suppliers.id"), nullable=False, index=True)
    name = Column(String)
    country = Column(String)
    lead_time_days_min = Column(Integer)
    lead_time_days_max = Column(Integer)
    reliability_score = Column(Float)
    aggregation_run_id = Column(String, nullable=True)
    cleaned_at = Column(DateTime, default=datetime.utcnow)


class PurchaseOrdersClean(Base):
    """Purchase orders with valid delivery dates."""
    __tablename__ = "purchase_orders_clean"

    id = Column(String, primary_key=True)
    raw_po_id = Column(String, ForeignKey("raw_purchase_orders.id"), nullable=False, index=True)
    supplier_id = Column(String, nullable=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    ordered_date = Column(Date, nullable=False, index=True)
    expected_delivery_date = Column(Date, nullable=True)
    quantity_ordered = Column(Float, nullable=False)
    unit_cost = Column(Float)
    status = Column(String)
    aggregation_run_id = Column(String, nullable=True)
    cleaned_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Canonical daily layer  (Sprint 2)
# ---------------------------------------------------------------------------

class SalesDaily(Base):
    """Aggregated daily fulfilled sales per product per store. Computed by AggregationService."""
    __tablename__ = "sales_daily"

    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    units_sold = Column(Float, default=0.0)
    net_revenue = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    avg_unit_price = Column(Float)
    order_count = Column(Integer, default=0)
    promotion_active = Column(Boolean, default=False)
    source_run_id = Column(String, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)


class InventoryDaily(Base):
    """Daily inventory position per product per store. Computed by AggregationService."""
    __tablename__ = "inventory_daily"

    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    on_hand_units = Column(Float, default=0.0)
    on_order_units = Column(Float, default=0.0)
    inbound_units = Column(Float, default=0.0)
    stockout_flag = Column(Boolean, default=False)
    days_of_supply = Column(Float, nullable=True)
    source_run_id = Column(String, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)


class PromotionDaily(Base):
    """Active promotion flag per product per store per day. Computed by AggregationService."""
    __tablename__ = "promotion_daily"

    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    is_active = Column(Boolean, default=False)
    promotion_id = Column(String, nullable=True)
    discount_pct = Column(Float, default=0.0)
    promotion_name = Column(String, nullable=True)
    source_run_id = Column(String, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)


class ProductStoreDaily(Base):
    """Canonical denormalized daily fact: one row per (product, store, date). Computed by AggregationService."""
    __tablename__ = "product_store_daily"

    id = Column(String, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    sku = Column(String)
    product_name = Column(String)
    category = Column(String)
    channel = Column(String)
    units_sold = Column(Float, default=0.0)
    net_revenue = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    on_hand_units = Column(Float, nullable=True)
    on_order_units = Column(Float, nullable=True)
    inbound_units = Column(Float, default=0.0)
    stockout_flag = Column(Boolean, default=False)
    days_of_supply = Column(Float, nullable=True)
    promotion_active = Column(Boolean, default=False)
    discount_pct = Column(Float, default=0.0)
    source_run_id = Column(String, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)


class AggregationRun(Base):
    """Tracks each execution of AggregationService.run_full_aggregation()."""
    __tablename__ = "aggregation_runs"

    id = Column(String, primary_key=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String)            # running / success / failed
    error_message = Column(Text)
    records_produced = Column(JSON, default=dict)


class FeatureRun(Base):
    """Tracks each execution of FeatureService.build_feature_matrix()."""
    __tablename__ = "feature_runs"

    id = Column(String, primary_key=True)
    source_aggregation_run_id = Column(String, nullable=True)
    status = Column(String)            # running / completed / failed
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    rows_created = Column(Integer, default=0)
    date_min = Column(Date)
    date_max = Column(Date)
    max_lag_days = Column(Integer, default=28)
    checks_json = Column(JSON, default=list)
    error_message = Column(Text)


class FeatureMatrix(Base):
    """
    ML-ready feature row per (product, store, date). Computed by FeatureService.

    All predictive features are leakage-safe:
    - Lag/rolling features use dates strictly before D.
    - Calendar features use date D.
    - Promotion/inventory features use state known on D.
    - target_units_sold is the historical label for supervised training.

    Pre-launch rows are excluded (product_age_bucket != 'pre_launch').
    """
    __tablename__ = "feature_matrix"

    id = Column(String, primary_key=True)
    date = Column(Date, nullable=False, index=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)

    # Supervised learning target (historical; never future)
    target_units_sold = Column(Float)

    # Lag features — units_sold at D-N (strictly before D)
    lag_units_1d = Column(Float)
    lag_units_7d = Column(Float)
    lag_units_14d = Column(Float)
    lag_units_28d = Column(Float)

    # Rolling mean features — mean over [D-window … D-1] (shift=1)
    rolling_units_mean_7d = Column(Float)
    rolling_units_mean_14d = Column(Float)
    rolling_units_mean_28d = Column(Float)

    # Rolling std features — std over [D-window … D-1] (shift=1)
    rolling_units_std_7d = Column(Float)
    rolling_units_std_28d = Column(Float)

    # Rolling revenue features
    rolling_revenue_mean_7d = Column(Float)
    rolling_revenue_mean_28d = Column(Float)

    # Calendar features (derived from date D)
    day_of_week = Column(Integer)      # 0=Mon … 6=Sun
    week_of_year = Column(Integer)
    month = Column(Integer)
    quarter = Column(Integer)
    is_weekend = Column(Boolean)

    # Promotion features (from promotion_daily for date D)
    promo_active = Column(Boolean)
    discount_pct = Column(Float)

    # Price / margin features (from product metadata)
    retail_price = Column(Float)
    unit_cost = Column(Float)
    gross_margin_pct = Column(Float)
    price_change_pct_7d = Column(Float)
    price_change_pct_28d = Column(Float)

    # Inventory features (from inventory_daily for date D)
    available_units = Column(Float)
    stockout_flag = Column(Boolean)
    days_of_supply = Column(Float)

    # Categorical / structural features
    category = Column(String)
    store_channel = Column(String)
    supplier_id = Column(String)

    # Lifecycle features
    days_since_launch = Column(Integer)
    product_age_bucket = Column(String)  # new_0_30 / ramp_31_90 / mature_91_365 / established_365_plus

    # Tracking
    source_aggregation_run_id = Column(String)
    feature_run_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True)
    model_type = Column(String)        # lightgbm / xgboost / naive / etc.
    trained_at = Column(DateTime)
    training_cutoff_date = Column(Date)
    hyperparameters = Column(JSON, default=dict)
    artifact_path = Column(String)
    is_active = Column(Boolean, default=False)
    metrics = Column(JSON, default=dict)


class ForecastRun(Base):
    """Tracks each baseline or ML forecast run. Computed by ForecastingService."""
    __tablename__ = "forecast_runs"

    id = Column(String, primary_key=True)
    model_name = Column(String, nullable=False)   # e.g. "seasonal_naive"
    model_type = Column(String, nullable=False)   # "seasonal_naive" / "moving_average_7d" / "moving_average_28d"
    horizon_days = Column(Integer, default=28)
    backtest_mode = Column(Boolean, default=True)
    train_start_date = Column(Date)
    train_end_date = Column(Date)
    test_start_date = Column(Date)
    test_end_date = Column(Date)
    status = Column(String)           # running / completed / failed
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    rows_created = Column(Integer, default=0)
    error_message = Column(Text)
    config_json = Column(JSON, default=dict)
    model_version_id = Column(String, ForeignKey("model_versions.id"), nullable=True)


class Forecast(Base):
    """
    One row per (run_id × forecast_date × product_id × store_id).
    Computed by ForecastingService.

    p10/p90 are simple uncertainty bands: p50 ± 1 std of recent demand.
    These are heuristics, not true probabilistic intervals.
    absolute_percentage_error stores the SMAPE per-row component:
      2 * |forecast - actual| / (|actual| + |forecast|), zero when denominator=0.
    """
    __tablename__ = "forecasts"

    id = Column(String, primary_key=True)
    forecast_run_id = Column(String, ForeignKey("forecast_runs.id"), nullable=True, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    horizon_day = Column(Integer, default=1)    # ordinal step in the forecast horizon
    model_name = Column(String)
    model_type = Column(String)
    p50_units = Column(Float)                   # point forecast (required)
    p10_units = Column(Float)                   # lower band (heuristic)
    p90_units = Column(Float)                   # upper band (heuristic)
    actual_units = Column(Float)                # actuals joined for backtest evaluation
    absolute_error = Column(Float)
    squared_error = Column(Float)
    absolute_percentage_error = Column(Float)   # SMAPE per-row component
    created_at = Column(DateTime, default=datetime.utcnow)


class StockoutRisk(Base):
    """Stockout probability and days-until-stockout. Computed by stockout_service."""
    __tablename__ = "stockout_risks"

    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    risk_date = Column(Date, nullable=False, index=True)
    stockout_probability = Column(Float)   # 0–1
    days_until_stockout = Column(Float)
    current_on_hand = Column(Float)
    safety_stock_level = Column(Float)
    risk_tier = Column(String)             # critical / high / medium / low
    computed_at = Column(DateTime, default=datetime.utcnow)


class ReorderRecommendation(Base):
    """Reorder recommendations. Computed by recommendation_service."""
    __tablename__ = "reorder_recommendations"

    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    supplier_id = Column(String, nullable=True)
    recommendation_date = Column(Date, nullable=False, index=True)
    recommended_qty = Column(Float)
    reorder_point = Column(Float)
    economic_order_qty = Column(Float)
    expected_delivery_date = Column(Date)
    estimated_cost = Column(Float)
    rationale = Column(Text)
    status = Column(String, default="pending")   # pending / approved / dismissed
    computed_at = Column(DateTime, default=datetime.utcnow)


class ModelMetric(Base):
    """
    Aggregated forecast metrics per (run, level).

    level values: "overall", "category", "store", "product"
    level_value:  "all" for overall, category name, store_id, or product_id otherwise.

    WAPE/Bias are None when sum(actual)=0 (undefined denominator).
    SMAPE is the mean of per-row symmetric APE; zero-denominator rows contribute 0.
    """
    __tablename__ = "model_metrics"

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("forecast_runs.id"), nullable=True, index=True)
    model_name = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    horizon_days = Column(Integer)
    level = Column(String)          # "overall" / "category" / "store" / "product"
    level_value = Column(String)    # value at that level; "all" for overall
    mae = Column(Float)
    rmse = Column(Float)
    wape = Column(Float)            # None when sum(actual)=0
    smape = Column(Float)
    bias = Column(Float)            # None when sum(actual)=0
    rows_evaluated = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    model_version_id = Column(String, nullable=True)   # reserved for future ML models
