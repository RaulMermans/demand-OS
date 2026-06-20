"use client";

import { useEffect, useState } from "react";
import { getDashboardRiskSummary, getRisks } from "@/lib/api";
import type { DashboardRiskSummaryResponse, RisksListResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import DataTable from "@/components/DataTable";

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

  return (
    <div>
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "4px" }}>Inventory Risk</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Stockout risk scores from the latest completed risk run
      </p>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={() => load()} />}

      {!loading && !error && summary && !summary.has_risk_run && (
        <EmptyState
          title="No risk run has been generated yet."
          message="Run POST /api/risks/run to compute stockout risk scores."
        />
      )}

      {summary?.has_risk_run && (
        <>
          {/* Risk tier counts */}
          <section style={{ marginBottom: "32px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "12px" }}>
              {[
                { label: "Critical", value: summary.tier_counts.critical, color: "#dc2626" },
                { label: "High", value: summary.tier_counts.high, color: "#c2410c" },
                { label: "Medium", value: summary.tier_counts.medium, color: "#a16207" },
                { label: "Low", value: summary.tier_counts.low, color: "#15803d" },
                { label: "Unknown", value: summary.tier_counts.unknown, color: "var(--text-secondary)" },
              ].map((t) => (
                <div
                  key={t.label}
                  style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px", textAlign: "center", cursor: "pointer" }}
                  onClick={() => { const next = t.label.toLowerCase(); const newFilter = next === tierFilter ? "" : next; setTierFilter(newFilter); load(newFilter); }}
                >
                  <div style={{ fontSize: "28px", fontWeight: 700, color: t.color }}>{t.value}</div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>{t.label}</div>
                </div>
              ))}
            </div>

            {summary.estimated_lost_sales_value != null && (
              <div style={{ marginTop: "16px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "16px", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>Estimated total lost sales value</span>
                <span style={{ fontWeight: 700, fontSize: "16px" }}>€{fmt(summary.estimated_lost_sales_value, 0)}</span>
              </div>
            )}
          </section>

          {/* Run info */}
          {summary.latest_run && (
            <div style={{ marginBottom: "24px", fontSize: "12px", color: "var(--text-secondary)" }}>
              Run {String(summary.latest_run.run_id ?? "").slice(0, 16)}… · as of {String(summary.latest_run.as_of_date ?? "")} · {String(summary.latest_run.risk_horizon_days ?? "?")}-day horizon
            </div>
          )}

          {/* Filter */}
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
                { key: "product_id", header: "Product ID", render: (r) => <span style={{ fontFamily: "monospace", fontSize: "11px" }}>{String(r.product_id).slice(0, 12)}…</span> },
                { key: "store_id", header: "Store", render: (r) => <span style={{ fontFamily: "monospace", fontSize: "11px" }}>{String(r.store_id).slice(0, 10)}…</span> },
                { key: "category", header: "Category" },
                { key: "risk_tier", header: "Tier", render: (r) => <StatusBadge value={r.risk_tier as string} /> },
                { key: "risk_score", header: "Score", align: "right", render: (r) => r.risk_score != null ? (r.risk_score as number).toFixed(0) : "—" },
                { key: "days_until_stockout", header: "Days until SO", align: "right", render: (r) => r.days_until_stockout != null ? (r.days_until_stockout as number).toFixed(0) : "—" },
                { key: "current_available_units", header: "Available", align: "right", render: (r) => r.current_available_units != null ? (r.current_available_units as number).toFixed(0) : "—" },
                { key: "lost_sales_value_estimate", header: "Est. lost sales", align: "right", render: (r) => r.lost_sales_value_estimate != null ? `€${(r.lost_sales_value_estimate as number).toFixed(0)}` : "—" },
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
