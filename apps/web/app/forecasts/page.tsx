"use client";

import { useEffect, useState } from "react";
import {
  getDashboardForecastSummary,
  getForecastRuns,
  getModelMetrics,
  getProductForecast,
  getForecastDiagnostics,
  getDSModelComparison,
} from "@/lib/api";
import type {
  DashboardForecastSummaryResponse,
  ForecastRunsResponse,
  ModelMetricsResponse,
  ProductForecastResponse,
  ForecastDiagnosticsResponse,
  ModelComparisonResponse,
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
import Link from "next/link";

const QUALITY_COLORS: Record<string, string> = {
  strong: "#15803d",
  directional: "#a16207",
  weak: "#dc2626",
  unknown: "#6b7280",
};

const QUALITY_LABELS: Record<string, string> = {
  strong: "Strong",
  directional: "Directional",
  weak: "Weak",
  unknown: "No model",
};

const GLOSSARY = [
  {
    term: "WAPE",
    def: "Weighted Absolute Percentage Error. Measures average forecast error relative to total actual demand. Lower is better. Below 30% is strong; 30–60% is directional; above 60% is weak.",
  },
  {
    term: "MAE",
    def: "Mean Absolute Error. The average of absolute differences between forecast and actual. Expressed in units — easier to interpret than percentage metrics.",
  },
  {
    term: "RMSE",
    def: "Root Mean Squared Error. Penalises large errors more than MAE. Higher RMSE relative to MAE signals occasional large forecast misses.",
  },
  {
    term: "Bias",
    def: "Mean signed error (forecast minus actual). Positive bias means the model systematically over-forecasts; negative means under-forecasting.",
  },
  {
    term: "Backtest",
    def: "Evaluation on historical data where actuals are already known. The model is trained only on data before the test window to prevent leakage.",
  },
  {
    term: "Planning forecast",
    def: "A forward-looking forecast for future dates where no actuals exist yet. Used to compute stockout risk and reorder recommendations.",
  },
  {
    term: "Prediction interval",
    def: "The p10–p90 band around the p50 (median) forecast. It represents the range within which actual demand is expected to fall 80% of the time under the model's assumptions.",
  },
];

export default function ForecastsPage() {
  const [summary, setSummary] = useState<DashboardForecastSummaryResponse | null>(null);
  const [runs, setRuns] = useState<ForecastRunsResponse | null>(null);
  const [metrics, setMetrics] = useState<ModelMetricsResponse | null>(null);
  const [diagnostics, setDiagnostics] = useState<ForecastDiagnosticsResponse | null>(null);
  const [comparison, setComparison] = useState<ModelComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [glossaryOpen, setGlossaryOpen] = useState(false);

  // Product drilldown
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
      getForecastDiagnostics().catch(() => null),
      getDSModelComparison().catch(() => null),
    ])
      .then(([s, r, m, d, c]) => {
        setSummary(s);
        setRuns(r);
        setMetrics(m);
        setDiagnostics(d);
        setComparison(c);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const loadProductForecast = (id: string) => {
    if (!id.trim()) return;
    setProductLoading(true);
    setProductError(null);
    setProductForecast(null);
    getProductForecast(id.trim(), { limit: 100 })
      .then(setProductForecast)
      .catch((e) => setProductError(e.message))
      .finally(() => setProductLoading(false));
  };

  const fmtPct = (n: number | null | undefined) =>
    n == null ? "—" : `${(n * 100).toFixed(1)}%`;

  const forecastChartData = productForecast?.rows.map((r) => ({
    date: r.forecast_date?.slice(0, 10) ?? "",
    actual: r.actual_units ?? null,
    p50: r.p50_units ?? null,
    p10: r.p10_units ?? null,
    p90: r.p90_units ?? null,
  })) ?? [];

  const metricsBarData = metrics?.metrics
    .filter((m) => m.wape != null)
    .map((m) => ({
      name: m.model_type.replace(/_/g, " "),
      value: Math.round((m.wape ?? 0) * 1000) / 10,
    })) ?? [];

  const latestDiag = diagnostics?.ml_model ?? diagnostics?.baseline ?? null;

  return (
    <div>
      <PageHeader
        title="Demand Forecasts"
        subtitle="Backtest accuracy, model comparison, and product-level prediction intervals."
        kicker="Forecasting"
        badge="Computed from pipeline · not production-calibrated"
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && summary && !summary.has_forecast && (
        <EmptyState
          title="No forecast run generated yet."
          message="Go to Pipeline Controls and run the Baseline Forecast step, or run POST /api/forecasts/baseline/run."
        />
      )}

      {summary?.has_forecast && (
        <>
          {/* Explainer card */}
          <div
            style={{
              background: "#f0f9ff",
              border: "1px solid #bae6fd",
              borderRadius: "8px",
              padding: "16px 20px",
              marginBottom: "24px",
            }}
          >
            <h2 style={{ fontSize: "13px", fontWeight: 600, color: "#0c4a6e", marginBottom: "8px" }}>
              About these forecasts
            </h2>
            <ul style={{ margin: 0, paddingLeft: "18px" }}>
              <li style={{ fontSize: "13px", color: "#0c4a6e", marginBottom: "4px", lineHeight: 1.5 }}>
                Forecasts are generated from leakage-safe historical demand features (lag, rolling windows, calendar, price, promotions).
              </li>
              <li style={{ fontSize: "13px", color: "#0c4a6e", marginBottom: "4px", lineHeight: 1.5 }}>
                Forecast outputs feed the stockout risk engine and reorder recommendation pipeline.
              </li>
              <li style={{ fontSize: "13px", color: "#0c4a6e", lineHeight: 1.5 }}>
                This is a prototype on synthetic data. Treat forecast outputs as directional planning signals, not production-calibrated estimates.
              </li>
            </ul>
            <div style={{ marginTop: "10px" }}>
              <Link href="/data-science" style={{ fontSize: "12px", color: "#0369a1" }}>
                View full ML Insights →
              </Link>
            </div>
          </div>

          {/* Model quality cards */}
          {latestDiag && (
            <div style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
                Model Quality
              </h2>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                  gap: "12px",
                  marginBottom: "12px",
                }}
              >
                {[
                  {
                    label: "WAPE",
                    value: fmtPct(latestDiag.wape),
                    note: "lower is better",
                  },
                  {
                    label: "MAE",
                    value: latestDiag.mae != null ? latestDiag.mae.toFixed(2) : "—",
                    note: "mean abs. error",
                  },
                  {
                    label: "RMSE",
                    value: latestDiag.rmse != null ? latestDiag.rmse.toFixed(2) : "—",
                    note: "root mean sq. error",
                  },
                  {
                    label: "Bias",
                    value: latestDiag.bias != null ? latestDiag.bias.toFixed(3) : "—",
                    note: "+over / −under",
                  },
                ].map((m) => (
                  <div
                    key={m.label}
                    style={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      padding: "14px",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                      {m.label}
                    </div>
                    <div style={{ fontSize: "20px", fontWeight: 700 }}>{m.value}</div>
                    <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "3px" }}>
                      {m.note}
                    </div>
                  </div>
                ))}
                <div
                  style={{
                    background: "var(--surface)",
                    border: `1px solid ${QUALITY_COLORS[latestDiag.quality_label] ?? "var(--border)"}44`,
                    borderRadius: "6px",
                    padding: "14px",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                    QUALITY
                  </div>
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: 700,
                      color: QUALITY_COLORS[latestDiag.quality_label] ?? "#6b7280",
                    }}
                  >
                    {QUALITY_LABELS[latestDiag.quality_label] ?? latestDiag.quality_label}
                  </div>
                  <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "3px" }}>
                    {latestDiag.model_name}
                  </div>
                </div>
              </div>
              {latestDiag.interpretation && (
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "0 0 4px" }}>
                  {latestDiag.interpretation}
                </p>
              )}
              {latestDiag.warning && (
                <div
                  style={{
                    fontSize: "12px",
                    color: "#92400e",
                    background: "#fef3c7",
                    borderRadius: "4px",
                    padding: "8px 12px",
                    marginTop: "8px",
                  }}
                >
                  {latestDiag.warning}
                </div>
              )}
            </div>
          )}

          {/* Model comparison */}
          {comparison && comparison.models.length >= 2 && (
            <div style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
                Model Comparison
              </h2>
              <BarChartPanel
                data={comparison.models
                  .filter((m) => m.wape != null)
                  .map((m) => ({
                    name: m.model_name,
                    value: Math.round((m.wape ?? 0) * 1000) / 10,
                  }))}
                height={160}
                emptyMessage="No model metrics available."
                valueFormatter={(v) => `${v}%`}
              />
              <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                WAPE comparison — lower is better. Ranked from best (left) to weakest.
              </p>
            </div>
          )}

          {/* Overall metric KPIs (existing) */}
          {summary.metrics && (
            <section style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
                Latest Planning Forecast
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "12px" }}>
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

          {/* Product forecast drilldown */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "4px" }}>
              Product Forecast Drilldown
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Enter a product ID to view its forecast vs actual chart with prediction intervals.
            </p>
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
              <div style={{ color: "#dc2626", fontSize: "12px", marginBottom: "12px" }}>{productError}</div>
            )}

            {productForecast && productForecast.rows.length > 0 && (
              <>
                <ChartCard
                  title={`Actual vs Forecast — ${productForecast.run_id ? "Latest planning run" : "—"}`}
                  subtitle="Blue = actual demand. Orange = p50 forecast. Grey bands = p10/p90 prediction interval."
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
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                  {productForecast.total} forecast rows. Prediction intervals are heuristic-based ±20% around p50 for this prototype.
                </p>
              </>
            )}

            {productForecast && productForecast.rows.length === 0 && (
              <EmptyState
                title="No forecast rows found for this product."
                message="Try a different product ID, or run the baseline forecast first."
              />
            )}
          </section>

          {/* Latest run — technical details collapsible */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
              Latest Forecast Run — Details
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              {[
                {
                  label: "Model",
                  value: summary.latest_run?.model_type
                    ? (summary.latest_run.model_type as string).replace(/_/g, " ")
                    : "—",
                },
                { label: "Horizon (days)", value: String(summary.latest_run?.horizon_days ?? "—") },
                { label: "Forecast rows", value: String(summary.latest_run?.rows_created ?? "—") },
                { label: "Completed at", value: (summary.latest_run?.completed_at as string)?.slice(0, 19) ?? "—" },
                { label: "Run ID", value: (summary.latest_run?.run_id as string)?.slice(0, 24) + "…" ?? "—" },
              ].map((row, i, arr) => (
                <div
                  key={row.label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "11px 18px",
                    borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <span style={{ fontWeight: 500, fontSize: "13px", fontFamily: "monospace" }}>{row.value ?? "—"}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Recent runs */}
          {runs && runs.runs.length > 0 && (
            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
                Recent Forecast Runs
              </h2>
              <DataTable
                columns={[
                  {
                    key: "model_type",
                    header: "Model",
                    render: (r) => (r.model_type as string).replace(/_/g, " "),
                  },
                  { key: "mode", header: "Mode", render: (r) => <StatusBadge value={r.mode as string} /> },
                  { key: "horizon_days", header: "Horizon", align: "right" },
                  { key: "rows_created", header: "Rows", align: "right" },
                  { key: "status", header: "Status", render: (r) => <StatusBadge value={r.status as string} /> },
                  {
                    key: "started_at",
                    header: "Started",
                    render: (r) => (r.started_at as string)?.slice(0, 19) ?? "—",
                  },
                ]}
                rows={runs.runs as unknown as Record<string, unknown>[]}
                emptyMessage="No forecast runs found."
              />
            </section>
          )}

          {/* Glossary */}
          <section style={{ marginBottom: "24px" }}>
            <button
              onClick={() => setGlossaryOpen((v) => !v)}
              style={{
                background: "none",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                padding: "8px 14px",
                fontSize: "12px",
                cursor: "pointer",
                color: "var(--text-secondary)",
              }}
            >
              {glossaryOpen ? "▲ Hide" : "▼ Show"} metric glossary
            </button>
            {glossaryOpen && (
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "6px",
                  padding: "16px",
                  marginTop: "8px",
                }}
              >
                {GLOSSARY.map((g) => (
                  <div key={g.term} style={{ marginBottom: "10px" }}>
                    <span style={{ fontWeight: 600, fontSize: "13px" }}>{g.term}: </span>
                    <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{g.def}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
