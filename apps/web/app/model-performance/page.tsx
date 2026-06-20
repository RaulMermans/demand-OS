"use client";

import { useEffect, useState } from "react";
import { getDashboardModelSummary, getModelVersions, getModelMetrics } from "@/lib/api";
import type {
  DashboardModelSummaryResponse,
  ModelVersionsResponse,
  ModelMetricsResponse,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import DataTable from "@/components/DataTable";

export default function ModelPerformancePage() {
  const [summary, setSummary] = useState<DashboardModelSummaryResponse | null>(null);
  const [versions, setVersions] = useState<ModelVersionsResponse | null>(null);
  const [metrics, setMetrics] = useState<ModelMetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getDashboardModelSummary(),
      getModelVersions(10),
      getModelMetrics({ limit: 50 }),
    ])
      .then(([s, v, m]) => { setSummary(s); setVersions(v); setMetrics(m); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const fmtPct = (n: number | null | undefined) =>
    n == null ? "—" : `${(n * 100).toFixed(2)}%`;

  return (
    <div>
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "4px" }}>Model Performance</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        ML model registry, accuracy metrics, and baseline comparison
      </p>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && summary && !summary.has_ml_model && (
        <EmptyState
          title="No ML model has been trained yet."
          message="Run POST /api/models/train to train the ML forecasting model. Baseline metrics are available via POST /api/forecasts/baseline/run."
        />
      )}

      {summary?.has_ml_model && (
        <>
          {/* Latest model summary */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Latest ML Model
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              {[
                { label: "Algorithm", value: summary.latest_model_version?.algorithm as string },
                { label: "Status", value: <StatusBadge value={summary.latest_model_version?.status as string} /> },
                { label: "Trained at", value: (summary.latest_model_version?.trained_at as string)?.slice(0, 19) ?? "—" },
                { label: "ML WAPE", value: summary.latest_model_version?.ml_wape != null ? fmtPct(summary.latest_model_version.ml_wape as number) : "—" },
                { label: "Artifact exists", value: summary.latest_model_version?.artifact_exists ? "Yes" : "No" },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <span style={{ fontWeight: 500 }}>{row.value ?? "—"}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Baseline comparison */}
          {summary.baseline_comparison && (
            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Baseline vs ML Comparison
              </h2>
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
                {[
                  { label: "Best baseline model", value: summary.baseline_comparison.best_baseline_model_type as string ?? "—" },
                  { label: "Best baseline WAPE", value: fmtPct(summary.baseline_comparison.best_baseline_wape as number) },
                  { label: "ML WAPE", value: fmtPct(summary.baseline_comparison.ml_wape as number) },
                  { label: "WAPE delta (ML − baseline)", value: summary.baseline_comparison.wape_delta != null ? `${((summary.baseline_comparison.wape_delta as number) * 100).toFixed(2)}pp` : "—" },
                  { label: "ML outperforms baseline", value: summary.baseline_comparison.ml_won != null ? (summary.baseline_comparison.ml_won ? "Yes" : "No") : "—" },
                ].map((row, i, arr) => (
                  <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                    <span style={{ fontWeight: 500 }}>{row.value}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Metrics table */}
          {metrics && metrics.metrics.length > 0 && (
            <section style={{ marginBottom: "32px" }}>
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Metrics by Model and Level
              </h2>
              <DataTable
                columns={[
                  { key: "model_type", header: "Model" },
                  { key: "level", header: "Level" },
                  { key: "level_value", header: "Value" },
                  { key: "wape", header: "WAPE", align: "right", render: (r) => fmtPct(r.wape as number) },
                  { key: "mae", header: "MAE", align: "right", render: (r) => r.mae != null ? (r.mae as number).toFixed(2) : "—" },
                  { key: "smape", header: "SMAPE", align: "right", render: (r) => fmtPct(r.smape as number) },
                  { key: "rows_evaluated", header: "Rows", align: "right" },
                ]}
                rows={metrics.metrics as unknown as Record<string, unknown>[]}
              />
            </section>
          )}

          {/* Model versions */}
          {versions && versions.versions.length > 0 && (
            <section>
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Model Registry
              </h2>
              <DataTable
                columns={[
                  { key: "algorithm", header: "Algorithm" },
                  { key: "model_type", header: "Type" },
                  { key: "status", header: "Status", render: (r) => <StatusBadge value={r.status as string} /> },
                  { key: "trained_at", header: "Trained at", render: (r) => (r.trained_at as string)?.slice(0, 19) ?? "—" },
                ]}
                rows={versions.versions as unknown as Record<string, unknown>[]}
              />
            </section>
          )}
        </>
      )}
    </div>
  );
}
