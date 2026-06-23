"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getAnalyticsCockpit,
  getInventoryTrend,
  getRiskDrivers,
  getReorderQueue,
} from "@/lib/api";
import type {
  CockpitResponse,
  InventoryTrendResponse,
  RiskDriversResponse,
  ReorderQueueResponse,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import StatusBadge from "@/components/StatusBadge";
import KpiCard from "@/components/KpiCard";
import InventoryTrendChart from "@/components/InventoryTrendChart";
import RiskDistributionChart from "@/components/RiskDistributionChart";
import RiskDriverList from "@/components/RiskDriverList";
import ReorderQueueTable from "@/components/ReorderQueueTable";

const QUALITY_COLORS: Record<string, string> = {
  Strong: "#15803d",
  Directional: "#a16207",
  "Weak / Demo signal": "#dc2626",
  "No model": "#6b7280",
};

const fmt = (n: number | null | undefined, dec = 0) =>
  n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: dec });

const fmtEur = (n: number | null | undefined) =>
  n == null ? "—" : `€${n.toLocaleString("en", { maximumFractionDigits: 0 })}`;

const fmtPct = (n: number | null | undefined) =>
  n == null ? "—" : `${n.toFixed(1)}%`;

function SectionHeader({ title, href, linkLabel }: { title: string; href?: string; linkLabel?: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: "12px",
      }}
    >
      <h2 style={{ fontSize: "15px", fontWeight: 700, margin: 0 }}>{title}</h2>
      {href && (
        <Link href={href} style={{ fontSize: "12px", color: "#2563eb" }}>
          {linkLabel ?? "View all →"}
        </Link>
      )}
    </div>
  );
}

