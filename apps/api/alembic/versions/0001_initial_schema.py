"""Initial schema — Sprint 0-7 tables.

Revision ID: 0001
Revises:
Create Date: 2026-06-19

Covers all tables created through Sprint 7:
  Raw layer, Ops layer, Clean layer, Canonical daily, Feature matrix,
  Model registry, Forecasts, Stockout risks, Reorder recommendations.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Raw layer
    # -----------------------------------------------------------------------

    op.create_table(
        "raw_suppliers",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("external_id", sa.String, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("country", sa.String),
        sa.Column("lead_time_days_min", sa.Integer),
        sa.Column("lead_time_days_max", sa.Integer),
        sa.Column("reliability_score", sa.Float),
        sa.Column("contact_email", sa.String),
        sa.Column("source_connector", sa.String, nullable=False),
        sa.Column("ingested_at", sa.DateTime),
        sa.Column("raw_payload", sa.JSON),
    )
    op.create_index("ix_raw_suppliers_external_id", "raw_suppliers", ["external_id"])

    op.create_table(
        "raw_stores",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("external_id", sa.String, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("region", sa.String),
        sa.Column("country", sa.String),
        sa.Column("timezone", sa.String),
        sa.Column("channel", sa.String),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("source_connector", sa.String, nullable=False),
        sa.Column("ingested_at", sa.DateTime),
        sa.Column("raw_payload", sa.JSON),
    )
    op.create_index("ix_raw_stores_external_id", "raw_stores", ["external_id"])

    op.create_table(
        "raw_products",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("external_id", sa.String, nullable=False),
        sa.Column("sku", sa.String, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("category", sa.String),
        sa.Column("brand", sa.String),
        sa.Column("supplier_id", sa.String, sa.ForeignKey("raw_suppliers.id")),
        sa.Column("unit_cost", sa.Float),
        sa.Column("unit_price", sa.Float),
        sa.Column("lead_time_days", sa.Integer),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("attributes", sa.JSON),
        sa.Column("source_connector", sa.String, nullable=False),
        sa.Column("ingested_at", sa.DateTime),
        sa.Column("raw_payload", sa.JSON),
    )
    op.create_index("ix_raw_products_external_id", "raw_products", ["external_id"])
    op.create_index("ix_raw_products_sku", "raw_products", ["sku"])

    op.create_table(
        "raw_promotions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("external_id", sa.String, nullable=False),
        sa.Column("name", sa.String),
        sa.Column("promotion_type", sa.String),
        sa.Column("discount_pct", sa.Float, default=0.0),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("applicable_skus", sa.JSON),
        sa.Column("applicable_stores", sa.JSON),
        sa.Column("source_connector", sa.String, nullable=False),
        sa.Column("ingested_at", sa.DateTime),
        sa.Column("raw_payload", sa.JSON),
    )
    op.create_index("ix_raw_promotions_external_id", "raw_promotions", ["external_id"])

    op.create_table(
        "raw_orders",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("external_order_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, sa.ForeignKey("raw_stores.id")),
        sa.Column("product_id", sa.String, sa.ForeignKey("raw_products.id")),
        sa.Column("ordered_at", sa.DateTime, nullable=False),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column("discount_amount", sa.Float, default=0.0),
        sa.Column("currency", sa.String, default="USD"),
        sa.Column("status", sa.String),
        sa.Column("promotion_id", sa.String, sa.ForeignKey("raw_promotions.id")),
        sa.Column("source_connector", sa.String, nullable=False),
        sa.Column("ingested_at", sa.DateTime),
        sa.Column("raw_payload", sa.JSON),
    )
    op.create_index("ix_raw_orders_external_order_id", "raw_orders", ["external_order_id"])
    op.create_index("ix_raw_orders_ordered_at", "raw_orders", ["ordered_at"])
    op.create_index("ix_raw_orders_order_date", "raw_orders", ["order_date"])

    op.create_table(
        "raw_inventory_snapshots",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("store_id", sa.String, sa.ForeignKey("raw_stores.id")),
        sa.Column("product_id", sa.String, sa.ForeignKey("raw_products.id")),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("quantity_on_hand", sa.Float, nullable=False),
        sa.Column("quantity_on_order", sa.Float, default=0.0),
        sa.Column("quantity_reserved", sa.Float, default=0.0),
        sa.Column("warehouse_location", sa.String),
        sa.Column("source_connector", sa.String, nullable=False),
        sa.Column("ingested_at", sa.DateTime),
        sa.Column("raw_payload", sa.JSON),
    )
    op.create_index("ix_raw_inventory_snapshots_snapshot_date", "raw_inventory_snapshots", ["snapshot_date"])

    op.create_table(
        "raw_purchase_orders",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("external_po_id", sa.String, nullable=False),
        sa.Column("supplier_id", sa.String, sa.ForeignKey("raw_suppliers.id")),
        sa.Column("product_id", sa.String, sa.ForeignKey("raw_products.id")),
        sa.Column("store_id", sa.String, sa.ForeignKey("raw_stores.id")),
        sa.Column("ordered_at", sa.DateTime, nullable=False),
        sa.Column("expected_delivery_date", sa.Date),
        sa.Column("quantity_ordered", sa.Float, nullable=False),
        sa.Column("unit_cost", sa.Float),
        sa.Column("status", sa.String),
        sa.Column("source_connector", sa.String, nullable=False),
        sa.Column("ingested_at", sa.DateTime),
        sa.Column("raw_payload", sa.JSON),
    )
    op.create_index("ix_raw_purchase_orders_external_po_id", "raw_purchase_orders", ["external_po_id"])

    # -----------------------------------------------------------------------
    # Ops layer
    # -----------------------------------------------------------------------

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("connector", sa.String, nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("finished_at", sa.DateTime),
        sa.Column("status", sa.String),
        sa.Column("records_ingested", sa.Integer, default=0),
        sa.Column("error_message", sa.Text),
        sa.Column("run_metadata", sa.JSON),
    )

    op.create_table(
        "pipeline_events",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("ingestion_run_id", sa.String, sa.ForeignKey("ingestion_runs.id")),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("severity", sa.String, default="info"),
        sa.Column("message", sa.Text),
        sa.Column("entity_type", sa.String),
        sa.Column("entity_id", sa.String),
        sa.Column("occurred_at", sa.DateTime),
        sa.Column("event_metadata", sa.JSON),
    )

    op.create_table(
        "aggregation_runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("finished_at", sa.DateTime),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("status", sa.String),
        sa.Column("error_message", sa.Text),
        sa.Column("records_produced", sa.JSON),
    )

    op.create_table(
        "feature_runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("source_aggregation_run_id", sa.String),
        sa.Column("status", sa.String),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("rows_created", sa.Integer, default=0),
        sa.Column("date_min", sa.Date),
        sa.Column("date_max", sa.Date),
        sa.Column("max_lag_days", sa.Integer, default=28),
        sa.Column("checks_json", sa.JSON),
        sa.Column("error_message", sa.Text),
    )

    # -----------------------------------------------------------------------
    # Cleaned layer
    # -----------------------------------------------------------------------

    op.create_table(
        "orders_clean",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("raw_order_id", sa.String, sa.ForeignKey("raw_orders.id"), nullable=False),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column("discount_amount", sa.Float, default=0.0),
        sa.Column("currency", sa.String, default="EUR"),
        sa.Column("promotion_id", sa.String),
        sa.Column("aggregation_run_id", sa.String),
        sa.Column("cleaned_at", sa.DateTime),
    )
    op.create_index("ix_orders_clean_raw_order_id", "orders_clean", ["raw_order_id"])
    op.create_index("ix_orders_clean_product_id", "orders_clean", ["product_id"])
    op.create_index("ix_orders_clean_store_id", "orders_clean", ["store_id"])
    op.create_index("ix_orders_clean_order_date", "orders_clean", ["order_date"])

    op.create_table(
        "inventory_clean",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("raw_snapshot_id", sa.String, sa.ForeignKey("raw_inventory_snapshots.id"), nullable=False),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("on_hand", sa.Float, nullable=False),
        sa.Column("on_order", sa.Float, default=0.0),
        sa.Column("aggregation_run_id", sa.String),
        sa.Column("cleaned_at", sa.DateTime),
    )

    op.create_table(
        "promotions_clean",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("raw_promotion_id", sa.String, sa.ForeignKey("raw_promotions.id"), nullable=False),
        sa.Column("name", sa.String),
        sa.Column("promotion_type", sa.String),
        sa.Column("discount_pct", sa.Float, default=0.0),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("applicable_skus", sa.JSON),
        sa.Column("applicable_stores", sa.JSON),
        sa.Column("aggregation_run_id", sa.String),
        sa.Column("cleaned_at", sa.DateTime),
    )

    op.create_table(
        "products_clean",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("raw_product_id", sa.String, sa.ForeignKey("raw_products.id"), nullable=False),
        sa.Column("sku", sa.String, nullable=False),
        sa.Column("name", sa.String),
        sa.Column("category", sa.String),
        sa.Column("brand", sa.String),
        sa.Column("supplier_id", sa.String),
        sa.Column("unit_cost", sa.Float),
        sa.Column("unit_price", sa.Float),
        sa.Column("lead_time_days", sa.Integer),
        sa.Column("aggregation_run_id", sa.String),
        sa.Column("cleaned_at", sa.DateTime),
    )

    op.create_table(
        "stores_clean",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("raw_store_id", sa.String, sa.ForeignKey("raw_stores.id"), nullable=False),
        sa.Column("name", sa.String),
        sa.Column("region", sa.String),
        sa.Column("country", sa.String),
        sa.Column("channel", sa.String),
        sa.Column("aggregation_run_id", sa.String),
        sa.Column("cleaned_at", sa.DateTime),
    )

    op.create_table(
        "suppliers_clean",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("raw_supplier_id", sa.String, sa.ForeignKey("raw_suppliers.id"), nullable=False),
        sa.Column("name", sa.String),
        sa.Column("country", sa.String),
        sa.Column("lead_time_days_min", sa.Integer),
        sa.Column("lead_time_days_max", sa.Integer),
        sa.Column("reliability_score", sa.Float),
        sa.Column("aggregation_run_id", sa.String),
        sa.Column("cleaned_at", sa.DateTime),
    )

    op.create_table(
        "purchase_orders_clean",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("raw_po_id", sa.String, sa.ForeignKey("raw_purchase_orders.id"), nullable=False),
        sa.Column("supplier_id", sa.String),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("ordered_date", sa.Date, nullable=False),
        sa.Column("expected_delivery_date", sa.Date),
        sa.Column("quantity_ordered", sa.Float, nullable=False),
        sa.Column("unit_cost", sa.Float),
        sa.Column("status", sa.String),
        sa.Column("aggregation_run_id", sa.String),
        sa.Column("cleaned_at", sa.DateTime),
    )

    # -----------------------------------------------------------------------
    # Canonical daily layer
    # -----------------------------------------------------------------------

    op.create_table(
        "sales_daily",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("units_sold", sa.Float, default=0.0),
        sa.Column("net_revenue", sa.Float, default=0.0),
        sa.Column("discount_amount", sa.Float, default=0.0),
        sa.Column("avg_unit_price", sa.Float),
        sa.Column("order_count", sa.Integer, default=0),
        sa.Column("promotion_active", sa.Boolean, default=False),
        sa.Column("source_run_id", sa.String),
        sa.Column("computed_at", sa.DateTime),
    )
    op.create_index("ix_sales_daily_product_id", "sales_daily", ["product_id"])
    op.create_index("ix_sales_daily_store_id", "sales_daily", ["store_id"])
    op.create_index("ix_sales_daily_date", "sales_daily", ["date"])

    op.create_table(
        "inventory_daily",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("on_hand_units", sa.Float, default=0.0),
        sa.Column("on_order_units", sa.Float, default=0.0),
        sa.Column("inbound_units", sa.Float, default=0.0),
        sa.Column("stockout_flag", sa.Boolean, default=False),
        sa.Column("days_of_supply", sa.Float),
        sa.Column("source_run_id", sa.String),
        sa.Column("computed_at", sa.DateTime),
    )
    op.create_index("ix_inventory_daily_product_id", "inventory_daily", ["product_id"])
    op.create_index("ix_inventory_daily_store_id", "inventory_daily", ["store_id"])
    op.create_index("ix_inventory_daily_date", "inventory_daily", ["date"])

    op.create_table(
        "promotion_daily",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("is_active", sa.Boolean, default=False),
        sa.Column("promotion_id", sa.String),
        sa.Column("discount_pct", sa.Float, default=0.0),
        sa.Column("promotion_name", sa.String),
        sa.Column("source_run_id", sa.String),
        sa.Column("computed_at", sa.DateTime),
    )

    op.create_table(
        "product_store_daily",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("sku", sa.String),
        sa.Column("product_name", sa.String),
        sa.Column("category", sa.String),
        sa.Column("channel", sa.String),
        sa.Column("units_sold", sa.Float, default=0.0),
        sa.Column("net_revenue", sa.Float, default=0.0),
        sa.Column("discount_amount", sa.Float, default=0.0),
        sa.Column("on_hand_units", sa.Float),
        sa.Column("on_order_units", sa.Float),
        sa.Column("inbound_units", sa.Float, default=0.0),
        sa.Column("stockout_flag", sa.Boolean, default=False),
        sa.Column("days_of_supply", sa.Float),
        sa.Column("promotion_active", sa.Boolean, default=False),
        sa.Column("discount_pct", sa.Float, default=0.0),
        sa.Column("source_run_id", sa.String),
        sa.Column("computed_at", sa.DateTime),
    )
    op.create_index("ix_product_store_daily_date", "product_store_daily", ["date"])
    op.create_index("ix_product_store_daily_product_id", "product_store_daily", ["product_id"])
    op.create_index("ix_product_store_daily_store_id", "product_store_daily", ["store_id"])

    # -----------------------------------------------------------------------
    # Feature matrix
    # -----------------------------------------------------------------------

    op.create_table(
        "feature_matrix",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("target_units_sold", sa.Float),
        sa.Column("lag_units_1d", sa.Float),
        sa.Column("lag_units_7d", sa.Float),
        sa.Column("lag_units_14d", sa.Float),
        sa.Column("lag_units_28d", sa.Float),
        sa.Column("rolling_units_mean_7d", sa.Float),
        sa.Column("rolling_units_mean_14d", sa.Float),
        sa.Column("rolling_units_mean_28d", sa.Float),
        sa.Column("rolling_units_std_7d", sa.Float),
        sa.Column("rolling_units_std_28d", sa.Float),
        sa.Column("rolling_revenue_mean_7d", sa.Float),
        sa.Column("rolling_revenue_mean_28d", sa.Float),
        sa.Column("day_of_week", sa.Integer),
        sa.Column("week_of_year", sa.Integer),
        sa.Column("month", sa.Integer),
        sa.Column("quarter", sa.Integer),
        sa.Column("is_weekend", sa.Boolean),
        sa.Column("promo_active", sa.Boolean),
        sa.Column("discount_pct", sa.Float),
        sa.Column("retail_price", sa.Float),
        sa.Column("unit_cost", sa.Float),
        sa.Column("gross_margin_pct", sa.Float),
        sa.Column("price_change_pct_7d", sa.Float),
        sa.Column("price_change_pct_28d", sa.Float),
        sa.Column("available_units", sa.Float),
        sa.Column("stockout_flag", sa.Boolean),
        sa.Column("days_of_supply", sa.Float),
        sa.Column("category", sa.String),
        sa.Column("store_channel", sa.String),
        sa.Column("supplier_id", sa.String),
        sa.Column("days_since_launch", sa.Integer),
        sa.Column("product_age_bucket", sa.String),
        sa.Column("source_aggregation_run_id", sa.String),
        sa.Column("feature_run_id", sa.String),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_feature_matrix_date", "feature_matrix", ["date"])
    op.create_index("ix_feature_matrix_product_id", "feature_matrix", ["product_id"])
    op.create_index("ix_feature_matrix_store_id", "feature_matrix", ["store_id"])
    op.create_index("ix_feature_matrix_feature_run_id", "feature_matrix", ["feature_run_id"])

    # -----------------------------------------------------------------------
    # Model registry
    # -----------------------------------------------------------------------

    op.create_table(
        "model_versions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("model_type", sa.String),
        sa.Column("trained_at", sa.DateTime),
        sa.Column("training_cutoff_date", sa.Date),
        sa.Column("hyperparameters", sa.JSON),
        sa.Column("artifact_path", sa.String),
        sa.Column("is_active", sa.Boolean, default=False),
        sa.Column("metrics", sa.JSON),
        sa.Column("model_name", sa.String),
        sa.Column("algorithm", sa.String),
        sa.Column("status", sa.String),
        sa.Column("training_start_date", sa.Date),
        sa.Column("training_end_date", sa.Date),
        sa.Column("test_start_date", sa.Date),
        sa.Column("test_end_date", sa.Date),
        sa.Column("feature_run_id", sa.String),
        sa.Column("feature_columns_json", sa.JSON),
        sa.Column("target_column", sa.String, default="target_units_sold"),
        sa.Column("metrics_summary_json", sa.JSON),
        sa.Column("config_json", sa.JSON),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )

    # -----------------------------------------------------------------------
    # Forecast runs + forecasts
    # -----------------------------------------------------------------------

    op.create_table(
        "forecast_runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("model_name", sa.String, nullable=False),
        sa.Column("model_type", sa.String, nullable=False),
        sa.Column("horizon_days", sa.Integer, default=28),
        sa.Column("backtest_mode", sa.Boolean, default=True),
        sa.Column("mode", sa.String, default="backtest"),
        sa.Column("train_start_date", sa.Date),
        sa.Column("train_end_date", sa.Date),
        sa.Column("test_start_date", sa.Date),
        sa.Column("test_end_date", sa.Date),
        sa.Column("status", sa.String),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("rows_created", sa.Integer, default=0),
        sa.Column("error_message", sa.Text),
        sa.Column("config_json", sa.JSON),
        sa.Column("model_version_id", sa.String, sa.ForeignKey("model_versions.id")),
    )

    op.create_table(
        "forecasts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("forecast_run_id", sa.String, sa.ForeignKey("forecast_runs.id")),
        sa.Column("forecast_date", sa.Date, nullable=False),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("horizon_day", sa.Integer, default=1),
        sa.Column("model_name", sa.String),
        sa.Column("model_type", sa.String),
        sa.Column("p50_units", sa.Float),
        sa.Column("p10_units", sa.Float),
        sa.Column("p90_units", sa.Float),
        sa.Column("actual_units", sa.Float),
        sa.Column("absolute_error", sa.Float),
        sa.Column("squared_error", sa.Float),
        sa.Column("absolute_percentage_error", sa.Float),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_forecasts_forecast_run_id", "forecasts", ["forecast_run_id"])
    op.create_index("ix_forecasts_forecast_date", "forecasts", ["forecast_date"])
    op.create_index("ix_forecasts_product_id", "forecasts", ["product_id"])
    op.create_index("ix_forecasts_store_id", "forecasts", ["store_id"])

    op.create_table(
        "model_metrics",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("run_id", sa.String, sa.ForeignKey("forecast_runs.id")),
        sa.Column("model_name", sa.String, nullable=False),
        sa.Column("model_type", sa.String, nullable=False),
        sa.Column("horizon_days", sa.Integer),
        sa.Column("level", sa.String),
        sa.Column("level_value", sa.String),
        sa.Column("mae", sa.Float),
        sa.Column("rmse", sa.Float),
        sa.Column("wape", sa.Float),
        sa.Column("smape", sa.Float),
        sa.Column("bias", sa.Float),
        sa.Column("rows_evaluated", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime),
        sa.Column("model_version_id", sa.String),
    )
    op.create_index("ix_model_metrics_run_id", "model_metrics", ["run_id"])

    # -----------------------------------------------------------------------
    # Stockout risk
    # -----------------------------------------------------------------------

    op.create_table(
        "stockout_risk_runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("source_forecast_run_id", sa.String, sa.ForeignKey("forecast_runs.id")),
        sa.Column("source_model_version_id", sa.String, sa.ForeignKey("model_versions.id")),
        sa.Column("mode", sa.String),
        sa.Column("status", sa.String),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("risk_horizon_days", sa.Integer),
        sa.Column("as_of_date", sa.Date),
        sa.Column("rows_created", sa.Integer, default=0),
        sa.Column("critical_count", sa.Integer, default=0),
        sa.Column("high_count", sa.Integer, default=0),
        sa.Column("medium_count", sa.Integer, default=0),
        sa.Column("low_count", sa.Integer, default=0),
        sa.Column("unknown_count", sa.Integer, default=0),
        sa.Column("checks_json", sa.JSON),
        sa.Column("config_json", sa.JSON),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "stockout_risks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("risk_run_id", sa.String, sa.ForeignKey("stockout_risk_runs.id"), nullable=False),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("category", sa.String),
        sa.Column("subcategory", sa.String),
        sa.Column("supplier_id", sa.String),
        sa.Column("forecast_run_id", sa.String, sa.ForeignKey("forecast_runs.id")),
        sa.Column("model_type", sa.String),
        sa.Column("model_name", sa.String),
        sa.Column("forecast_horizon_days", sa.Integer),
        sa.Column("current_on_hand_units", sa.Float),
        sa.Column("current_reserved_units", sa.Float, default=0.0),
        sa.Column("current_available_units", sa.Float),
        sa.Column("inbound_units_within_horizon", sa.Float, default=0.0),
        sa.Column("supplier_lead_time_days", sa.Integer),
        sa.Column("supplier_reliability_score", sa.Float),
        sa.Column("forecast_demand_p50", sa.Float),
        sa.Column("forecast_demand_p90", sa.Float),
        sa.Column("average_daily_forecast", sa.Float),
        sa.Column("projected_end_inventory_p50", sa.Float),
        sa.Column("projected_end_inventory_p90", sa.Float),
        sa.Column("days_of_supply", sa.Float),
        sa.Column("days_until_stockout", sa.Float),
        sa.Column("expected_stockout_date", sa.Date),
        sa.Column("safety_stock_units", sa.Float),
        sa.Column("inventory_coverage_ratio", sa.Float),
        sa.Column("lost_sales_units_estimate", sa.Float),
        sa.Column("lost_sales_value_estimate", sa.Float),
        sa.Column("risk_score", sa.Float),
        sa.Column("risk_tier", sa.String),
        sa.Column("risk_reason", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_stockout_risks_risk_run_id", "stockout_risks", ["risk_run_id"])
    op.create_index("ix_stockout_risks_as_of_date", "stockout_risks", ["as_of_date"])
    op.create_index("ix_stockout_risks_product_id", "stockout_risks", ["product_id"])
    op.create_index("ix_stockout_risks_store_id", "stockout_risks", ["store_id"])

    # -----------------------------------------------------------------------
    # Reorder recommendations
    # -----------------------------------------------------------------------

    op.create_table(
        "recommendation_runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("source_risk_run_id", sa.String, sa.ForeignKey("stockout_risk_runs.id")),
        sa.Column("source_forecast_run_id", sa.String),
        sa.Column("mode", sa.String, default="recommendation_only"),
        sa.Column("status", sa.String),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("as_of_date", sa.Date),
        sa.Column("horizon_days", sa.Integer),
        sa.Column("rows_created", sa.Integer, default=0),
        sa.Column("critical_count", sa.Integer, default=0),
        sa.Column("high_count", sa.Integer, default=0),
        sa.Column("medium_count", sa.Integer, default=0),
        sa.Column("low_count", sa.Integer, default=0),
        sa.Column("total_recommended_units", sa.Float, default=0.0),
        sa.Column("total_estimated_value", sa.Float, default=0.0),
        sa.Column("checks_json", sa.JSON),
        sa.Column("config_json", sa.JSON),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "reorder_recommendations",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("recommendation_run_id", sa.String, sa.ForeignKey("recommendation_runs.id"), nullable=False),
        sa.Column("source_risk_run_id", sa.String, sa.ForeignKey("stockout_risk_runs.id")),
        sa.Column("source_risk_id", sa.String, sa.ForeignKey("stockout_risks.id")),
        sa.Column("as_of_date", sa.Date, nullable=False),
        sa.Column("product_id", sa.String, nullable=False),
        sa.Column("store_id", sa.String, nullable=False),
        sa.Column("category", sa.String),
        sa.Column("subcategory", sa.String),
        sa.Column("supplier_id", sa.String),
        sa.Column("risk_tier", sa.String),
        sa.Column("risk_score", sa.Float),
        sa.Column("expected_stockout_date", sa.Date),
        sa.Column("days_until_stockout", sa.Float),
        sa.Column("current_available_units", sa.Float),
        sa.Column("inbound_units_within_horizon", sa.Float, default=0.0),
        sa.Column("inventory_position", sa.Float),
        sa.Column("supplier_lead_time_days", sa.Integer),
        sa.Column("supplier_reliability_score", sa.Float),
        sa.Column("forecast_demand_p50", sa.Float),
        sa.Column("forecast_demand_p90", sa.Float),
        sa.Column("lead_time_demand_units", sa.Float),
        sa.Column("safety_stock_units", sa.Float),
        sa.Column("reorder_point_units", sa.Float),
        sa.Column("recommended_units", sa.Float),
        sa.Column("recommended_units_rounded", sa.Float),
        sa.Column("min_order_quantity", sa.Float, default=1.0),
        sa.Column("order_multiple", sa.Float, default=1.0),
        sa.Column("estimated_order_cost", sa.Float),
        sa.Column("estimated_lost_sales_value", sa.Float),
        sa.Column("estimated_lost_sales_avoided", sa.Float),
        sa.Column("urgency", sa.String),
        sa.Column("recommendation_reason", sa.Text),
        sa.Column("confidence_level", sa.String),
        sa.Column("status", sa.String, default="open"),
        sa.Column("reviewed_at", sa.DateTime),
        sa.Column("reviewed_by", sa.String),
        sa.Column("review_note", sa.Text),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_reorder_recommendations_recommendation_run_id", "reorder_recommendations", ["recommendation_run_id"])
    op.create_index("ix_reorder_recommendations_as_of_date", "reorder_recommendations", ["as_of_date"])
    op.create_index("ix_reorder_recommendations_product_id", "reorder_recommendations", ["product_id"])
    op.create_index("ix_reorder_recommendations_store_id", "reorder_recommendations", ["store_id"])


def downgrade() -> None:
    op.drop_table("reorder_recommendations")
    op.drop_table("recommendation_runs")
    op.drop_table("stockout_risks")
    op.drop_table("stockout_risk_runs")
    op.drop_table("model_metrics")
    op.drop_table("forecasts")
    op.drop_table("forecast_runs")
    op.drop_table("model_versions")
    op.drop_table("feature_matrix")
    op.drop_table("product_store_daily")
    op.drop_table("promotion_daily")
    op.drop_table("inventory_daily")
    op.drop_table("sales_daily")
    op.drop_table("purchase_orders_clean")
    op.drop_table("suppliers_clean")
    op.drop_table("stores_clean")
    op.drop_table("products_clean")
    op.drop_table("promotions_clean")
    op.drop_table("inventory_clean")
    op.drop_table("orders_clean")
    op.drop_table("feature_runs")
    op.drop_table("aggregation_runs")
    op.drop_table("pipeline_events")
    op.drop_table("ingestion_runs")
    op.drop_table("raw_purchase_orders")
    op.drop_table("raw_inventory_snapshots")
    op.drop_table("raw_orders")
    op.drop_table("raw_promotions")
    op.drop_table("raw_products")
    op.drop_table("raw_stores")
    op.drop_table("raw_suppliers")
