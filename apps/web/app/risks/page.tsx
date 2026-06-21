"use client";

import { useEffect, useState } from "react";
import { getDashboardRiskSummary, getRisks } from "@/lib/api";
import type { DashboardRiskSummaryResponse, RisksListResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import DataTable from "@/components/DataTable";
import ChartCard from "@/components/ChartCard";
import BarChartPanel from "@/components/BarChartPanel";
import KpiCard from "@/components/KpiCard";
import PageHeader from "@/components/PageHeader";

const TIER_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#c2410c",
  medium: "#a16207",
  low: "#15803d",
  unknown: "#6b7280",
};

const TIER_FILTER_OPTIONS = ["", "critical", "high", "medium", "low"];

export default function RisksPage() {
  const [summary, setSummary] = useState<DashboardRiskSummaryResponse | null>(null);
  const [risks, setRisks] = useState<RisksListResponse | null>(null);
  const [tierFilter, setTierFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = (tier = tierFilter) => {
    setLoading(true);
    setError(null);
    Promise.all([
      getDashboardRiskSummary(),
      getRisks({ risk_tier: tier || undefined, limit: 100 }),
    ])
      .then(([s, r]) => { setSummary(s); setRisks(r); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const fmt = (n: number | null | undefined, decimals = 0) =>
    n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: decimals });

  const tierChartData = summary?.tier_counts
    ? ["critical", "high", "medium", "low", "unknown"].map((t) => ({
        name: t.charAt(0).toUpperCase() + t.slice(1),
        value: summary.tier_counts[t] ?? 0,
        color: TIER_COLORS[t],
      }))
    : [];

  return (
    <div>
      <PageHeader
        title="Inventory risk"
        subtitle="Prioritize product and store combinations using projected demand, inventory coverage, and supplier lead times."
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={() => load()} />}

      {!loading && !error && summary && !summary.has_risk_run && (
        <EmptyState
          title="No risk run has been generated yet."
          message="Go to Pipeline Controls and click Run Stockout Risk, or run POST /api/risks/run."
        />
      )}

      {summary?.has_risk_run && (
        <>
          {/* KPI tier cards */}
          <section style={{ marginBottom: "24px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: "12px" }}>
              {(["critical", "high", "medium", "low", "unknown"] as const).map((t) => (
                <KpiCard
                  key={t}
                  label={t.charAt(0).toUpperCase() + t.slice(1)}
                  value={summary.tier_counts[t] ?? 0}
                  color={TIER_COLORS[t]}
                  onClick={() => {
                    const newFilter = t === tierFilter ? "" : t;
                    setTierFilter(newFilter);
                    load(newFilter);
                  }}
                />
              ))}
            </div>
            {summary.estimated_lost_sales_value != null && (
              <div style={{ marginTop: "12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>Estimated total lost sales value</span>
                <span style={{ fontWeight: 700, fontSize: "16px" }}>€{fmt(summary.estimated_lost_sales_value, 0)}</span>
              </div>
            )}
          </section>

          {/* Risk tier distribution chart */}
          <ChartCard
            title="Risk Tier Distribution"
            subtitle="Number of product/store combinations per risk tier (latest run)"
          >
            <BarChartPanel
              data={tierChartData.filter((d) => d.value > 0)}
              height={180}
              emptyMessage="No risk data to display."
              valueFormatter={(v) => String(v)}
            />
          </ChartCard>

          {/* Run info */}
          {summary.latest_run && (
            <div style={{ marginBottom: "16px", fontSize: "12px", color: "var(--text-secondary)" }}>
              Run {String(summary.latest_run.run_id ?? "").slice(0, 16)}… · as of{" "}
              {String(summary.latest_run.as_of_date ?? "")} · {String(summary.latest_run.risk_horizon_days ?? "?")}-day horizon
            </div>
          )}

          {/* Filter bar */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "16px", alignItems: "center" }}>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Filter tier:</span>
            {TIER_FILTER_OPTIONS.map((opt) => (
              <button
                key={opt || "all"}
                onClick={() => { setTierFilter(opt); load(opt); }}
                style={{
                  padding: "4px 12px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  cursor: "pointer",
                  border: tierFilter === opt ? "1px solid var(--accent)" : "1px solid var(--border)",
                  background: tierFilter === opt ? "var(--accent)" : "var(--surface)",
                  color: tierFilter === opt ? "#fff" : "var(--text-primary)",
                }}
              >
                {opt || "All"}
              </button>
            ))}
          </div>

          {/* Risks table */}
          {risks && (
            <DataTable
              columns={[
                {
                  key: "product_id",
                  header: "Product ID",
                  render: (r) => (
                    <span style={{ fontFamily: "monospace", fontSize: "11px" }}>
                      {String(r.product_id).slice(0, 12)}…
                    </span>
                  ),
                },
                {
                  key: "store_id",
                  header: "Store",
                  render: (r) => (
                    <span style={{ fontFamily: "monospace", fontSize: "11px" }}>
                      {String(r.store_id).slice(0, 10)}…
                    </span>
                  ),
                },
                { key: "category", header: "Category" },
                { key: "risk_tier", header: "Tier", render: (r) => <StatusBadge value={r.risk_tier as string} /> },
                {
                  key: "risk_score",
                  header: "Score",
                  align: "right",
                  render: (r) => r.risk_score != null ? (r.risk_score as number).toFixed(0) : "—",
                },
                {
                  key: "days_until_stockout",
                  header: "Days until SO",
                  align: "right",
                  render: (r) => r.days_until_stockout != null ? (r.days_until_stockout as number).toFixed(0) : "—",
                },
                {
                  key: "current_available_units",
                  header: "Available",
                  align: "right",
                  render: (r) => r.current_available_units != null ? (r.current_available_units as number).toFixed(0) : "—",
                },
                {
                  key: "lost_sales_value_estimate",
                  header: "Est. lost sales",
                  align: "right",
                  render: (r) =>
                    r.lost_sales_value_estimate != null
                      ? `€${(r.lost_sales_value_estimate as number).toFixed(0)}`
                      : "—",
                },
              ]}
              rows={risks.rows as unknown as Record<string, unknown>[]}
              emptyMessage="No risks found for the selected filter."
            />
          )}
          {risks && (
            <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--text-secondary)" }}>
              Showing {risks.rows.length} of {risks.total} risks
            </div>
          )}
        </>
      )}
    </div>
  );
}
