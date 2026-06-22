"use client";

import { useEffect, useState } from "react";
import {
  getDashboardModelSummary,
  getModelVersions,
  getModelMetrics,
  getForecastDiagnostics,
  getFeatureSignals,
  getDSModelComparison,
} from "@/lib/api";
import type {
  DashboardModelSummaryResponse,
  ModelVersionsResponse,
  ModelMetricsResponse,
  ForecastDiagnosticsResponse,
  FeatureSignalsResponse,
  ModelComparisonResponse,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import DataTable from "@/components/DataTable";
import ChartCard from "@/components/ChartCard";
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
  unknown: "Unknown",
};

export default function ModelPerformancePage() {
  const [summary, setSummary] = useState<DashboardModelSummaryResponse | null>(null);
  const [versions, setVersions] = useState<ModelVersionsResponse | null>(null);
  const [metrics, setMetrics] = useState<ModelMetricsResponse | null>(null);
  const [diagnostics, setDiagnostics] = useState<ForecastDiagnosticsResponse | null>(null);
  const [signals, setSignals] = useState<FeatureSignalsResponse | null>(null);
  const [comparison, setComparison] = useState<ModelComparisonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getDashboardModelSummary(),
      getModelVersions(10),
      getModelMetrics({ limit: 50 }),
      getForecastDiagnostics().catch(() => null),
      getFeatureSignals().catch(() => null),
      getDSModelComparison().catch(() => null),
    ])
      .then(([s, v, m, d, f, c]) => {
        setSummary(s);
        setVersions(v);
        setMetrics(m);
        setDiagnostics(d);
        setSignals(f);
        setComparison(c);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const fmtPct = (n: number | null | undefined) =>
    n == null ? "—" : `${(n * 100).toFixed(1)}%`;

  const latestDiag = diagnostics?.ml_model ?? diagnostics?.baseline ?? null;
  const qualityLabel = latestDiag?.quality_label ?? "unknown";

  const compChartData = comparison?.models
    .filter((m) => m.wape != null)
    .map((m) => ({
      name: m.model_name,
      value: Math.round((m.wape ?? 0) * 1000) / 10,
    })) ?? [];

  return (
    <div>
      <PageHeader
        title="Model Performance"
        subtitle="Evaluation metrics, baseline vs ML comparison, and feature signal explanation."
        kicker="ML evaluation"
        badge="Backtest results · synthetic data"
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && summary && !summary.has_ml_model && (
        <>
          {/* Show baseline info even without ML model */}
          {diagnostics?.baseline && (
            <div
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "20px",
                marginBottom: "24px",
              }}
            >
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "8px" }}>
                Best Baseline — {diagnostics.baseline.model_name}
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: "10px" }}>
                {[
                  { label: "WAPE", value: fmtPct(diagnostics.baseline.wape) },
                  { label: "MAE", value: diagnostics.baseline.mae?.toFixed(2) ?? "—" },
                  { label: "RMSE", value: diagnostics.baseline.rmse?.toFixed(2) ?? "—" },
                  { label: "Bias", value: diagnostics.baseline.bias?.toFixed(3) ?? "—" },
                ].map((m) => (
                  <KpiCard key={m.label} label={m.label} value={m.value} />
                ))}
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "12px" }}>
                {diagnostics.baseline.interpretation}
              </p>
            </div>
          )}
          <EmptyState
            title="No ML model trained yet."
            message="Go to Pipeline Controls and run Train ML Model, or run POST /api/models/train. Baseline metrics are shown above."
          />
        </>
      )}

      {(summary?.has_ml_model || diagnostics?.baseline) && (
        <>
          {/* Quality summary */}
          {latestDiag && (
            <div
              style={{
                background: "var(--surface)",
                border: `1px solid ${QUALITY_COLORS[qualityLabel] ?? "var(--border)"}44`,
                borderRadius: "8px",
                padding: "18px 22px",
                marginBottom: "24px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Latest model
                  </div>
                  <div style={{ fontSize: "16px", fontWeight: 700 }}>{latestDiag.model_name}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "4px 12px",
                      borderRadius: "4px",
                      fontWeight: 700,
                      fontSize: "13px",
                      background: `${QUALITY_COLORS[qualityLabel]}22`,
                      color: QUALITY_COLORS[qualityLabel] ?? "#6b7280",
                      border: `1px solid ${QUALITY_COLORS[qualityLabel]}44`,
                    }}
                  >
                    {QUALITY_LABELS[qualityLabel] ?? qualityLabel}
                  </span>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>
                    WAPE {fmtPct(latestDiag.wape)}
                  </div>
                </div>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "10px", marginBottom: 0 }}>
                {latestDiag.interpretation}
              </p>
              {latestDiag.warning && (
                <div
                  style={{
                    marginTop: "10px",
                    padding: "8px 12px",
                    background: "#fef3c7",
                    borderRadius: "4px",
                    fontSize: "12px",
                    color: "#92400e",
                  }}
                >
                  {latestDiag.warning}
                </div>
              )}
            </div>
          )}

          {/* Model leaderboard */}
          {compChartData.length > 0 && (
            <div style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "8px" }}>
                Model Leaderboard
              </h2>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                WAPE comparison across all completed model runs. Lower WAPE = better forecast accuracy.
              </p>
              <BarChartPanel
                data={compChartData}
                height={160}
                emptyMessage="No model metrics available."
                valueFormatter={(v) => `${v}%`}
              />
              {comparison && (
                <div style={{ overflowX: "auto", marginTop: "16px" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                    <thead>
                      <tr>
                        {["Rank", "Model", "WAPE", "MAE", "Bias", "Quality", "Best for"].map((h) => (
                          <th
                            key={h}
                            style={{
                              textAlign: "left",
                              padding: "6px 10px",
                              borderBottom: "2px solid var(--border)",
                              color: "var(--text-secondary)",
                              fontSize: "11px",
                              fontWeight: 600,
                              whiteSpace: "nowrap",
                            }}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {comparison.models.map((m) => (
                        <tr key={m.model_type} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "7px 10px", fontWeight: 700 }}>#{m.rank}</td>
                          <td style={{ padding: "7px 10px", fontWeight: 600 }}>{m.model_name}</td>
                          <td style={{ padding: "7px 10px" }}>{fmtPct(m.wape)}</td>
                          <td style={{ padding: "7px 10px" }}>{m.mae?.toFixed(3) ?? "—"}</td>
                          <td style={{ padding: "7px 10px" }}>{m.bias?.toFixed(3) ?? "—"}</td>
                          <td style={{ padding: "7px 10px" }}>
                            <span
                              style={{
                                color: QUALITY_COLORS[m.quality_label] ?? "#6b7280",
                                fontWeight: 600,
                              }}
                            >
                              {QUALITY_LABELS[m.quality_label] ?? m.quality_label}
                            </span>
                          </td>
                          <td style={{ padding: "7px 10px", color: "var(--text-secondary)", maxWidth: "160px" }}>
                            {m.best_for}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Error interpretation */}
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "18px 22px",
              marginBottom: "24px",
            }}
          >
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
              Error Interpretation Guide
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
              {[
                {
                  label: "WAPE < 30%",
                  badge: "Strong",
                  color: QUALITY_COLORS.strong,
                  desc: "Strong demand signal. Reliable directional forecast for inventory planning on this synthetic dataset.",
                },
                {
                  label: "WAPE 30–60%",
                  badge: "Directional",
                  color: QUALITY_COLORS.directional,
                  desc: "Usable directional signal. Forecasts indicate demand direction but point estimates have meaningful uncertainty.",
                },
                {
                  label: "WAPE > 60%",
                  badge: "Weak",
                  color: QUALITY_COLORS.weak,
                  desc: "Weak signal. Treat with caution. The model captures some pattern but should not be relied on for precise quantities.",
                },
                {
                  label: "Bias",
                  badge: null,
                  color: "#6b7280",
                  desc: "Positive bias = over-forecasting. Negative bias = under-forecasting. Small bias is acceptable; large bias suggests a systematic problem.",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    background: "var(--border)",
                    borderRadius: "6px",
                    padding: "12px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                    <span style={{ fontWeight: 600, fontSize: "12px" }}>{item.label}</span>
                    {item.badge && (
                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 600,
                          color: item.color,
                          background: `${item.color}22`,
                          border: `1px solid ${item.color}44`,
                          padding: "1px 6px",
                          borderRadius: "3px",
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Feature signal groups */}
          {signals && signals.signals.length > 0 && (
            <div style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "4px" }}>
                Feature Signal Groups
              </h2>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                {signals.total_features} features across {signals.signals.filter((s) => s.available).length} active groups.
              </p>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "10px",
                }}
              >
                {signals.signals.map((grp) => (
                  <div
                    key={grp.group}
                    style={{
                      background: grp.available ? "var(--surface)" : "var(--border)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      padding: "12px",
                      opacity: grp.available ? 1 : 0.6,
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: "12px", marginBottom: "4px" }}>{grp.group}</div>
                    <p style={{ fontSize: "11px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.4 }}>
                      {grp.interpretation}
                    </p>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: "8px" }}>
                <Link href="/data-science" style={{ fontSize: "12px" }}>
                  View detailed ML Insights →
                </Link>
              </div>
            </div>
          )}

          {/* ML model KPI summary */}
          {summary?.has_ml_model && summary.latest_model_version && (
            <section style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
                Latest ML Model Details
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px" }}>
                {[
                  { label: "Algorithm", value: summary.latest_model_version?.algorithm as string ?? "—" },
                  {
                    label: "ML WAPE",
                    value: summary.latest_model_version?.ml_wape != null
                      ? fmtPct(summary.latest_model_version.ml_wape as number)
                      : "—",
                  },
                  {
                    label: "Baseline WAPE",
                    value: summary.baseline_comparison?.best_baseline_wape != null
                      ? fmtPct(summary.baseline_comparison.best_baseline_wape as number)
                      : "—",
                  },
                  {
                    label: "ML outperforms",
                    value: summary.baseline_comparison?.ml_won != null
                      ? (summary.baseline_comparison.ml_won ? "Yes" : "No")
                      : "—",
                  },
                ].map((m) => (
                  <KpiCard key={m.label} label={m.label} value={m.value} />
                ))}
              </div>
            </section>
          )}

          {/* Metrics table */}
          {metrics && metrics.metrics.length > 0 && (
            <section style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
                Metrics by Model and Level
              </h2>
              <DataTable
                columns={[
                  { key: "model_type", header: "Model", render: (r) => (r.model_type as string).replace(/_/g, " ") },
                  { key: "level", header: "Level" },
                  { key: "level_value", header: "Value" },
                  { key: "wape", header: "WAPE", align: "right", render: (r) => fmtPct(r.wape as number) },
                  {
                    key: "mae",
                    header: "MAE",
                    align: "right",
                    render: (r) => r.mae != null ? (r.mae as number).toFixed(2) : "—",
                  },
                  { key: "smape", header: "SMAPE", align: "right", render: (r) => fmtPct(r.smape as number) },
                  { key: "rows_evaluated", header: "Rows", align: "right" },
                ]}
                rows={metrics.metrics as unknown as Record<string, unknown>[]}
              />
            </section>
          )}

          {/* Limitations */}
          <div
            style={{
              background: "var(--border)",
              borderRadius: "8px",
              padding: "18px 22px",
              marginBottom: "24px",
            }}
          >
            <h2 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "10px" }}>
              Limitations
            </h2>
            <ul style={{ margin: 0, paddingLeft: "18px" }}>
              {[
                "All data is synthetic. Metrics reflect simulated retail patterns, not real demand.",
                "The ML model is a HistGradientBoosting prototype on a small dataset. It is not production-calibrated.",
                "WAPE thresholds (Strong / Directional / Weak) are for demo evaluation context only.",
                "Prediction intervals are heuristic ±20% bands. They are not statistically rigorous confidence intervals.",
                "Feature importances are not yet exposed in the UI. Use feature signal groups as an indication of input types.",
              ].map((line, i) => (
                <li key={i} style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "5px", lineHeight: 1.5 }}>
                  {line}
                </li>
              ))}
            </ul>
          </div>

          {/* Model versions registry */}
          {versions && versions.versions.length > 0 && (
            <section>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
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
