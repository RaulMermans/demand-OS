/**
 * TypeScript types for DemandOS API responses.
 * Mirrors the Pydantic schemas in apps/api/app/schemas/api.py
 */

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}

// ---------------------------------------------------------------------------
// Overview / Data Health
// ---------------------------------------------------------------------------

export interface OverviewSummary {
  products: number;
  stores: number;
  orders: number;
  feature_rows_count: number;
  feature_readiness: string | null;
  latest_feature_run_status: string | null;
  latest_forecast_run_status: string | null;
  latest_baseline_model: string | null;
  latest_baseline_wape: number | null;
  forecast_rows_count: number;
  model_metrics_count: number;
  last_ingestion_run: string | null;
  latest_ml_model_status: string | null;
  latest_ml_model_algorithm: string | null;
  latest_ml_wape: number | null;
  best_baseline_wape: number | null;
  model_artifact_exists: boolean;
  critical_stockout_count: number;
  high_stockout_count: number;
  medium_stockout_count: number;
  low_stockout_count: number;
  estimated_lost_sales_value: number | null;
  latest_risk_run_status: string | null;
  latest_risk_horizon_days: number | null;
  open_recommendation_count: number;
  critical_recommendation_count: number;
  high_recommendation_count: number;
  total_recommended_units: number;
  estimated_order_cost: number;
  estimated_lost_sales_avoided: number;
  latest_recommendation_run_status: string | null;
}

export interface OverviewResponse {
  status: string;
  data_mode: string;
  pipeline_ready: boolean;
  message: string;
  summary: OverviewSummary;
}

export interface DataHealthCheck {
  name: string;
  status: "passed" | "failed" | "warning";
  detail?: string;
}

export interface DataHealthResponse {
  status: string;
  data_mode: string;
  products_count: number;
  stores_count: number;
  orders_count: number;
  inventory_snapshots_count: number;
  promotions_count: number;
  suppliers_count: number;
  purchase_orders_count: number;
  latest_ingestion_run: Record<string, unknown> | null;
  latest_aggregation_run: Record<string, unknown> | null;
  canonical_counts: {
    sales_daily: number;
    inventory_daily: number;
    product_store_daily: number;
  };
  feature_counts: { feature_matrix: number };
  latest_feature_run: Record<string, unknown> | null;
  forecast_counts: {
    forecast_runs: number;
    forecasts: number;
    model_metrics: number;
  };
  latest_forecast_run: Record<string, unknown> | null;
  model_counts: {
    model_versions: number;
    ml_forecast_runs: number;
  };
  latest_model_version: Record<string, unknown> | null;
  risk_counts: {
    stockout_risk_runs: number;
    stockout_risks: number;
  };
  latest_stockout_risk_run: Record<string, unknown> | null;
  recommendation_counts: {
    recommendation_runs: number;
    reorder_recommendations: number;
  };
  latest_recommendation_run: Record<string, unknown> | null;
  checks: DataHealthCheck[];
  message: string;
}

// ---------------------------------------------------------------------------
// Forecasts
// ---------------------------------------------------------------------------

export interface ForecastRunSummary {
  run_id: string;
  model_name: string;
  model_type: string;
  horizon_days: number;
  backtest_mode: boolean;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  rows_created: number;
  test_start_date: string | null;
  test_end_date: string | null;
}

export interface ForecastRunsResponse {
  runs: ForecastRunSummary[];
  total: number;
}

export interface ForecastRow {
  id: string;
  forecast_run_id: string | null;
  forecast_date: string | null;
  product_id: string;
  store_id: string;
  horizon_day: number;
  model_type: string | null;
  p50_units: number | null;
  p10_units: number | null;
  p90_units: number | null;
  actual_units: number | null;
  absolute_error: number | null;
  absolute_percentage_error: number | null;
}

export interface LatestForecastResponse {
  status: string;
  message?: string;
  run: Partial<ForecastRunSummary> | null;
  sample: ForecastRow[];
  sample_size?: number;
}

export interface ProductForecastResponse {
  status: string;
  product_id: string;
  run_id: string | null;
  rows: ForecastRow[];
  total: number;
}

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

export interface ModelVersion {
  model_version_id: string;
  model_name: string | null;
  algorithm: string | null;
  model_type: string | null;
  status: string | null;
  trained_at: string | null;
  training_start_date: string | null;
  training_end_date: string | null;
  test_start_date: string | null;
  test_end_date: string | null;
  artifact_path: string | null;
  metrics_summary: Record<string, unknown> | null;
  config: Record<string, unknown> | null;
  feature_columns: string[] | null;
  created_at: string | null;
}

export interface ModelVersionsResponse {
  versions: ModelVersion[];
  total: number;
}

export interface ModelMetric {
  id: string;
  run_id: string | null;
  model_type: string;
  horizon_days: number | null;
  level: string | null;
  level_value: string | null;
  mae: number | null;
  rmse: number | null;
  wape: number | null;
  smape: number | null;
  bias: number | null;
  rows_evaluated: number;
  created_at: string | null;
}

export interface ModelMetricsResponse {
  status: string;
  message?: string;
  metrics: ModelMetric[];
  total?: number;
}

export interface ModelCompareResponse {
  status: string;
  ml_run_id?: string;
  ml_model_type?: string;
  ml_wape?: number | null;
  best_baseline_run_id?: string;
  best_baseline_model_type?: string;
  best_baseline_wape?: number | null;
  wape_delta?: number | null;
  ml_won_against_baseline?: boolean | null;
  message?: string;
}

// ---------------------------------------------------------------------------
// Stockout Risks
// ---------------------------------------------------------------------------

