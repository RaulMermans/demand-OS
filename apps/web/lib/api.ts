/**
 * DemandOS typed API client.
 *
 * All functions use NEXT_PUBLIC_API_BASE_URL as the API base.
 * When the env var is blank/unset, same-origin relative paths are used (/api/...).
 * No hardcoded production URLs. No fake fallback data.
 *
 * Write/control endpoints optionally accept an API key sent as
 * X-DemandOS-API-Key header. The key is read from sessionStorage via
 * lib/apiKey.ts — never from environment variables.
 */

import type {
  HealthResponse,
  OverviewResponse,
  DataHealthResponse,
  ForecastRunsResponse,
  LatestForecastResponse,
  ProductForecastResponse,
  ModelVersionsResponse,
  ModelMetricsResponse,
  ModelCompareResponse,
  RiskRunsResponse,
  LatestRiskResponse,
  RisksListResponse,
  ProductRisksResponse,
  RecommendationRunsResponse,
  LatestRecommendationsResponse,
  RecommendationsListResponse,
  ProductRecommendationsResponse,
  StatusUpdateResponse,
  StatusUpdatePayload,
  DashboardOverviewResponse,
  DashboardForecastSummaryResponse,
  DashboardRiskSummaryResponse,
  DashboardRecommendationSummaryResponse,
  DashboardModelSummaryResponse,
  DashboardPipelineStatusResponse,
  DashboardProductResponse,
  PipelineControlResponse,
  FullPipelineResponse,
  PipelineRunsResponse,
  LatestPipelineRunResponse,
  DataScienceSummaryResponse,
  ForecastDiagnosticsResponse,
  ModelComparisonResponse,
  FeatureSignalsResponse,
  BusinessImpactResponse,
  CockpitResponse,
  InventoryTrendResponse,
  RiskDriversResponse,
  ReorderQueueResponse,
  ExecutiveSummaryResponse,
} from "./types";
import { getStoredApiKey } from "./apiKey";

// When NEXT_PUBLIC_API_BASE_URL is blank or absent, use same-origin relative paths
// ("/api/..."). This is the correct mode for a single Vercel project where frontend
// and backend are served from the same domain.
// When a URL is provided (e.g. local dev http://localhost:8000), use it as prefix.
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL
  ? process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "")
  : "";

