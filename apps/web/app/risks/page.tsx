"use client";

import { useEffect, useState } from "react";
import { getDashboardRiskSummary, getRisks, getRiskDrivers } from "@/lib/api";
import type { DashboardRiskSummaryResponse, RisksListResponse, RiskDriversResponse } from "@/lib/types";
import RiskDriverList from "@/components/RiskDriverList";
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
  const [drivers, setDrivers] = useState<RiskDriversResponse | null>(null);
  const [tierFilter, setTierFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = (tier = tierFilter) => {
    setLoading(true);
    setError(null);
    Promise.all([
      getDashboardRiskSummary(),
      getRisks({ risk_tier: tier || undefined, limit: 100 }),
      getRiskDrivers(8).catch(() => null),
    ])
      .then(([s, r, d]) => { setSummary(s); setRisks(r); setDrivers(d); })
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

  const criticalCount = summary?.tier_counts?.critical ?? 0;
  const highCount = summary?.tier_counts?.high ?? 0;

  return (
    <div>
      <PageHeader
        title="Risk Board"
        subtitle="Find the SKU-store combinations most likely to stock out."
        kicker="Risk scoring"
        badge="Planning guidance · not automated"
      />
      <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "20px", marginTop: "-4px" }}>
        Risk scores are planning guidance, not automated purchasing decisions.
      </p>

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
          {/* What this page means */}
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
              How risk scores are computed · triage guidance
            </h2>
            <ul style={{ margin: 0, paddingLeft: "18px" }}>
              <li style={{ fontSize: "13px", color: "#0c4a6e", marginBottom: "4px", lineHeight: 1.5 }}>
                The demand forecast pipeline estimates daily expected demand for each product/store.
              </li>
              <li style={{ fontSize: "13px", color: "#0c4a6e", marginBottom: "4px", lineHeight: 1.5 }}>
                Risk scoring compares available inventory + incoming POs against forecasted demand over the planning horizon.
              </li>
              <li style={{ fontSize: "13px", color: "#0c4a6e", marginBottom: "4px", lineHeight: 1.5 }}>
                Combinations likely to exhaust stock before the next replenishment are scored as critical or high.
              </li>
              <li style={{ fontSize: "13px", color: "#0c4a6e", lineHeight: 1.5 }}>
                Risk scores are planning guidance only. They do not trigger automatic reorders or supplier actions.
              </li>
            </ul>
          </div>

          {/* Prioritize these first */}
          {(criticalCount > 0 || highCount > 0) && (
            <div
              style={{
                background: criticalCount > 0 ? "#fef2f2" : "#fff7ed",
                border: `1px solid ${criticalCount > 0 ? "#fecaca" : "#fed7aa"}`,
                borderRadius: "8px",
                padding: "16px 20px",
                marginBottom: "24px",
              }}
            >
              <h2
                style={{
                  fontSize: "13px",
                  fontWeight: 600,
                  color: criticalCount > 0 ? "#991b1b" : "#92400e",
                  marginBottom: "8px",
                }}
              >
                Prioritize these first
              </h2>
              <ul style={{ margin: 0, paddingLeft: "18px" }}>
                {criticalCount > 0 && (
                  <li
                    style={{
                      fontSize: "13px",
                      color: "#991b1b",
                      marginBottom: "4px",
                      lineHeight: 1.5,
                    }}
                  >
                    <strong>{criticalCount} critical risk{criticalCount > 1 ? "s" : ""}:</strong> These product/store combinations
                    are likely to stock out within the planning horizon. Review immediately.
                  </li>
                )}
                {highCount > 0 && (
                  <li style={{ fontSize: "13px", color: "#92400e", lineHeight: 1.5 }}>
                    <strong>{highCount} high risk{highCount > 1 ? "s" : ""}:</strong> Elevated stockout probability. Review after
                    resolving critical items.
                  </li>
                )}
              </ul>
              <div style={{ marginTop: "8px" }}>
                <button
                  onClick={() => { setTierFilter("critical"); load("critical"); }}
                  style={{
                    padding: "4px 12px",
                    borderRadius: "4px",
                    fontSize: "11px",
                    cursor: "pointer",
                    border: "1px solid #fecaca",
                    background: "#fee2e2",
                    color: "#991b1b",
                    marginRight: "8px",
                  }}
                >
                  Show critical only
                </button>
                <Link href="/recommendations" style={{ fontSize: "12px" }}>
                  View Reorder Queue →
                </Link>
              </div>
            </div>
          )}

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
              <div
                style={{
                  marginTop: "12px",
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "14px 18px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "12px" }}>
                    Estimated total lost sales exposure
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                    Sum of per-item estimates across all risk tiers · planning guidance only
                  </div>
                </div>
                <span style={{ fontWeight: 700, fontSize: "18px" }}>
                  €{fmt(summary.estimated_lost_sales_value, 0)}
                </span>
              </div>
            )}
          </section>

          {/* Risk tier chart */}
          <ChartCard
            title="Risk Tier Distribution"
            subtitle="Number of product/store combinations per risk tier (latest run)"
          >
            <BarChartPanel
              data={tierChartData.filter((d) => d.value > 0)}
              height={160}
              emptyMessage="No risk data to display."
              valueFormatter={(v) => String(v)}
            />
          </ChartCard>

          {/* Risk driver panel */}
          {drivers && drivers.drivers.length > 0 && (
            <section style={{ marginBottom: "24px" }}>
              <h2 style={{ fontSize: "15px", fontWeight: 700, marginBottom: "12px" }}>
                Risk drivers — top exposures
              </h2>
              <RiskDriverList drivers={drivers.drivers} disclaimer={drivers.disclaimer} />
            </section>
          )}

          {/* Run info */}
          {summary.latest_run && (
            <div style={{ marginBottom: "12px", fontSize: "12px", color: "var(--text-secondary)" }}>
              Risk run as of {String(summary.latest_run.as_of_date ?? "")} ·{" "}
              {String(summary.latest_run.risk_horizon_days ?? "?")} day planning horizon ·{" "}
              {String(summary.latest_run.rows_created ?? "?")} risk rows computed
            </div>
          )}

          {/* Filter bar */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "14px", alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Filter by tier:</span>
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
            <>
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
                  {
                    key: "risk_tier",
                    header: "Risk tier",
                    render: (r) => <StatusBadge value={r.risk_tier as string} />,
                  },
                  {
                    key: "days_until_stockout",
                    header: "Days to SO",
                    align: "right",
                    render: (r) =>
                      r.days_until_stockout != null
                        ? (r.days_until_stockout as number).toFixed(0)
                        : "—",
                  },
                  {
                    key: "current_available_units",
                    header: "Available units",
                    align: "right",
                    render: (r) =>
                      r.current_available_units != null
                        ? (r.current_available_units as number).toFixed(0)
                        : "—",
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
              <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--text-secondary)" }}>
                Showing {risks.rows.length} of {risks.total} risk rows
              </div>
            </>
          )}

          {/* Safety note */}
          <div
            style={{
              marginTop: "24px",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "12px 16px",
              fontSize: "12px",
              color: "var(--text-secondary)",
            }}
          >
            <strong>Planning guidance only.</strong> Risk scores are internal estimates based on forecast
            demand and current inventory. They do not trigger automatic reorders. Review high-risk items
            and use the{" "}
            <Link href="/recommendations">Reorder Queue</Link>{" "}
            page to review suggested reorder quantities.
          </div>
        </>
      )}
    </div>
  );
}
