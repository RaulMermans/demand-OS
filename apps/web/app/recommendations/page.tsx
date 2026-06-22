"use client";

import { useEffect, useState } from "react";
import {
  getDashboardRecommendationSummary,
  getRecommendations,
  updateRecommendationStatus,
} from "@/lib/api";
import type {
  DashboardRecommendationSummaryResponse,
  RecommendationsListResponse,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import DataTable from "@/components/DataTable";
import ChartCard from "@/components/ChartCard";
import BarChartPanel from "@/components/BarChartPanel";
import PageHeader from "@/components/PageHeader";

const URGENCY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#c2410c",
  medium: "#a16207",
  low: "#15803d",
};

const URGENCY_OPTS = ["", "critical", "high", "medium", "low"];
const STATUS_OPTS = ["", "open", "reviewed", "approved_internal", "ignored", "resolved"];

export default function RecommendationsPage() {
  const [summary, setSummary] = useState<DashboardRecommendationSummaryResponse | null>(null);
  const [recs, setRecs] = useState<RecommendationsListResponse | null>(null);
  const [urgencyFilter, setUrgencyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);

  const load = (urgency = urgencyFilter, status = statusFilter) => {
    setLoading(true);
    setError(null);
    Promise.all([
      getDashboardRecommendationSummary(),
      getRecommendations({ urgency: urgency || undefined, status: status || undefined, limit: 100 }),
    ])
      .then(([s, r]) => { setSummary(s); setRecs(r); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const fmt = (n: number | null | undefined, decimals = 0) =>
    n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: decimals });

  const handleStatusUpdate = async (id: string, newStatus: string) => {
    setUpdating(id);
    try {
      await updateRecommendationStatus(id, { status: newStatus });
      await load();
    } catch (e) {
      alert(`Failed to update: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setUpdating(null);
    }
  };

  const urgencyChartData = summary?.urgency_counts
    ? Object.entries(summary.urgency_counts)
        .map(([k, v]) => ({
          name: k.charAt(0).toUpperCase() + k.slice(1),
          value: v,
          color: URGENCY_COLORS[k] ?? "#6b7280",
        }))
        .filter((d) => d.value > 0)
    : [];

  return (
    <div>
      <PageHeader
        title="Reorder Recommendations"
        subtitle="Internal review guidance for reorder quantities. Status changes are recorded inside DemandOS only."
        kicker="Decision support"
        badge="Internal approval only · no purchasing"
      />

      {/* Why this exists */}
      <div
        style={{
          background: "#f0f9ff",
          border: "1px solid #bae6fd",
          borderRadius: "8px",
          padding: "16px 20px",
          marginBottom: "20px",
        }}
      >
        <h2 style={{ fontSize: "13px", fontWeight: 600, color: "#0c4a6e", marginBottom: "8px" }}>
          Why these recommendations exist
        </h2>
        <ul style={{ margin: 0, paddingLeft: "18px" }}>
          <li style={{ fontSize: "13px", color: "#0c4a6e", marginBottom: "4px", lineHeight: 1.5 }}>
            Each recommendation is triggered by a stockout risk score above a threshold for a product/store combination.
          </li>
          <li style={{ fontSize: "13px", color: "#0c4a6e", marginBottom: "4px", lineHeight: 1.5 }}>
            Recommended units are calculated from forecasted demand gap, current inventory, and supplier lead time.
          </li>
          <li style={{ fontSize: "13px", color: "#0c4a6e", lineHeight: 1.5 }}>
            Estimated order cost uses the product's unit cost. Lost sales avoided estimates the revenue impact of acting on the recommendation.
          </li>
        </ul>
      </div>

      {/* Safety boundary — prominent */}
      <div
        style={{
          background: "#fffbeb",
          border: "1px solid #fde68a",
          borderRadius: "8px",
          padding: "12px 18px",
          marginBottom: "20px",
          fontSize: "13px",
          color: "#78350f",
        }}
      >
        <strong>No purchase order is created.</strong> Approving a recommendation changes its internal
        review status inside DemandOS only. No supplier is contacted. No external API is called.
        Reorder actions require explicit human approval outside this system.
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={() => load()} />}

      {!loading && !error && summary && !summary.has_recommendation_run && (
        <EmptyState
          title="No recommendation run has been generated yet."
          message="Go to Pipeline Controls and run the Recommendations step, or run POST /api/recommendations/run."
        />
      )}

      {summary?.has_recommendation_run && (
        <>
          {/* Summary KPI cards */}
          <section style={{ marginBottom: "24px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
                gap: "12px",
              }}
            >
              {[
                { label: "Open", value: fmt(summary.open_count) },
                { label: "Critical", value: fmt(summary.urgency_counts.critical), color: "#dc2626" },
                { label: "High", value: fmt(summary.urgency_counts.high), color: "#c2410c" },
                { label: "Medium", value: fmt(summary.urgency_counts.medium), color: "#a16207" },
                { label: "Low", value: fmt(summary.urgency_counts.low), color: "#15803d" },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    padding: "14px",
                    textAlign: "center",
                  }}
                >
                  <div
                    style={{
                      fontSize: "24px",
                      fontWeight: 700,
                      color: m.color ?? "var(--text-primary)",
                    }}
                  >
                    {m.value}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "3px" }}>
                    {m.label}
                  </div>
                </div>
              ))}
            </div>
            {summary.total_estimated_order_cost != null && (
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
                  <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                    Total estimated order cost (all recommendations)
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                    Based on unit cost × recommended units · internal estimate only
                  </div>
                </div>
                <span style={{ fontWeight: 700, fontSize: "18px" }}>
                  €{fmt(summary.total_estimated_order_cost, 0)}
                </span>
              </div>
            )}
          </section>

          {/* Urgency distribution */}
          {urgencyChartData.length > 0 && (
            <ChartCard
              title="Recommendation Urgency Distribution"
              subtitle="Count by urgency level (latest run). Critical and high urgency items should be reviewed first."
            >
              <BarChartPanel
                data={urgencyChartData}
                height={140}
                emptyMessage="No urgency data."
                valueFormatter={(v) => String(v)}
              />
            </ChartCard>
          )}

          {/* Review status explanation */}
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "16px 20px",
              marginBottom: "16px",
            }}
          >
            <h2 style={{ fontSize: "13px", fontWeight: 600, marginBottom: "8px" }}>
              Review status guide
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                gap: "8px",
                fontSize: "12px",
              }}
            >
              {[
                { status: "open", desc: "Newly generated, not yet reviewed" },
                { status: "reviewed", desc: "Seen by an operator, no action taken yet" },
                { status: "approved_internal", desc: "Approved for internal planning — no PO created" },
                { status: "ignored", desc: "Acknowledged and deprioritised" },
                { status: "resolved", desc: "Addressed outside this system" },
              ].map((item) => (
                <div
                  key={item.status}
                  style={{ background: "var(--border)", borderRadius: "4px", padding: "8px" }}
                >
                  <div style={{ fontWeight: 600 }}>{item.status}</div>
                  <div style={{ color: "var(--text-secondary)", marginTop: "2px", lineHeight: 1.4 }}>
                    {item.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Filters */}
          <div
            style={{
              display: "flex",
              gap: "16px",
              marginBottom: "14px",
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Urgency:</span>
              {URGENCY_OPTS.map((opt) => (
                <button
                  key={opt || "all"}
                  onClick={() => { setUrgencyFilter(opt); load(opt, statusFilter); }}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    fontSize: "11px",
                    cursor: "pointer",
                    border: urgencyFilter === opt ? "1px solid var(--accent)" : "1px solid var(--border)",
                    background: urgencyFilter === opt ? "var(--accent)" : "var(--surface)",
                    color: urgencyFilter === opt ? "#fff" : "var(--text-primary)",
                  }}
                >
                  {opt || "All"}
                </button>
              ))}
            </div>
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Status:</span>
              {STATUS_OPTS.map((opt) => (
                <button
                  key={opt || "all"}
                  onClick={() => { setStatusFilter(opt); load(urgencyFilter, opt); }}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    fontSize: "11px",
                    cursor: "pointer",
                    border: statusFilter === opt ? "1px solid var(--accent)" : "1px solid var(--border)",
                    background: statusFilter === opt ? "var(--accent)" : "var(--surface)",
                    color: statusFilter === opt ? "#fff" : "var(--text-primary)",
                  }}
                >
                  {opt || "All"}
                </button>
              ))}
            </div>
          </div>

          {/* Table */}
          {recs && (
            <>
              <DataTable
                columns={[
                  {
                    key: "product_id",
                    header: "Product",
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
                    key: "urgency",
                    header: "Urgency",
                    render: (r) => <StatusBadge value={r.urgency as string} />,
                  },
                  {
                    key: "risk_tier",
                    header: "Risk tier",
                    render: (r) => <StatusBadge value={r.risk_tier as string} />,
                  },
                  {
                    key: "recommended_units_rounded",
                    header: "Rec. units",
                    align: "right",
                    render: (r) =>
                      r.recommended_units_rounded != null
                        ? String((r.recommended_units_rounded as number).toFixed(0))
                        : "—",
                  },
                  {
                    key: "estimated_order_cost",
                    header: "Est. order cost",
                    align: "right",
                    render: (r) =>
                      r.estimated_order_cost != null
                        ? `€${(r.estimated_order_cost as number).toFixed(0)}`
                        : "—",
                  },
                  {
                    key: "estimated_lost_sales_avoided",
                    header: "Lost sales avoided",
                    align: "right",
                    render: (r) =>
                      r.estimated_lost_sales_avoided != null
                        ? `€${(r.estimated_lost_sales_avoided as number).toFixed(0)}`
                        : "—",
                  },
                  {
                    key: "status",
                    header: "Review status",
                    render: (r) => (
                      <select
                        value={r.status as string}
                        disabled={updating === (r.id as string)}
                        onChange={(e) => handleStatusUpdate(r.id as string, e.target.value)}
                        style={{
                          fontSize: "11px",
                          background: "var(--surface-2)",
                          color: "var(--text-primary)",
                          border: "1px solid var(--border)",
                          borderRadius: "4px",
                          padding: "2px 6px",
                          cursor: "pointer",
                        }}
                      >
                        {["open", "reviewed", "approved_internal", "ignored", "resolved"].map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    ),
                  },
                ]}
                rows={recs.recommendations as unknown as Record<string, unknown>[]}
                emptyMessage="No recommendations found for the selected filters."
              />
              <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--text-secondary)" }}>
                Showing {recs.returned} of {recs.total} recommendations ·{" "}
                Internal review status only · no external actions triggered
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