// ---------------------------------------------------------------------------
// Internal fetch helpers
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `API error ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? body?.error?.message ?? detail;
    } catch {
      // ignore json parse error
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

/** POST to a write/control endpoint, attaching the stored API key if present. */
async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const key = getStoredApiKey();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (key) headers["X-DemandOS-API-Key"] = key;
  return apiFetch<T>(path, {
    method: "POST",
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

/** PATCH to a write endpoint, attaching the stored API key if present. */
async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  const key = getStoredApiKey();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (key) headers["X-DemandOS-API-Key"] = key;
  return apiFetch<T>(path, {
    method: "PATCH",
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

// ---------------------------------------------------------------------------
// Overview / Data Health
// ---------------------------------------------------------------------------

export function getOverview(): Promise<OverviewResponse> {
  return apiFetch<OverviewResponse>("/api/overview");
}

export function getDataHealth(): Promise<DataHealthResponse> {
  return apiFetch<DataHealthResponse>("/api/data-health");
}

// ---------------------------------------------------------------------------
// Dashboard summaries
// ---------------------------------------------------------------------------

export function getDashboardOverview(): Promise<DashboardOverviewResponse> {
  return apiFetch<DashboardOverviewResponse>("/api/dashboard/overview");
}

export function getDashboardForecastSummary(): Promise<DashboardForecastSummaryResponse> {
  return apiFetch<DashboardForecastSummaryResponse>("/api/dashboard/forecast-summary");
}

export function getDashboardRiskSummary(): Promise<DashboardRiskSummaryResponse> {
  return apiFetch<DashboardRiskSummaryResponse>("/api/dashboard/risk-summary");
}

export function getDashboardRecommendationSummary(): Promise<DashboardRecommendationSummaryResponse> {
  return apiFetch<DashboardRecommendationSummaryResponse>("/api/dashboard/recommendation-summary");
}

export function getDashboardModelSummary(): Promise<DashboardModelSummaryResponse> {
  return apiFetch<DashboardModelSummaryResponse>("/api/dashboard/model-summary");
}

// ---------------------------------------------------------------------------
// Forecasts
// ---------------------------------------------------------------------------

export function getForecastRuns(limit = 20): Promise<ForecastRunsResponse> {
  return apiFetch<ForecastRunsResponse>(`/api/forecasts/runs?limit=${limit}`);
}

export function getLatestForecast(limit = 50): Promise<LatestForecastResponse> {
  return apiFetch<LatestForecastResponse>(`/api/forecasts/latest?limit=${limit}`);
}

export function getProductForecast(
  productId: string,
  params?: { store_id?: string; run_id?: string; limit?: number }
): Promise<ProductForecastResponse> {
  const qs = new URLSearchParams();
  if (params?.store_id) qs.set("store_id", params.store_id);
  if (params?.run_id) qs.set("run_id", params.run_id);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<ProductForecastResponse>(
    `/api/forecasts/product/${encodeURIComponent(productId)}${query}`
  );
}

// ---------------------------------------------------------------------------
// Models
// ---------------------------------------------------------------------------

export function getModelVersions(limit = 20): Promise<ModelVersionsResponse> {
  return apiFetch<ModelVersionsResponse>(`/api/models/versions?limit=${limit}`);
}

export function getModelMetrics(params?: {
  run_id?: string;
  model_type?: string;
  level?: string;
  limit?: number;
}): Promise<ModelMetricsResponse> {
  const qs = new URLSearchParams();
  if (params?.run_id) qs.set("run_id", params.run_id);
  if (params?.model_type) qs.set("model_type", params.model_type);
  if (params?.level) qs.set("level", params.level);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<ModelMetricsResponse>(`/api/model-metrics${query}`);
}

export function getModelComparison(): Promise<ModelCompareResponse> {
  return apiFetch<ModelCompareResponse>("/api/models/compare");
}

// ---------------------------------------------------------------------------
// Risks
// ---------------------------------------------------------------------------

export function getRiskRuns(limit = 20): Promise<RiskRunsResponse> {
  return apiFetch<RiskRunsResponse>(`/api/risks/runs?limit=${limit}`);
}

export function getLatestRisks(limit = 50): Promise<LatestRiskResponse> {
  return apiFetch<LatestRiskResponse>(`/api/risks/latest?limit=${limit}`);
}

export function getRisks(params?: {
  risk_tier?: string;
  store_id?: string;
  category?: string;
  limit?: number;
  offset?: number;
}): Promise<RisksListResponse> {
  const qs = new URLSearchParams();
  if (params?.risk_tier) qs.set("risk_tier", params.risk_tier);
  if (params?.store_id) qs.set("store_id", params.store_id);
  if (params?.category) qs.set("category", params.category);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<RisksListResponse>(`/api/risks${query}`);
}

export function getProductRisks(productId: string): Promise<ProductRisksResponse> {
  return apiFetch<ProductRisksResponse>(
    `/api/risks/product/${encodeURIComponent(productId)}`
  );
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

export function getRecommendationRuns(limit = 20): Promise<RecommendationRunsResponse> {
  return apiFetch<RecommendationRunsResponse>(
    `/api/recommendations/runs?limit=${limit}`
  );
}

export function getLatestRecommendations(): Promise<LatestRecommendationsResponse> {
  return apiFetch<LatestRecommendationsResponse>("/api/recommendations/latest");
}

export function getRecommendations(params?: {
  status?: string;
  urgency?: string;
  risk_tier?: string;
  store_id?: string;
  category?: string;
  supplier_id?: string;
  limit?: number;
  offset?: number;
}): Promise<RecommendationsListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.urgency) qs.set("urgency", params.urgency);
  if (params?.risk_tier) qs.set("risk_tier", params.risk_tier);
  if (params?.store_id) qs.set("store_id", params.store_id);
  if (params?.category) qs.set("category", params.category);
  if (params?.supplier_id) qs.set("supplier_id", params.supplier_id);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch<RecommendationsListResponse>(`/api/recommendations${query}`);
}

export function getProductRecommendations(
  productId: string
): Promise<ProductRecommendationsResponse> {
  return apiFetch<ProductRecommendationsResponse>(
    `/api/recommendations/product/${encodeURIComponent(productId)}`
  );
}

export function updateRecommendationStatus(
  id: string,
  payload: StatusUpdatePayload
): Promise<StatusUpdateResponse> {
  return apiPatch<StatusUpdateResponse>(
    `/api/recommendations/${encodeURIComponent(id)}/status`,
    payload
  );
}

// ---------------------------------------------------------------------------
// Pipeline controls (write — sends API key header when configured)
// ---------------------------------------------------------------------------

export function runDemoReset(params?: {
  seed?: number;
  product_count?: number;
  store_count?: number;
  history_days?: number;
}): Promise<PipelineControlResponse> {
  return apiPost<PipelineControlResponse>("/api/demo/reset", params ?? {});
}

export function runAggregation(): Promise<PipelineControlResponse> {
  return apiPost<PipelineControlResponse>("/api/aggregation/run", {});
}

export function runFeatureBuild(): Promise<PipelineControlResponse> {
  return apiPost<PipelineControlResponse>("/api/features/build", {});
}

export function runBaselineForecast(params?: {
  model_type?: string;
  horizon_days?: number;
  backtest_days?: number;
}): Promise<PipelineControlResponse> {
  return apiPost<PipelineControlResponse>("/api/forecasts/baseline/run", params ?? {
    model_type: "seasonal_naive",
    horizon_days: 28,
    backtest_days: 56,
  });
}

export function runModelTrain(params?: {
  algorithm?: string;
  horizon_days?: number;
  backtest_days?: number;
}): Promise<PipelineControlResponse> {
  return apiPost<PipelineControlResponse>("/api/models/train", params ?? {
    algorithm: "hist_gradient_boosting",
    horizon_days: 28,
    backtest_days: 56,
  });
}

export function runPlanningForecast(params?: {
  model_type?: string;
  horizon_days?: number;
}): Promise<PipelineControlResponse> {
  return apiPost<PipelineControlResponse>("/api/forecasts/planning/run", params ?? {
    model_type: "seasonal_naive",
    horizon_days: 28,
  });
}

export function runStockoutRisk(params?: {
  horizon_days?: number;
  mode?: string;
}): Promise<PipelineControlResponse> {
  return apiPost<PipelineControlResponse>("/api/risks/run", params ?? {
    horizon_days: 28,
    mode: "forward_planning",
  });
}

export function runRecommendations(params?: {
  include_low_risk?: boolean;
}): Promise<PipelineControlResponse> {
  return apiPost<PipelineControlResponse>("/api/recommendations/run", params ?? {});
}

// ---------------------------------------------------------------------------
// Dashboard — Sprint 9 endpoints
// ---------------------------------------------------------------------------

export function getDashboardPipelineStatus(): Promise<DashboardPipelineStatusResponse> {
  return apiFetch<DashboardPipelineStatusResponse>("/api/dashboard/pipeline-status");
}

export function getDashboardProduct(productId: string): Promise<DashboardProductResponse> {
  return apiFetch<DashboardProductResponse>(
    `/api/dashboard/product/${encodeURIComponent(productId)}`
  );
}

// ---------------------------------------------------------------------------
// Demo Pipeline — Sprint 10
// ---------------------------------------------------------------------------

export function runFullDemoPipeline(params?: {
  seed?: number;
  product_count?: number;
  store_count?: number;
  history_days?: number;
}): Promise<FullPipelineResponse> {
  return apiPost<FullPipelineResponse>("/api/demo/run-full-pipeline", params ?? {});
}

export function getDemoPipelineRuns(limit = 20): Promise<PipelineRunsResponse> {
  return apiFetch<PipelineRunsResponse>(`/api/demo/pipeline-runs?limit=${limit}`);
}

export function getLatestDemoPipelineRun(): Promise<LatestPipelineRunResponse> {
  return apiFetch<LatestPipelineRunResponse>("/api/demo/pipeline-runs/latest");
}

// ---------------------------------------------------------------------------
// Data Science Summary Layer — Sprint 15
// ---------------------------------------------------------------------------

export function getDataScienceSummary(): Promise<DataScienceSummaryResponse> {
  return apiFetch<DataScienceSummaryResponse>("/api/data-science/summary");
}

export function getForecastDiagnostics(): Promise<ForecastDiagnosticsResponse> {
  return apiFetch<ForecastDiagnosticsResponse>("/api/data-science/forecast-diagnostics");
}

export function getDSModelComparison(): Promise<ModelComparisonResponse> {
  return apiFetch<ModelComparisonResponse>("/api/data-science/model-comparison");
}

export function getFeatureSignals(): Promise<FeatureSignalsResponse> {
  return apiFetch<FeatureSignalsResponse>("/api/data-science/feature-signals");
}

export function getBusinessImpact(): Promise<BusinessImpactResponse> {
  return apiFetch<BusinessImpactResponse>("/api/data-science/business-impact");
}

// ---------------------------------------------------------------------------
// Analytics Cockpit — Sprint 16
// ---------------------------------------------------------------------------

export function getAnalyticsCockpit(): Promise<CockpitResponse> {
  return apiFetch<CockpitResponse>("/api/analytics/cockpit");
}

export function getInventoryTrend(params?: {
  product_id?: string;
  store_id?: string;
  days?: number;
}): Promise<InventoryTrendResponse> {
  const qs = new URLSearchParams();
  if (params?.product_id) qs.set("product_id", params.product_id);
  if (params?.store_id) qs.set("store_id", params.store_id);
  if (params?.days) qs.set("days", String(params.days));
  const query = qs.toString();
  return apiFetch<InventoryTrendResponse>(`/api/analytics/inventory-trend${query ? `?${query}` : ""}`);
}

export function getRiskDrivers(limit = 10): Promise<RiskDriversResponse> {
  return apiFetch<RiskDriversResponse>(`/api/analytics/risk-drivers?limit=${limit}`);
}

export function getReorderQueue(): Promise<ReorderQueueResponse> {
  return apiFetch<ReorderQueueResponse>("/api/analytics/reorder-queue");
}

export function getExecutiveSummary(): Promise<ExecutiveSummaryResponse> {
  return apiFetch<ExecutiveSummaryResponse>("/api/analytics/executive-summary");
}