export interface RiskRunSummary {
  run_id: string;
  mode: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  as_of_date: string | null;
  risk_horizon_days: number | null;
  rows_created: number;
  risk_counts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    unknown: number;
  };
  source_forecast_run_id: string | null;
  error_message: string | null;
}

export interface RiskRunsResponse {
  runs: RiskRunSummary[];
  total: number;
}

export interface StockoutRisk {
  id: string;
  risk_run_id: string;
  as_of_date: string | null;
  product_id: string;
  store_id: string;
  category: string | null;
  supplier_id: string | null;
  forecast_run_id: string | null;
  model_type: string | null;
  forecast_horizon_days: number | null;
  current_on_hand_units: number | null;
  current_available_units: number | null;
  inbound_units_within_horizon: number | null;
  supplier_lead_time_days: number | null;
  supplier_reliability_score: number | null;
  forecast_demand_p50: number | null;
  forecast_demand_p90: number | null;
  average_daily_forecast: number | null;
  projected_end_inventory_p50: number | null;
  projected_end_inventory_p90: number | null;
  days_of_supply: number | null;
  days_until_stockout: number | null;
  expected_stockout_date: string | null;
  safety_stock_units: number | null;
  inventory_coverage_ratio: number | null;
  lost_sales_units_estimate: number | null;
  lost_sales_value_estimate: number | null;
  risk_score: number | null;
  risk_tier: string | null;
  risk_reason: string | null;
  created_at: string | null;
}

export interface LatestRiskResponse {
  status: string;
  message?: string;
  run: RiskRunSummary | null;
  sample: StockoutRisk[];
  sample_size?: number;
}

export interface RisksListResponse {
  status: string;
  message?: string;
  run_id: string | null;
  mode?: string;
  as_of_date?: string | null;
  rows: StockoutRisk[];
  total: number;
  risk_counts?: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    unknown: number;
  };
}

export interface ProductRisksResponse {
  status: string;
  product_id: string;
  run_id: string | null;
  rows: StockoutRisk[];
  total: number;
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

export interface RecommendationRunSummary {
  run_id: string;
  source_risk_run_id: string | null;
  mode: string | null;
  status: string;
  as_of_date: string | null;
  started_at: string | null;
  completed_at: string | null;
  rows_created: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_recommended_units: number | null;
  total_estimated_value: number | null;
}

export interface RecommendationRunsResponse {
  runs: RecommendationRunSummary[];
  total: number;
}

export interface ReorderRecommendation {
  id: string;
  recommendation_run_id: string;
  source_risk_run_id: string | null;
  source_risk_id: string | null;
  as_of_date: string | null;
  product_id: string;
  store_id: string;
  category: string | null;
  supplier_id: string | null;
  risk_tier: string | null;
  risk_score: number | null;
  expected_stockout_date: string | null;
  days_until_stockout: number | null;
  current_available_units: number | null;
  inbound_units_within_horizon: number | null;
  inventory_position: number | null;
  supplier_lead_time_days: number | null;
  supplier_reliability_score: number | null;
  forecast_demand_p50: number | null;
  lead_time_demand_units: number | null;
  safety_stock_units: number | null;
  reorder_point_units: number | null;
  recommended_units: number | null;
  recommended_units_rounded: number | null;
  min_order_quantity: number | null;
  order_multiple: number | null;
  estimated_order_cost: number | null;
  estimated_lost_sales_value: number | null;
  estimated_lost_sales_avoided: number | null;
  urgency: string | null;
  recommendation_reason: string | null;
  confidence_level: string | null;
  status: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  review_note: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface LatestRecommendationsResponse {
  status: string;
  message?: string;
  run: RecommendationRunSummary | null;
  recommendations: ReorderRecommendation[];
}

export interface RecommendationsListResponse {
  recommendations: ReorderRecommendation[];
  total: number;
  returned: number;
  run_id: string | null;
}

export interface ProductRecommendationsResponse {
  product_id: string;
  run_id: string | null;
  recommendations: ReorderRecommendation[];
}

export interface StatusUpdateResponse {
  status: string;
  recommendation_id: string;
  new_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  note: string;
}

export interface StatusUpdatePayload {
  status: string;
  reviewed_by?: string;
  review_note?: string;
}

// ---------------------------------------------------------------------------
// Dashboard summaries
// ---------------------------------------------------------------------------

export interface DashboardOverviewResponse {
  status: string;
  raw_counts: Record<string, number>;
  pipeline_readiness: Record<string, unknown>;
  risk_summary: Record<string, unknown>;
  recommendation_summary: Record<string, unknown>;
  forecast_summary: Record<string, unknown>;
}

export interface DashboardRiskSummaryResponse {
  status: string;
  has_risk_run: boolean;
  latest_run: Record<string, unknown> | null;
  tier_counts: Record<string, number>;
  estimated_lost_sales_value: number | null;
  message: string | null;
}

export interface DashboardRecommendationSummaryResponse {
  status: string;
  has_recommendation_run: boolean;
  latest_run: Record<string, unknown> | null;
  urgency_counts: Record<string, number>;
  open_count: number;
  total_estimated_order_cost: number | null;
  message: string | null;
}

export interface DashboardForecastSummaryResponse {
  status: string;
  has_forecast: boolean;
  latest_run: Record<string, unknown> | null;
  metrics: Record<string, unknown> | null;
  message: string | null;
}

export interface DashboardModelSummaryResponse {
  status: string;
  has_ml_model: boolean;
  latest_model_version: Record<string, unknown> | null;
  baseline_comparison: Record<string, unknown> | null;
  message: string | null;
}
