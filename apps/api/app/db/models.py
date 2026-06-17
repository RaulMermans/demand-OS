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


class FeatureMatrix(Base):
    """ML feature row per product/store/date. Computed by feature_service."""
    __tablename__ = "feature_matrix"

    id = Column(String, primary_key=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    feature_date = Column(Date, nullable=False, index=True)
    features = Column(JSON)            # dict of feature_name → value
    computed_at = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True)
    model_type = Column(String)        # lightgbm / xgboost / naive / etc.
    trained_at = Column(DateTime)
    training_cutoff_date = Column(Date)
    hyperparameters = Column(JSON, default=dict)
    artifact_path = Column(String)
    is_active = Column(Boolean, default=False)
    metrics = Column(JSON, default=dict)   # rmse, mae, smape, etc.


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id = Column(String, primary_key=True)
    model_version_id = Column(String, ForeignKey("model_versions.id"), nullable=True)
    run_at = Column(DateTime, nullable=False)
    forecast_horizon_days = Column(Integer, default=28)
    status = Column(String)
    records_produced = Column(Integer, default=0)


class Forecast(Base):
    """Point + interval forecasts per product/store/date. Computed by forecasting_service."""
    __tablename__ = "forecasts"

    id = Column(String, primary_key=True)
    forecast_run_id = Column(String, ForeignKey("forecast_runs.id"), nullable=True)
    product_id = Column(String, nullable=False, index=True)
    store_id = Column(String, nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    predicted_units = Column(Float)
    lower_bound = Column(Float)
    upper_bound = Column(Float)
    confidence_level = Column(Float, default=0.9)
    computed_at = Column(DateTime, default=datetime.utcnow)


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
    __tablename__ = "model_metrics"

    id = Column(String, primary_key=True)
    model_version_id = Column(String, ForeignKey("model_versions.id"), nullable=True)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float)
    product_id = Column(String)   # null = aggregate metric
    store_id = Column(String)
    horizon_days = Column(Integer)
    computed_at = Column(DateTime, default=datetime.utcnow)
