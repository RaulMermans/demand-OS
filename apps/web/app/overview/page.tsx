"use client";

import { useEffect, useState } from "react";
import { getOverview } from "@/lib/api";
import type { OverviewResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";

export default function OverviewPage() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    getOverview()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const fmt = (n: number | null | undefined, decimals = 0) =>
    n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: decimals });

  const s = data?.summary;

  return (
    <div>
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "4px" }}>Overview</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Pipeline status and computed metric totals
      </p>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}

      {data && data.status === "no_data" && (
        <EmptyState
          title="No data ingested yet"
          message="Run POST /api/demo/reset to seed the demo dataset, then run the pipeline stages."
        />
      )}

      {s && data.status !== "no_data" && (
        <>
          {/* Raw counts */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Raw Data
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px" }}>
              {[
                { label: "Products", value: fmt(s.products) },
                { label: "Stores", value: fmt(s.stores) },
                { label: "Orders", value: fmt(s.orders) },
                { label: "Feature rows", value: fmt(s.feature_rows_count) },
              ].map((m) => (
                <div key={m.label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px" }}>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{m.label}</div>
                  <div style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px" }}>{m.value}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Forecasting */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Forecasting
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              {[
                { label: "Latest baseline model", value: s.latest_baseline_model ?? "None" },
                { label: "Latest baseline WAPE", value: s.latest_baseline_wape != null ? `${(s.latest_baseline_wape * 100).toFixed(1)}%` : "—" },
                { label: "Latest ML algorithm", value: s.latest_ml_model_algorithm ?? "Not trained" },
                { label: "Latest ML WAPE", value: s.latest_ml_wape != null ? `${(s.latest_ml_wape * 100).toFixed(1)}%` : "—" },
                { label: "Forecast rows", value: fmt(s.forecast_rows_count) },
                { label: "ML artifact exists", value: s.model_artifact_exists ? "Yes" : "No" },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <span style={{ fontWeight: 500 }}>{row.value}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Risk + recommendations */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Risk &amp; Recommendations
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
              {[
                { label: "Critical risks", value: fmt(s.critical_stockout_count), color: "#dc2626" },
                { label: "High risks", value: fmt(s.high_stockout_count), color: "#c2410c" },
                { label: "Est. lost sales", value: s.estimated_lost_sales_value != null ? `€${fmt(s.estimated_lost_sales_value, 0)}` : "—" },
                { label: "Open recommendations", value: fmt(s.open_recommendation_count) },
                { label: "Est. order cost", value: s.estimated_order_cost > 0 ? `€${fmt(s.estimated_order_cost, 0)}` : "—" },
                { label: "Est. lost sales avoided", value: s.estimated_lost_sales_avoided > 0 ? `€${fmt(s.estimated_lost_sales_avoided, 0)}` : "—" },
              ].map((m) => (
                <div key={m.label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px" }}>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{m.label}</div>
                  <div style={{ fontSize: "22px", fontWeight: 700, marginTop: "4px", color: m.color ?? "var(--text-primary)" }}>{m.value}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Pipeline run statuses */}
          <section>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Latest Run Statuses
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              {[
                { label: "Feature build", value: s.latest_feature_run_status },
                { label: "Forecast run", value: s.latest_forecast_run_status },
                { label: "Risk run", value: s.latest_risk_run_status },
                { label: "Recommendation run", value: s.latest_recommendation_run_status },
                { label: "ML model", value: s.latest_ml_model_status },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <StatusBadge value={row.value ?? "warning"} label={row.value ?? "Not run"} />
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
