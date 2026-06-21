"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDashboardOverview } from "@/lib/api";
import type { DashboardOverviewResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import StatusBadge from "@/components/StatusBadge";
import PageHeader from "@/components/PageHeader";

export default function HomePage() {
  const [data, setData] = useState<DashboardOverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardOverview()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const fmt = (n: number | null | undefined, decimals = 0) =>
    n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: decimals });

  return (
    <div>
      <PageHeader
        title="Inventory decisions, from raw data"
        subtitle="A deterministic demand forecasting and stockout-risk workspace. Every value below is computed from synthetic raw commerce records."
        kicker="Public portfolio prototype"
        badge="Live demo · synthetic dataset"
      />

      {loading && <LoadingState message="Loading dashboard overview..." />}
      {error && <ErrorState message={error} onRetry={() => { setLoading(true); setError(null); getDashboardOverview().then(setData).catch((e) => setError(e.message)).finally(() => setLoading(false)); }} />}

      {data && (
        <>
          {data.status === "no_data" && (
            <div className="scaffold-banner">
              <strong>No data yet.</strong> Run{" "}
              <code>POST /api/demo/reset</code> to seed the demo dataset, then
              run aggregation, features, forecasts, risks, and recommendations.
            </div>
          )}

          {/* Raw counts */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "16px",
              marginBottom: "32px",
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
                  padding: "20px",
                }}
              >
                <div style={{ color: "var(--text-secondary)", fontSize: "12px" }}>{item.label}</div>
                <div style={{ fontSize: "28px", fontWeight: 700, margin: "8px 0" }}>{item.value}</div>
              </div>
            ))}
          </div>

          {/* Pipeline readiness */}
          <div style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>
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
                    padding: "12px 20px",
                    borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none",
                  }}
                >
                  <span style={{ fontSize: "13px" }}>{step.label}</span>
                  <StatusBadge value={step.ready ? "completed" : "warning"} label={step.ready ? "Ready" : "Pending"} />
                </div>
              ))}
            </div>
          </div>

          {/* Risk + Recommendation summary */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "16px",
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
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                  STOCKOUT RISK
                </div>
                <div style={{ display: "flex", gap: "16px" }}>
                  {[
                    { label: "Critical", value: data.risk_summary.critical as number, color: "#dc2626" },
                    { label: "High", value: data.risk_summary.high as number, color: "#c2410c" },
                    { label: "Medium", value: data.risk_summary.medium as number, color: "#a16207" },
                    { label: "Low", value: data.risk_summary.low as number, color: "#15803d" },
                  ].map((tier) => (
                    <div key={tier.label} style={{ textAlign: "center" }}>
                      <div style={{ fontSize: "22px", fontWeight: 700, color: tier.color }}>{tier.value ?? "—"}</div>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{tier.label}</div>
                    </div>
                  ))}
                </div>
                {data.risk_summary.estimated_lost_sales_value != null && (
                  <div style={{ marginTop: "12px", fontSize: "12px", color: "var(--text-secondary)" }}>
                    Est. lost sales: €{fmt(data.risk_summary.estimated_lost_sales_value as number, 0)}
                  </div>
                )}
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
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px" }}>
                  REORDER RECOMMENDATIONS
                </div>
                <div style={{ fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>
                  {fmt(data.recommendation_summary.open_count as number)}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>open recommendations</div>
                {data.recommendation_summary.estimated_order_cost != null && (
                  <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--text-secondary)" }}>
                    Est. order cost: €{fmt(data.recommendation_summary.estimated_order_cost as number, 0)}
                  </div>
                )}
              </div>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
