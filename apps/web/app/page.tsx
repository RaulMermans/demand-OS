"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDashboardOverview, getBusinessImpact, getForecastDiagnostics } from "@/lib/api";
import type {
  DashboardOverviewResponse,
  BusinessImpactResponse,
  ForecastDiagnosticsResponse,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import StatusBadge from "@/components/StatusBadge";
import PageHeader from "@/components/PageHeader";

const QUALITY_COLORS: Record<string, string> = {
  strong: "#15803d",
  directional: "#a16207",
  weak: "#dc2626",
  unknown: "#6b7280",
};

const QUALITY_LABELS: Record<string, string> = {
  strong: "Strong signal",
  directional: "Directional signal",
  weak: "Weak signal — use cautiously",
  unknown: "No model yet",
};

export default function HomePage() {
  const [data, setData] = useState<DashboardOverviewResponse | null>(null);
  const [impact, setImpact] = useState<BusinessImpactResponse | null>(null);
  const [diagnostics, setDiagnostics] = useState<ForecastDiagnosticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getDashboardOverview(),
      getBusinessImpact().catch(() => null),
      getForecastDiagnostics().catch(() => null),
    ])
      .then(([overview, biz, diag]) => {
        setData(overview);
        setImpact(biz);
        setDiagnostics(diag);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const fmt = (n: number | null | undefined, decimals = 0) =>
    n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: decimals });

  const fmtPct = (n: number | null | undefined) =>
    n == null ? "—" : `${(n * 100).toFixed(1)}%`;

  const latestModel = diagnostics?.ml_model ?? diagnostics?.baseline ?? null;
  const qualityLabel = latestModel?.quality_label ?? "unknown";

  return (
    <div>
      <PageHeader
        title="Inventory decisions, from raw data to forecasted risk"
        subtitle="DemandOS turns synthetic raw commerce records into demand forecasts, stockout risk, and internal reorder guidance."
        kicker="Public portfolio prototype"
        badge="Live demo · synthetic dataset"
      />

      {loading && <LoadingState message="Loading dashboard..." />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && (
        <>
          {data?.status === "no_data" && (
            <div className="scaffold-banner">
              <strong>No data yet.</strong> Run{" "}
              <code>POST /api/demo/reset</code> to seed the demo dataset, then
              run aggregation, features, forecasts, risks, and recommendations.
            </div>
          )}

          {/* How to read this dashboard */}
          <div
            style={{
              background: "#f0f9ff",
              border: "1px solid #bae6fd",
              borderRadius: "8px",
              padding: "20px 24px",
              marginBottom: "24px",
            }}
          >
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "#0c4a6e", marginBottom: "10px" }}>
              How to read this dashboard
            </h2>
            <ol style={{ margin: 0, paddingLeft: "20px" }}>
              {[
                "Raw commerce records (orders, inventory, products) are seeded into the database.",
                "The pipeline builds daily demand aggregates and leakage-safe ML features.",
                "Forecasting models estimate near-term demand using 30+ signals.",
                "Stockout risk scoring identifies product/store combinations likely to run out.",
                "Reorder recommendations are internal review guidance — no purchase order is created automatically.",
              ].map((line, i) => (
                <li
                  key={i}
                  style={{ fontSize: "13px", color: "#0c4a6e", marginBottom: "5px", lineHeight: 1.5 }}
                >
                  {line}
                </li>
              ))}
            </ol>
            <div style={{ marginTop: "10px" }}>
              <Link href="/data-science" style={{ fontSize: "12px", color: "#0369a1" }}>
                View ML Insights for the full data science breakdown →
              </Link>
            </div>
          </div>

          {/* What to review first */}
          {impact?.has_data && (
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #86efac",
                borderRadius: "8px",
                padding: "20px 24px",
                marginBottom: "24px",
              }}
            >
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "#166534", marginBottom: "10px" }}>
                What to review first
              </h2>
              <ul style={{ margin: 0, paddingLeft: "20px" }}>
                {impact.review_guidance.map((line, i) => (
                  <li
                    key={i}
                    style={{ fontSize: "13px", color: "#166534", marginBottom: "5px", lineHeight: 1.5 }}
                  >
                    {line}
                  </li>
                ))}
              </ul>
              <div style={{ marginTop: "10px", display: "flex", gap: "16px", flexWrap: "wrap" }}>
                <Link href="/risks" style={{ fontSize: "12px", color: "#166534" }}>
                  View inventory risks →
                </Link>
                <Link href="/recommendations" style={{ fontSize: "12px", color: "#166534" }}>
                  View reorder recommendations →
                </Link>
              </div>
            </div>
          )}

          {/* Model confidence */}
          {latestModel && (
            <div
              style={{
                background: "var(--surface)",
                border: `1px solid ${QUALITY_COLORS[qualityLabel] ?? "var(--border)"}44`,
                borderRadius: "8px",
                padding: "18px 24px",
                marginBottom: "24px",
              }}
            >
              <h2 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "6px" }}>
                Model confidence
              </h2>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                <span
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    fontSize: "12px",
                    fontWeight: 600,
                    background: `${QUALITY_COLORS[qualityLabel]}22`,
                    color: QUALITY_COLORS[qualityLabel] ?? "#6b7280",
                    border: `1px solid ${QUALITY_COLORS[qualityLabel]}44`,
                  }}
                >
                  {QUALITY_LABELS[qualityLabel]}
                </span>
                <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                  {latestModel.model_name} · WAPE {fmtPct(latestModel.wape)}
                </span>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "0 0 8px" }}>
                {latestModel.interpretation}
              </p>
              {latestModel.warning && (
                <div
                  style={{
                    fontSize: "12px",
                    color: "#92400e",
                    background: "#fef3c7",
                    borderRadius: "4px",
                    padding: "6px 10px",
                    marginBottom: "8px",
                  }}
                >
                  {latestModel.warning}
                </div>
              )}
              <Link href="/data-science" style={{ fontSize: "12px" }}>
                View full ML Insights →
              </Link>
            </div>
          )}

          {/* Raw counts */}
          {data && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                gap: "16px",
                marginBottom: "24px",
              }}
            >
              {[
                { label: "Products", value: fmt(data.raw_counts.products) },
                { label: "Stores", value: fmt(data.raw_counts.stores) },
                { label: "Orders", value: fmt(data.raw_counts.orders) },
                { label: "Inventory snapshots", value: fmt(data.raw_counts.inventory_snapshots) },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    padding: "18px",
                  }}
                >
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{item.label}</div>
                  <div style={{ fontSize: "26px", fontWeight: 700, margin: "6px 0" }}>{item.value}</div>
                </div>
              ))}
            </div>
          )}

          {/* Pipeline readiness */}
          {data && (
            <div style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
                Pipeline Status
              </h2>
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  overflow: "hidden",
                }}
              >
                {[
                  { label: "Data seeded", ready: data.pipeline_readiness.data_seeded },
                  { label: "Aggregation run", ready: data.pipeline_readiness.aggregation_run },
                  { label: "Features built", ready: data.pipeline_readiness.features_built },
                  { label: "Forecast run", ready: data.pipeline_readiness.forecast_run },
                  { label: "Risk run", ready: data.pipeline_readiness.risk_run },
                  { label: "Recommendation run", ready: data.pipeline_readiness.recommendation_run },
                ].map((step, i, arr) => (
                  <div
                    key={step.label}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "11px 18px",
                      borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none",
                    }}
                  >
                    <span style={{ fontSize: "13px" }}>{step.label}</span>
                    <StatusBadge
                      value={step.ready ? "completed" : "warning"}
                      label={step.ready ? "Ready" : "Pending"}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk + Recommendation cards */}
          {data && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                gap: "16px",
                marginBottom: "24px",
              }}
            >
              <Link href="/risks" style={{ textDecoration: "none" }}>
                <div
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    padding: "20px",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "10px" }}>
                    STOCKOUT RISK
                  </div>
                  <div style={{ display: "flex", gap: "14px", flexWrap: "wrap", marginBottom: "10px" }}>
                    {[
                      { label: "Critical", value: data.risk_summary.critical as number, color: "#dc2626" },
                      { label: "High", value: data.risk_summary.high as number, color: "#c2410c" },
                      { label: "Medium", value: data.risk_summary.medium as number, color: "#a16207" },
                      { label: "Low", value: data.risk_summary.low as number, color: "#15803d" },
                    ].map((tier) => (
                      <div key={tier.label} style={{ textAlign: "center" }}>
                        <div style={{ fontSize: "20px", fontWeight: 700, color: tier.color }}>
                          {tier.value ?? "—"}
                        </div>
                        <div style={{ fontSize: "10px", color: "var(--text-secondary)" }}>{tier.label}</div>
                      </div>
                    ))}
                  </div>
                  {data.risk_summary.estimated_lost_sales_value != null && (
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      Est. lost sales: €{fmt(data.risk_summary.estimated_lost_sales_value as number)}
                    </div>
                  )}
                  <div style={{ fontSize: "12px", marginTop: "10px" }}>View risk details →</div>
                </div>
              </Link>

              <Link href="/recommendations" style={{ textDecoration: "none" }}>
                <div
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    padding: "20px",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "10px" }}>
                    REORDER RECOMMENDATIONS
                  </div>
                  <div style={{ fontSize: "26px", fontWeight: 700, marginBottom: "6px" }}>
                    {fmt(data.recommendation_summary.open_count as number)}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "10px" }}>
                    open internal review items
                  </div>
                  {data.recommendation_summary.estimated_order_cost != null && (
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      Est. order cost: €{fmt(data.recommendation_summary.estimated_order_cost as number)}
                    </div>
                  )}
                  <div style={{ fontSize: "12px", marginTop: "10px" }}>Review recommendations →</div>
                </div>
              </Link>
            </div>
          )}

          {/* Safety note */}
          <div
            style={{
              fontSize: "12px",
              color: "var(--text-secondary)",
              padding: "12px 16px",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
            }}
          >
            <strong>Safety boundary:</strong> No purchasing is automated. Recommendations are internal
            review guidance only. No external APIs, emails, or purchase orders are triggered.
          </div>
        </>
      )}
    </div>
  );
}
