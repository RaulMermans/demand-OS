"use client";

import { useEffect, useState } from "react";
import {
  getDashboardForecastSummary,
  getForecastRuns,
  getModelMetrics,
  getProductForecast,
} from "@/lib/api";
import type {
  DashboardForecastSummaryResponse,
  ForecastRunsResponse,
  ModelMetricsResponse,
  ProductForecastResponse,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import DataTable from "@/components/DataTable";
import ChartCard from "@/components/ChartCard";
import LineChartPanel from "@/components/LineChartPanel";
import BarChartPanel from "@/components/BarChartPanel";
import KpiCard from "@/components/KpiCard";
import PageHeader from "@/components/PageHeader";

export default function ForecastsPage() {
  const [summary, setSummary] = useState<DashboardForecastSummaryResponse | null>(null);
  const [runs, setRuns] = useState<ForecastRunsResponse | null>(null);
  const [metrics, setMetrics] = useState<ModelMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Product drilldown
  const [productId, setProductId] = useState("");
  const [productInput, setProductInput] = useState("");
  const [productForecast, setProductForecast] = useState<ProductForecastResponse | null>(null);
  const [productLoading, setProductLoading] = useState(false);
  const [productError, setProductError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getDashboardForecastSummary(),
      getForecastRuns(10),
      getModelMetrics({ level: "overall", limit: 20 }),
    ])
      .then(([s, r, m]) => { setSummary(s); setRuns(r); setMetrics(m); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const loadProductForecast = (id: string) => {
    if (!id.trim()) return;
    setProductId(id.trim());
    setProductLoading(true);
    setProductError(null);
    setProductForecast(null);
    getProductForecast(id.trim(), { limit: 100 })
      .then(setProductForecast)
      .catch((e) => setProductError(e.message))
      .finally(() => setProductLoading(false));
  };

  const fmtPct = (n: number | null | undefined) =>
    n == null ? "—" : `${(n * 100).toFixed(2)}%`;

  // Build forecast line chart data from product forecast rows
  const forecastChartData = productForecast?.rows.map((r) => ({
    date: r.forecast_date?.slice(0, 10) ?? "",
    actual: r.actual_units ?? null,
    p50: r.p50_units ?? null,
    p10: r.p10_units ?? null,
    p90: r.p90_units ?? null,
  })) ?? [];

  // Metrics bar chart: compare models by WAPE
  const metricsBarData = metrics?.metrics
    .filter((m) => m.wape != null)
    .map((m) => ({
      name: m.model_type.replace(/_/g, " "),
      value: Math.round((m.wape ?? 0) * 1000) / 10,
    })) ?? [];

  return (
    <div>
      <PageHeader
        title="Demand forecasts"
        subtitle="Inspect backtest accuracy, compare model performance, and explore product-level prediction intervals."
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && summary && !summary.has_forecast && (
        <EmptyState
          title="No forecast run has been generated yet."
          message="Go to Pipeline Controls and run the Baseline Forecast step, or run POST /api/forecasts/baseline/run."
        />
      )}

      {summary?.has_forecast && (
        <>
          {/* Overall metric KPIs */}
          {summary.metrics && (
            <section style={{ marginBottom: "24px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "12px" }}>
                {[
                  { label: "MAE", value: summary.metrics.mae != null ? (summary.metrics.mae as number).toFixed(2) : "—" },
                  { label: "RMSE", value: summary.metrics.rmse != null ? (summary.metrics.rmse as number).toFixed(2) : "—" },
                  { label: "WAPE", value: fmtPct(summary.metrics.wape as number) },
                  { label: "SMAPE", value: fmtPct(summary.metrics.smape as number) },
                  { label: "Bias", value: summary.metrics.bias != null ? (summary.metrics.bias as number).toFixed(3) : "—" },
                  { label: "Rows evaluated", value: String(summary.metrics.rows_evaluated ?? "—") },
                ].map((m) => (
                  <KpiCard key={m.label} label={m.label} value={m.value} />
                ))}
              </div>
            </section>
          )}

          {/* Model WAPE comparison chart */}
          {metricsBarData.length > 0 && (
            <ChartCard
              title="Model WAPE Comparison"
              subtitle="Lower WAPE is better. Overall level, all available models."
            >
              <BarChartPanel
                data={metricsBarData}
                height={180}
                emptyMessage="No metrics available."
                valueFormatter={(v) => `${v}%`}
              />
            </ChartCard>
          )}

          {/* Product forecast drilldown */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Product Forecast Drilldown
            </h2>
            <div style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
              <input
                type="text"
                value={productInput}
                onChange={(e) => setProductInput(e.target.value)}
                placeholder="Enter product ID…"
                onKeyDown={(e) => { if (e.key === "Enter") loadProductForecast(productInput); }}
                style={{
                  flex: 1,
                  padding: "6px 10px",
                  borderRadius: "6px",
                  border: "1px solid var(--border)",
                  background: "var(--surface-2)",
                  color: "var(--text-primary)",
                  fontSize: "13px",
                  fontFamily: "monospace",
                }}
              />
              <button
                onClick={() => loadProductForecast(productInput)}
                disabled={!productInput.trim() || productLoading}
                style={{
                  padding: "6px 16px",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: !productInput.trim() || productLoading ? "not-allowed" : "pointer",
                  border: "1px solid var(--accent)",
                  background: "var(--accent)",
                  color: "#fff",
                  opacity: !productInput.trim() || productLoading ? 0.6 : 1,
                }}
              >
                {productLoading ? "Loading…" : "Load"}
              </button>
            </div>

            {productError && (
              <div style={{ color: "#dc2626", fontSize: "12px", marginBottom: "12px" }}>
                {productError}
              </div>
            )}

            {productForecast && productForecast.rows.length > 0 && (
              <ChartCard
                title={`Actual vs Forecast — ${productId}`}
                subtitle={`${productForecast.total} forecast rows · run ${productForecast.run_id?.slice(0, 16) ?? "unknown"}…`}
              >
                <LineChartPanel
                  data={forecastChartData}
                  xKey="date"
                  series={[
                    { key: "actual", label: "Actual", color: "#1d4ed8" },
                    { key: "p50", label: "Forecast (p50)", color: "#f59e0b" },
                    { key: "p90", label: "Upper band (p90)", color: "#d1d5db", dashed: true },
                    { key: "p10", label: "Lower band (p10)", color: "#d1d5db", dashed: true },
                  ]}
                  height={220}
                  emptyMessage="No forecast rows for this product."
                  valueFormatter={(v) => v.toFixed(1)}
                />
              </ChartCard>
            )}

            {productForecast && productForecast.rows.length === 0 && (
              <EmptyState
                title="No forecast rows found for this product."
                message="Try a different product ID, or run the baseline forecast first."
              />
            )}
          </section>

          {/* Latest run */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Latest Forecast Run
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              {[
                { label: "Run ID", value: summary.latest_run?.run_id as string },
                { label: "Model type", value: summary.latest_run?.model_type as string },
                { label: "Mode", value: summary.latest_run?.mode as string },
                { label: "Horizon (days)", value: String(summary.latest_run?.horizon_days ?? "—") },
                { label: "Forecast rows", value: String(summary.latest_run?.rows_created ?? "—") },
                { label: "Completed at", value: (summary.latest_run?.completed_at as string)?.slice(0, 19) ?? "—" },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <span style={{ fontWeight: 500, fontSize: "13px", fontFamily: "monospace" }}>{row.value ?? "—"}</span>
                </div>
              ))}
            </div>
          </section>

          {/* All runs table */}
          {runs && runs.runs.length > 0 && (
            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Recent Runs
              </h2>
              <DataTable
                columns={[
                  { key: "model_type", header: "Model" },
                  { key: "mode", header: "Mode", render: (r) => <StatusBadge value={r.mode as string} /> },
                  { key: "horizon_days", header: "Horizon", align: "right" },
                  { key: "rows_created", header: "Rows", align: "right" },
                  { key: "status", header: "Status", render: (r) => <StatusBadge value={r.status as string} /> },
                  { key: "started_at", header: "Started", render: (r) => (r.started_at as string)?.slice(0, 19) ?? "—" },
                ]}
                rows={runs.runs as unknown as Record<string, unknown>[]}
                emptyMessage="No forecast runs found."
              />
            </section>
          )}

          {/* Per-model metrics table */}
          {metrics && metrics.metrics.length > 0 && (
            <section>
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Metrics by Model (overall level)
              </h2>
              <DataTable
                columns={[
                  { key: "model_type", header: "Model" },
                  { key: "wape", header: "WAPE", align: "right", render: (r) => fmtPct(r.wape as number) },
                  { key: "mae", header: "MAE", align: "right", render: (r) => r.mae != null ? (r.mae as number).toFixed(2) : "—" },
                  { key: "smape", header: "SMAPE", align: "right", render: (r) => fmtPct(r.smape as number) },
                  { key: "rows_evaluated", header: "Rows", align: "right" },
                ]}
                rows={metrics.metrics as unknown as Record<string, unknown>[]}
              />
            </section>
          )}
        </>
      )}
    </div>
  );
}
