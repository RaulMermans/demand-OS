"use client";

import { useEffect, useState } from "react";
import { getOverview, getDashboardPipelineStatus } from "@/lib/api";
import type { OverviewResponse, DashboardPipelineStatusResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import KpiCard from "@/components/KpiCard";
import ChartCard from "@/components/ChartCard";
import BarChartPanel from "@/components/BarChartPanel";

export default function OverviewPage() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<DashboardPipelineStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getOverview(),
      getDashboardPipelineStatus(),
    ])
      .then(([o, p]) => { setData(o); setPipelineStatus(p); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const fmt = (n: number | null | undefined, decimals = 0) =>
    n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: decimals });

  const s = data?.summary;

  // Risk tier chart data
  const riskChartData = s
    ? [
        { name: "Critical", value: s.critical_stockout_count, color: "#dc2626" },
        { name: "High", value: s.high_stockout_count, color: "#c2410c" },
        { name: "Medium", value: s.medium_stockout_count, color: "#a16207" },
        { name: "Low", value: s.low_stockout_count, color: "#15803d" },
      ].filter((d) => d.value > 0)
    : [];

  // Recommendation urgency chart data
  const recChartData = s
    ? [
        { name: "Critical", value: s.critical_recommendation_count, color: "#dc2626" },
        { name: "High", value: s.high_recommendation_count, color: "#c2410c" },
        { name: "Open", value: s.open_recommendation_count, color: "#1d4ed8" },
      ].filter((d) => d.value > 0)
    : [];

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
          message="Go to Pipeline Controls to seed the demo dataset and run the pipeline."
        />
      )}

      {s && data?.status !== "no_data" && (
        <>
          {/* Raw data KPIs */}
          <section style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Raw Data
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px" }}>
              {[
                { label: "Products", value: fmt(s.products) },
                { label: "Stores", value: fmt(s.stores) },
                { label: "Orders", value: fmt(s.orders) },
                { label: "Feature rows", value: fmt(s.feature_rows_count) },
                { label: "Forecast rows", value: fmt(s.forecast_rows_count) },
              ].map((m) => (
                <KpiCard key={m.label} label={m.label} value={m.value} />
              ))}
            </div>
          </section>

          {/* Risk + recommendations charts */}
          {(riskChartData.length > 0 || recChartData.length > 0) && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "24px" }}>
              <ChartCard title="Risk Tier Summary" subtitle="Latest completed risk run">
                <BarChartPanel
                  data={riskChartData}
                  height={160}
                  emptyMessage="No risk data."
                  valueFormatter={(v) => String(v)}
                />
              </ChartCard>
              <ChartCard title="Recommendation Summary" subtitle="Open + urgency breakdown">
                <BarChartPanel
                  data={recChartData}
                  height={160}
                  emptyMessage="No recommendations."
                  valueFormatter={(v) => String(v)}
                />
              </ChartCard>
            </div>
          )}

          {/* Risk + recommendation metric cards */}
          <section style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Risk &amp; Recommendations
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
              {[
                { label: "Critical risks", value: fmt(s.critical_stockout_count), color: "#dc2626" },
                { label: "High risks", value: fmt(s.high_stockout_count), color: "#c2410c" },
                { label: "Est. lost sales", value: s.estimated_lost_sales_value != null ? `€${fmt(s.estimated_lost_sales_value, 0)}` : "—" },
                { label: "Open recommendations", value: fmt(s.open_recommendation_count) },
                { label: "Est. order cost", value: s.estimated_order_cost > 0 ? `€${fmt(s.estimated_order_cost, 0)}` : "—" },
                { label: "Est. lost sales avoided", value: s.estimated_lost_sales_avoided > 0 ? `€${fmt(s.estimated_lost_sales_avoided, 0)}` : "—" },
              ].map((m) => (
                <KpiCard key={m.label} label={m.label} value={m.value} color={m.color} />
              ))}
            </div>
          </section>

          {/* Forecasting summary */}
          <section style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Forecasting
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              {[
                { label: "Latest baseline model", value: s.latest_baseline_model ?? "None" },
                { label: "Latest baseline WAPE", value: s.latest_baseline_wape != null ? `${(s.latest_baseline_wape * 100).toFixed(1)}%` : "—" },
                { label: "Latest ML algorithm", value: s.latest_ml_model_algorithm ?? "Not trained" },
                { label: "Latest ML WAPE", value: s.latest_ml_wape != null ? `${(s.latest_ml_wape * 100).toFixed(1)}%` : "—" },
                { label: "ML artifact exists", value: s.model_artifact_exists ? "Yes" : "No" },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <span style={{ fontWeight: 500 }}>{row.value}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Pipeline run statuses */}
          <section style={{ marginBottom: "24px" }}>
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

          {/* Pipeline readiness from Sprint 9 status endpoint */}
          {pipelineStatus && (
            <section>
              <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                Pipeline Stage Readiness
              </h2>
              <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
                {pipelineStatus.steps.map((step, i, arr) => (
                  <div key={step.step} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{step.label}</span>
                    <StatusBadge value={step.status} />
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
