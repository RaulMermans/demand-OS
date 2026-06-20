/**
 * DemandOS typed API client.
 *
 * All functions use NEXT_PUBLIC_API_BASE_URL (defaults to http://localhost:8000).
 * No hardcoded production URLs. No fake fallback data.
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
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

// ---------------------------------------------------------------------------
// Internal fetch helper
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
  return apiFetch<StatusUpdateResponse>(
    `/api/recommendations/${encodeURIComponent(id)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}