function Panel({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "12px",
        padding: "20px",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export default function HomePage() {
  const [cockpit, setCockpit] = useState<CockpitResponse | null>(null);
  const [trend, setTrend] = useState<InventoryTrendResponse | null>(null);
  const [riskDrivers, setRiskDrivers] = useState<RiskDriversResponse | null>(null);
  const [queue, setQueue] = useState<ReorderQueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getAnalyticsCockpit(),
      getInventoryTrend({ days: 30 }).catch(() => null),
      getRiskDrivers(5).catch(() => null),
      getReorderQueue().catch(() => null),
    ])
      .then(([c, t, d, q]) => {
        setCockpit(c);
        setTrend(t);
        setRiskDrivers(d);
        setQueue(q);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const qualityLabel = cockpit?.forecasting.forecast_quality_label ?? "No model";
  const qualityColor = QUALITY_COLORS[qualityLabel] ?? "#6b7280";
  const noData = cockpit?.status === "no_data";

  return (
    <div>
      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <div style={{ marginBottom: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
          <span
            style={{
              fontSize: "10px",
              fontWeight: 700,
              letterSpacing: "0.07em",
              padding: "3px 10px",
              borderRadius: "100px",
              background: "#dbeafe",
              color: "#1e40af",
              textTransform: "uppercase",
            }}
          >
            Synthetic demo · no external actions
          </span>
        </div>
        <h1 style={{ fontSize: "28px", fontWeight: 750, letterSpacing: "-0.02em", margin: "0 0 8px" }}>
          Inventory intelligence from raw data to reorder guidance
        </h1>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)", margin: 0, maxWidth: "640px" }}>
          DemandOS turns synthetic raw commerce records into demand forecasts, stockout risk scores,
          and internal reorder recommendations — no hardcoded values, no external side effects.
        </p>
      </div>

      {loading && <LoadingState message="Loading analytics cockpit..." />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && (
        <>
          {/* ── No-data banner ─────────────────────────────────────────── */}
          {noData && (
            <div
              style={{
                background: "#fefce8",
                border: "1px solid #fde047",
                borderRadius: "8px",
                padding: "14px 18px",
                marginBottom: "24px",
                fontSize: "13px",
                color: "#713f12",
              }}
            >
              <strong>No pipeline data found.</strong> Run{" "}
              <code style={{ background: "#fef9c3", padding: "1px 4px", borderRadius: "3px" }}>
                POST /api/demo/run-full-pipeline
              </code>{" "}
              from the{" "}
              <Link href="/pipeline" style={{ color: "#92400e" }}>
                Pipeline page
              </Link>{" "}
              to seed the demo dataset end-to-end.
            </div>
          )}

          {/* ── Executive KPI cards ─────────────────────────────────────── */}
          {cockpit && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "12px",
                marginBottom: "24px",
              }}
            >
              <KpiCard
                label="SKUs monitored"
                value={fmt(cockpit.dataset.sku_store_combinations)}
                sub={`${cockpit.dataset.products} products × ${cockpit.dataset.stores} stores`}
              />
              <KpiCard
                label="Stockout risk"
                value={fmtPct(cockpit.inventory.stockout_risk_percent)}
                color={
                  (cockpit.inventory.stockout_risk_percent ?? 0) > 30 ? "#dc2626" :
                  (cockpit.inventory.stockout_risk_percent ?? 0) > 10 ? "#d97706" : "#15803d"
                }
                sub={`${cockpit.inventory.at_risk_sku_stores} at-risk combinations`}
              />
              <KpiCard
                label="Inventory value"
                value={fmtEur(cockpit.inventory.estimated_inventory_value)}
                sub={cockpit.inventory.inventory_value_method}
              />
              <KpiCard
                label="Forecast quality"
                value={qualityLabel}
                color={qualityColor}
                sub={
                  cockpit.forecasting.latest_wape != null
                    ? `WAPE ${(cockpit.forecasting.latest_wape * 100).toFixed(1)}%`
                    : "No model yet"
                }
              />
              <KpiCard
                label="Est. lost sales"
                value={fmtEur(cockpit.risk.estimated_lost_sales)}
                color={cockpit.risk.estimated_lost_sales != null ? "#dc2626" : undefined}
                sub="from at-risk SKU/stores"
              />
              <KpiCard
                label="Open recommendations"
                value={fmt(cockpit.recommendations.open)}
                sub={
                  cockpit.recommendations.estimated_order_cost != null
                    ? `Est. cost ${fmtEur(cockpit.recommendations.estimated_order_cost)}`
                    : "internal review only"
                }
              />
            </div>
          )}

          {/* ── Inventory trend chart ───────────────────────────────────── */}
          <Panel style={{ marginBottom: "24px" }}>
            <SectionHeader title="Inventory trend (last 30 days)" />
            {trend && trend.series.length > 0 ? (
              <>
                <InventoryTrendChart series={trend.series} height={220} />
                {trend.metadata.reorder_point_note && (
                  <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "8px", fontStyle: "italic" }}>
                    {trend.metadata.reorder_point_note}
                  </p>
                )}
              </>
            ) : (
              <InventoryTrendChart series={[]} height={220} />
            )}
          </Panel>

          {/* ── Pipeline status + Risk distribution ─────────────────────── */}
          {cockpit && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
                marginBottom: "24px",
              }}
            >
              {/* Pipeline */}
              <Panel>
                <SectionHeader title="Pipeline status" href="/pipeline" linkLabel="Run pipeline →" />
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {(
                    [
                      { label: "Raw data", key: "data_seeded" },
                      { label: "ML features", key: "features" },
                      { label: "Demand forecasts", key: "forecasts" },
                      { label: "Stockout risks", key: "risks" },
                      { label: "Reorder recommendations", key: "recommendations" },
                    ] as Array<{ label: string; key: keyof typeof cockpit.pipeline }>
                  ).map(({ label, key }) => (
                    <div
                      key={key}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "6px 0",
                        borderBottom: "1px solid var(--border)",
                      }}
                    >
                      <span style={{ fontSize: "12px" }}>{label}</span>
                      <StatusBadge
                        value={cockpit.pipeline[key] === "ready" ? "completed" : "warning"}
                        label={cockpit.pipeline[key] === "ready" ? "Ready" : "Pending"}
                      />
                    </div>
                  ))}
                </div>
              </Panel>

              {/* Risk distribution */}
              <Panel>
                <SectionHeader title="Risk distribution" href="/risks" />
                <RiskDistributionChart
                  critical={cockpit.risk.critical}
                  high={cockpit.risk.high}
                  medium={cockpit.risk.medium}
                  low={cockpit.risk.low}
                />
                {cockpit.risk.estimated_lost_sales != null && (
                  <div
                    style={{
                      marginTop: "14px",
                      padding: "10px 12px",
                      background: "#fef2f2",
                      border: "1px solid #fecaca",
                      borderRadius: "6px",
                      fontSize: "12px",
                      color: "#991b1b",
                    }}
                  >
                    <strong>Est. lost sales exposure:</strong>{" "}
                    {fmtEur(cockpit.risk.estimated_lost_sales)}
                  </div>
                )}
              </Panel>
            </div>
          )}

          {/* ── Risk drivers ────────────────────────────────────────────── */}
          <div style={{ marginBottom: "24px" }}>
            <SectionHeader title="Top risk drivers" href="/risks" />
            <RiskDriverList
              drivers={riskDrivers?.drivers ?? []}
              disclaimer={riskDrivers?.disclaimer}
            />
          </div>

          {/* ── Reorder queue preview ───────────────────────────────────── */}
          <div style={{ marginBottom: "24px" }}>
            <SectionHeader title="Reorder queue (top 5)" href="/recommendations" />
            <Panel>
              <ReorderQueueTable items={queue?.items ?? []} limit={5} compact />
              {queue && queue.items.length > 5 && (
                <div style={{ marginTop: "10px", textAlign: "right" }}>
                  <Link href="/recommendations" style={{ fontSize: "12px", color: "#2563eb" }}>
                    View all {queue.items.length} recommendations →
                  </Link>
                </div>
              )}
            </Panel>
          </div>

          {/* ── Safety boundary ─────────────────────────────────────────── */}
          <div
            style={{
              background: "#f8fafc",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "14px 18px",
              fontSize: "12px",
              color: "var(--text-secondary)",
            }}
          >
            <strong style={{ color: "var(--text-primary)" }}>Safety boundary:</strong>{" "}
            DemandOS does not create purchase orders, contact suppliers, or trigger any external action.
            All outputs are internal review guidance computed from the synthetic demo dataset.
            Scenario outputs are simulated only. Connectors are disabled.
            <span style={{ display: "block", marginTop: "6px" }}>
              <Link href="/data-science" style={{ color: "#2563eb" }}>ML Insights →</Link>
              {" · "}
              <Link href="/overview" style={{ color: "#2563eb" }}>Pipeline overview →</Link>
              {" · "}
              <Link href="/scenarios" style={{ color: "#2563eb" }}>Scenario planner →</Link>
            </span>
          </div>
        </>
      )}
    </div>
  );
}
