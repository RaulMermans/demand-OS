"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getDataScienceSummary,
  getForecastDiagnostics,
  getDSModelComparison,
  getFeatureSignals,
  getBusinessImpact,
} from "@/lib/api";
import type {
  DataScienceSummaryResponse,
  ForecastDiagnosticsResponse,
  ModelComparisonResponse,
  FeatureSignalsResponse,
  BusinessImpactResponse,
  ModelDiagnostic,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import PageHeader from "@/components/PageHeader";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

const TIER_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#c2410c",
  medium: "#a16207",
  low: "#15803d",
  unknown: "#6b7280",
};

function fmt(n: number | null | undefined, dec = 0): string {
  return n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: dec });
}

function fmtPct(n: number | null | undefined): string {
  return n == null ? "—" : `${(n * 100).toFixed(1)}%`;
}

function QualityBadge({ label }: { label: string }) {
  const color = QUALITY_COLORS[label] ?? "#6b7280";
  const text = QUALITY_LABELS[label] ?? label;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: 600,
        background: `${color}22`,
        color,
        border: `1px solid ${color}44`,
      }}
    >
      {text}
    </span>
  );
}

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "24px",
        marginBottom: "24px",
      }}
    >
      <h2 style={{ fontSize: "16px", fontWeight: 600, margin: "0 0 4px" }}>{title}</h2>
      {subtitle && (
        <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "0 0 16px" }}>
          {subtitle}
        </p>
      )}
      {children}
    </div>
  );
}

function MetricRow({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        padding: "8px 0",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
        {label}
        {note && (
          <span style={{ fontSize: "11px", marginLeft: "6px", fontStyle: "italic" }}>
            ({note})
          </span>
        )}
      </span>
      <span style={{ fontSize: "14px", fontWeight: 600 }}>{value}</span>
    </div>
  );
}

