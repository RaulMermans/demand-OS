"use client";

import { useEffect, useState } from "react";
import { getDashboardForecastSummary, getForecastRuns, getModelMetrics } from "@/lib/api";
import type {
  DashboardForecastSummaryResponse,
  ForecastRunsResponse,
  ModelMetricsResponse,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import DataTable from "@/components/DataTable";

export default function ForecastsPage() {
  const [summary, setSummary] = useState<DashboardForecastSummaryResponse | null>(null);
  const [runs, setRuns] = useState<ForecastRunsResponse | null>(null);
  const [metrics, setMetrics] = useState<ModelMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

  const fmtPct = (n: number | null | undefined) =>
    n == null ? "—" : `${(n * 100).toFixed(2)}%`;

  return (
    <div>
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "4px" }}>Forecasts</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Demand forecast runs and model accuracy metrics
      </p>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && summary && !summary.has_forecast && (
        <EmptyState
          title="No forecast run has been generated yet."
          message="Run POST /api/forecasts/baseline/run to generate a baseline forecast, or POST /api/models/train to train the ML model."
        />
      )}

      {summary?.has_forecast && (
        <>
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
                { label: "Completed at", value: summary.latest_run?.completed_at as string ?? "—" },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <span style={{ fontWeight: 500, fontSize: "13px", fontFamily: "monospace" }}>{row.value ?? "—"}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Overall metrics */}
          {summary.metrics && (
            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Overall Metrics (latest run)
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
                  <div key={m.label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px", textAlign: "center" }}>
                    <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{m.label}</div>
                    <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "4px" }}>{m.value}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

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
                  { key: "mae", header: "MAE", align: "right", render: (r) => (r.mae != null ? (r.mae as number).toFixed(2) : "—") },
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