function DiagnosticCard({ diag, label }: { diag: ModelDiagnostic; label: string }) {
  return (
    <div
      style={{
        background: "var(--surface-secondary, #f9fafb)",
        border: "1px solid var(--border)",
        borderRadius: "6px",
        padding: "16px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "12px",
        }}
      >
        <div>
          <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "2px" }}>
            {label}
          </div>
          <div style={{ fontWeight: 600, fontSize: "14px" }}>{diag.model_name}</div>
        </div>
        <QualityBadge label={diag.quality_label} />
      </div>
      <MetricRow label="WAPE" value={fmtPct(diag.wape)} note="lower is better" />
      <MetricRow label="MAE" value={diag.mae != null ? diag.mae.toFixed(3) : "—"} note="mean absolute error" />
      <MetricRow label="RMSE" value={diag.rmse != null ? diag.rmse.toFixed(3) : "—"} note="root mean squared error" />
      <MetricRow label="Bias" value={diag.bias != null ? diag.bias.toFixed(3) : "—"} note="systematic over/under-forecast" />
      <MetricRow label="Forecast rows" value={fmt(diag.forecast_rows)} />
      {diag.backtest_horizon_days && (
        <MetricRow label="Backtest horizon" value={`${diag.backtest_horizon_days} days`} />
      )}
      <p
        style={{
          fontSize: "12px",
          color: "var(--text-secondary)",
          marginTop: "12px",
          lineHeight: 1.5,
        }}
      >
        {diag.interpretation}
      </p>
      {diag.warning && (
        <div
          style={{
            marginTop: "8px",
            padding: "8px",
            background: "#fef3c7",
            borderRadius: "4px",
            fontSize: "12px",
            color: "#92400e",
          }}
        >
          {diag.warning}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DataSciencePage() {
  const [summary, setSummary] = useState<DataScienceSummaryResponse | null>(null);
  const [diagnostics, setDiagnostics] = useState<ForecastDiagnosticsResponse | null>(null);
  const [comparison, setComparison] = useState<ModelComparisonResponse | null>(null);
  const [signals, setSignals] = useState<FeatureSignalsResponse | null>(null);
  const [impact, setImpact] = useState<BusinessImpactResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getDataScienceSummary(),
      getForecastDiagnostics(),
      getDSModelComparison(),
      getFeatureSignals(),
      getBusinessImpact(),
    ])
      .then(([s, d, c, f, i]) => {
        setSummary(s);
        setDiagnostics(d);
        setComparison(c);
        setSignals(f);
        setImpact(i);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <PageHeader
        title="ML Insights"
        subtitle="A transparent view of the demand forecasting pipeline: data volumes, model evaluation, feature signals, and decision impact."
        kicker="Data science explainability"
        badge="Read-only · computed from pipeline"
      />

      {loading && <LoadingState message="Loading ML insights..." />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && (
        <>
          {/* 1. ML Workflow Overview */}
          <SectionCard
            title="ML Workflow Overview"
            subtitle="How DemandOS transforms raw commerce records into inventory decisions."
          >
            <div
              style={{
                display: "flex",
                gap: "6px",
                flexWrap: "wrap",
                alignItems: "center",
                marginBottom: "16px",
              }}
            >
              {[
                "Raw Records",
                "→",
                "Daily Aggregation",
                "→",
                "Feature Matrix",
                "→",
                "Forecast Model",
                "→",
                "Stockout Risk",
                "→",
                "Reorder Guidance",
              ].map((step, i) => (
                <span
                  key={i}
                  style={{
                    padding: step === "→" ? "0" : "4px 10px",
                    borderRadius: "4px",
                    fontSize: "12px",
                    fontWeight: step === "→" ? 400 : 600,
                    color: step === "→" ? "var(--text-secondary)" : "var(--text-primary)",
                    background: step === "→" ? "transparent" : "var(--border)",
                  }}
                >
                  {step}
                </span>
              ))}
            </div>
            {summary && summary.pipeline_story.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: "20px" }}>
                {summary.pipeline_story.map((line, i) => (
                  <li
                    key={i}
                    style={{
                      fontSize: "13px",
                      color: "var(--text-secondary)",
                      marginBottom: "6px",
                      lineHeight: 1.5,
                    }}
                  >
                    {line}
                  </li>
                ))}
              </ul>
            )}
            {summary && summary.status === "no_data" && (
              <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                No pipeline data found. Seed demo data and run the pipeline from{" "}
                <Link href="/pipeline">Pipeline Controls</Link>.
              </p>
            )}
          </SectionCard>

          {/* 2. Data Volume */}
          {summary && summary.status === "ok" && (
            <SectionCard
              title="Data Volume & Feature Matrix"
              subtitle="How much data flows through the pipeline."
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                  gap: "12px",
                }}
              >
                {[
                  { label: "Products", value: fmt(summary.data_volume.products) },
                  { label: "Stores", value: fmt(summary.data_volume.stores) },
                  { label: "Orders", value: fmt(summary.data_volume.orders) },
                  { label: "Inventory snapshots", value: fmt(summary.data_volume.inventory_snapshots) },
                  { label: "Feature rows", value: fmt(summary.data_volume.feature_rows) },
                  { label: "Forecast rows", value: fmt(summary.data_volume.forecast_rows) },
                ].map((item) => (
                  <div
                    key={item.label}
                    style={{
                      background: "var(--border)",
                      borderRadius: "6px",
                      padding: "12px",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontSize: "22px", fontWeight: 700 }}>{item.value}</div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>
                      {item.label}
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}

          {/* 3. Model Comparison */}
          <SectionCard
            title="Model Leaderboard"
            subtitle="All completed forecast models ranked by WAPE. Lower WAPE is better."
          >
            {comparison && comparison.models.length === 0 && (
              <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                No completed forecast runs yet. Run baseline and ML forecasts from{" "}
                <Link href="/pipeline">Pipeline Controls</Link>.
              </p>
            )}
            {comparison && comparison.models.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                  <thead>
                    <tr>
                      {["Rank", "Model", "WAPE", "MAE", "RMSE", "Bias", "Quality", "Best for"].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: "left",
                            padding: "8px 12px",
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
                        <td style={{ padding: "10px 12px", fontWeight: 700 }}>#{m.rank}</td>
                        <td style={{ padding: "10px 12px", fontWeight: 600 }}>{m.model_name}</td>
                        <td style={{ padding: "10px 12px" }}>{fmtPct(m.wape)}</td>
                        <td style={{ padding: "10px 12px" }}>{m.mae != null ? m.mae.toFixed(3) : "—"}</td>
                        <td style={{ padding: "10px 12px" }}>{m.rmse != null ? m.rmse.toFixed(3) : "—"}</td>
                        <td style={{ padding: "10px 12px" }}>{m.bias != null ? m.bias.toFixed(3) : "—"}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <QualityBadge label={m.quality_label} />
                        </td>
                        <td
                          style={{
                            padding: "10px 12px",
                            color: "var(--text-secondary)",
                            fontSize: "12px",
                            maxWidth: "200px",
                          }}
                        >
                          {m.best_for}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {comparison.message && (
                  <p
                    style={{
                      fontSize: "12px",
                      color: "var(--text-secondary)",
                      marginTop: "8px",
                      fontStyle: "italic",
                    }}
                  >
                    {comparison.message}
                  </p>
                )}
              </div>
            )}
          </SectionCard>

          {/* 4. Forecast Diagnostics */}
          <SectionCard
            title="Forecast Diagnostics"
            subtitle="Error metrics from the latest backtest evaluation. WAPE = Weighted Absolute Percentage Error."
          >
            {diagnostics && !diagnostics.has_model && (
              <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                {diagnostics.message}
              </p>
            )}
            {diagnostics && diagnostics.has_model && (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                    gap: "16px",
                    marginBottom: "20px",
                  }}
                >
                  {diagnostics.baseline && (
                    <DiagnosticCard diag={diagnostics.baseline} label="Best Baseline" />
                  )}
                  {diagnostics.ml_model && (
                    <DiagnosticCard diag={diagnostics.ml_model} label="ML Model" />
                  )}
                </div>
                <div
                  style={{
                    background: "var(--border)",
                    borderRadius: "6px",
                    padding: "12px 16px",
                  }}
                >
                  <div style={{ fontSize: "12px", fontWeight: 600, marginBottom: "8px" }}>
                    WAPE interpretation guide
                  </div>
                  {Object.entries(diagnostics.wape_interpretation_guide).map(([key, text]) => (
                    <div key={key} style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                      <QualityBadge label={key} />
                      <span style={{ marginLeft: "8px" }}>{text}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </SectionCard>

          {/* 5. Feature Signal Groups */}
          <SectionCard
            title="Feature Signal Groups"
            subtitle={
              signals
                ? `${signals.total_features} features across ${signals.signals.filter((s) => s.available).length} active signal groups.`
                : "What the model uses as inputs to predict demand."
            }
          >
            {signals && (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                    gap: "12px",
                    marginBottom: "16px",
                  }}
                >
                  {signals.signals.map((grp) => (
                    <div
                      key={grp.group}
                      style={{
                        background: grp.available ? "var(--surface)" : "var(--border)",
                        border: "1px solid var(--border)",
                        borderRadius: "6px",
                        padding: "14px",
                        opacity: grp.available ? 1 : 0.6,
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: "8px",
                        }}
                      >
                        <span style={{ fontWeight: 600, fontSize: "13px" }}>{grp.group}</span>
                        <span
                          style={{
                            fontSize: "10px",
                            padding: "2px 6px",
                            borderRadius: "3px",
                            background: grp.available ? "#d1fae5" : "#fee2e2",
                            color: grp.available ? "#065f46" : "#991b1b",
                          }}
                        >
                          {grp.available ? "Active" : "Unavailable"}
                        </span>
                      </div>
                      {grp.example_features.length > 0 && (
                        <div style={{ marginBottom: "8px", display: "flex", flexWrap: "wrap", gap: "4px" }}>
                          {grp.example_features.map((f) => (
                            <code
                              key={f}
                              style={{
                                fontSize: "10px",
                                padding: "2px 5px",
                                background: "var(--border)",
                                borderRadius: "3px",
                              }}
                            >
                              {f}
                            </code>
                          ))}
                        </div>
                      )}
                      <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                        {grp.interpretation}
                      </p>
                    </div>
                  ))}
                </div>
                <p
                  style={{
                    fontSize: "12px",
                    color: "var(--text-secondary)",
                    fontStyle: "italic",
                    margin: 0,
                  }}
                >
                  {signals.disclaimer}
                </p>
              </>
            )}
          </SectionCard>

          {/* 6. Business Impact */}
          <SectionCard
            title="Business Impact Summary"
            subtitle="Decision-level view: what to review first and what actions are available."
          >
            {impact && !impact.has_data && (
              <p style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                {impact.message}
              </p>
            )}
            {impact && impact.has_data && (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                    gap: "12px",
                    marginBottom: "20px",
                  }}
                >
                  <div
                    style={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      padding: "14px",
                    }}
                  >
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                      RISK TIER DISTRIBUTION
                    </div>
                    {Object.entries(impact.risk_tier_distribution).map(([tier, count]) => (
                      <div
                        key={tier}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          padding: "3px 0",
                          fontSize: "13px",
                        }}
                      >
                        <span style={{ color: TIER_COLORS[tier] ?? "#6b7280", textTransform: "capitalize" }}>
                          {tier}
                        </span>
                        <strong>{count}</strong>
                      </div>
                    ))}
                  </div>
                  <div
                    style={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      padding: "14px",
                    }}
                  >
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                      RECOMMENDATION URGENCY
                    </div>
                    {Object.entries(impact.recommendation_urgency_distribution).map(([urg, count]) => (
                      <div
                        key={urg}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          padding: "3px 0",
                          fontSize: "13px",
                        }}
                      >
                        <span style={{ color: TIER_COLORS[urg] ?? "#6b7280", textTransform: "capitalize" }}>
                          {urg}
                        </span>
                        <strong>{count}</strong>
                      </div>
                    ))}
                  </div>
                  <div
                    style={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      padding: "14px",
                    }}
                  >
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                      FINANCIAL EXPOSURE
                    </div>
                    <div style={{ marginBottom: "8px" }}>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Est. lost sales</div>
                      <div style={{ fontSize: "18px", fontWeight: 700 }}>
                        {impact.estimated_lost_sales != null ? `€${fmt(impact.estimated_lost_sales)}` : "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Est. order cost</div>
                      <div style={{ fontSize: "18px", fontWeight: 700 }}>
                        {impact.estimated_order_cost != null ? `€${fmt(impact.estimated_order_cost)}` : "—"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Review guidance */}
                <div
                  style={{
                    background: "#f0fdf4",
                    border: "1px solid #86efac",
                    borderRadius: "6px",
                    padding: "14px",
                    marginBottom: "16px",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: "13px", marginBottom: "8px", color: "#166534" }}>
                    What to review first
                  </div>
                  <ul style={{ margin: 0, paddingLeft: "18px" }}>
                    {impact.review_guidance.map((line, i) => (
                      <li key={i} style={{ fontSize: "13px", color: "#166534", marginBottom: "4px" }}>
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Top risks */}
                {impact.top_risks.length > 0 && (
                  <div style={{ marginBottom: "16px" }}>
                    <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "10px" }}>
                      Top Risks
                    </h3>
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                        <thead>
                          <tr>
                            {["Product", "Store", "Risk tier", "Days to stockout", "Est. lost sales"].map((h) => (
                              <th
                                key={h}
                                style={{
                                  textAlign: "left",
                                  padding: "6px 10px",
                                  borderBottom: "2px solid var(--border)",
                                  color: "var(--text-secondary)",
                                  fontSize: "11px",
                                  fontWeight: 600,
                                }}
                              >
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {impact.top_risks.map((r, i) => (
                            <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                              <td style={{ padding: "7px 10px" }}>
                                {r.product_name ?? r.product_id.slice(0, 8)}
                              </td>
                              <td style={{ padding: "7px 10px", color: "var(--text-secondary)" }}>
                                {r.store_id.slice(0, 8)}
                              </td>
                              <td style={{ padding: "7px 10px" }}>
                                <span
                                  style={{
                                    color: TIER_COLORS[r.risk_tier] ?? "#6b7280",
                                    fontWeight: 600,
                                    textTransform: "capitalize",
                                  }}
                                >
                                  {r.risk_tier}
                                </span>
                              </td>
                              <td style={{ padding: "7px 10px" }}>
                                {r.days_until_stockout != null ? `${r.days_until_stockout.toFixed(0)} days` : "—"}
                              </td>
                              <td style={{ padding: "7px 10px" }}>
                                {r.lost_sales_value_estimate != null
                                  ? `€${fmt(r.lost_sales_value_estimate)}`
                                  : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div style={{ marginTop: "6px", textAlign: "right" }}>
                      <Link href="/risks" style={{ fontSize: "12px" }}>
                        View all risks →
                      </Link>
                    </div>
                  </div>
                )}

                {/* Top recommendations */}
                {impact.top_recommendations.length > 0 && (
                  <div style={{ marginBottom: "16px" }}>
                    <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "10px" }}>
                      Top Recommendations
                    </h3>
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                        <thead>
                          <tr>
                            {["Product", "Store", "Urgency", "Recommended units", "Est. order cost"].map((h) => (
                              <th
                                key={h}
                                style={{
                                  textAlign: "left",
                                  padding: "6px 10px",
                                  borderBottom: "2px solid var(--border)",
                                  color: "var(--text-secondary)",
                                  fontSize: "11px",
                                  fontWeight: 600,
                                }}
                              >
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {impact.top_recommendations.map((r, i) => (
                            <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                              <td style={{ padding: "7px 10px" }}>
                                {r.product_name ?? r.product_id.slice(0, 8)}
                              </td>
                              <td style={{ padding: "7px 10px", color: "var(--text-secondary)" }}>
                                {r.store_id.slice(0, 8)}
                              </td>
                              <td style={{ padding: "7px 10px" }}>
                                <span
                                  style={{
                                    color: TIER_COLORS[r.urgency] ?? "#6b7280",
                                    fontWeight: 600,
                                    textTransform: "capitalize",
                                  }}
                                >
                                  {r.urgency}
                                </span>
                              </td>
                              <td style={{ padding: "7px 10px" }}>
                                {r.recommended_units != null ? fmt(r.recommended_units) : "—"}
                              </td>
                              <td style={{ padding: "7px 10px" }}>
                                {r.estimated_order_cost != null
                                  ? `€${fmt(r.estimated_order_cost)}`
                                  : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div style={{ marginTop: "6px", textAlign: "right" }}>
                      <Link href="/recommendations" style={{ fontSize: "12px" }}>
                        View all recommendations →
                      </Link>
                    </div>
                  </div>
                )}
              </>
            )}
          </SectionCard>

          {/* 7. Limitations and interpretation */}
          <SectionCard
            title="Limitations & Interpretation"
            subtitle="What this system is and is not."
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                gap: "12px",
              }}
            >
              {[
                {
                  title: "Synthetic data",
                  body: "All records are generated from a synthetic commerce simulator. Results reflect simulated demand patterns, not real retail operations.",
                },
                {
                  title: "Prototype forecaster",
                  body: "The ML model is a HistGradientBoosting regressor trained on a small synthetic dataset. Forecasts are evaluated but not production-calibrated.",
                },
                {
                  title: "No automated purchasing",
                  body: "Reorder recommendations are internal review guidance only. No purchase order is created. All actions require explicit human approval.",
                },
                {
                  title: "Feature association, not causation",
                  body: "Feature signals describe which inputs are used by the model. They indicate statistical association, not causal relationships.",
                },
                {
                  title: "WAPE context",
                  body: "WAPE below 30% is strong for a demo; 30–60% is a usable directional signal; above 60% means treat with caution. These thresholds are for synthetic-data evaluation.",
                },
                {
                  title: "Portfolio demonstration",
                  body: "DemandOS demonstrates a deterministic ML pipeline architecture. It is a public portfolio prototype, not a production system.",
                },
              ].map((item) => (
                <div
                  key={item.title}
                  style={{
                    background: "var(--border)",
                    borderRadius: "6px",
                    padding: "14px",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: "13px", marginBottom: "6px" }}>
                    {item.title}
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                    {item.body}
                  </p>
                </div>
              ))}
            </div>
          </SectionCard>

          {/* Automation safety note */}
          {impact && (
            <div
              style={{
                background: "#f0f9ff",
                border: "1px solid #bae6fd",
                borderRadius: "8px",
                padding: "14px 18px",
                marginBottom: "24px",
                fontSize: "13px",
                color: "#0c4a6e",
              }}
            >
              <strong>Safety boundary: </strong>
              {impact.automation_note}
            </div>
          )}
        </>
      )}
    </div>
  );
}
