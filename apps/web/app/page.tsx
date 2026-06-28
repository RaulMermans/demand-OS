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
import SituationBanner from "@/components/SituationBanner";
import DemoScenarioCard from "@/components/DemoScenarioCard";
import TechnicalTrace from "@/components/TechnicalTrace";
import TrustBadge from "@/components/TrustBadge";
import InventoryTrendChart from "@/components/InventoryTrendChart";
import RiskDriverList from "@/components/RiskDriverList";
import ReorderQueueTable from "@/components/ReorderQueueTable";

const fmt = (n: number | null | undefined, dec = 0) =>
  n == null ? "—" : n.toLocaleString("en", { maximumFractionDigits: dec });

function Panel({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "10px",
        padding: "18px",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function SectionLabel({ title, href, linkLabel }: { title: string; href?: string; linkLabel?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
      <h2 style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", margin: 0 }}>
        {title}
      </h2>
      {href && (
        <Link href={href} style={{ fontSize: "12px", color: "var(--accent)", textDecoration: "none" }}>
          {linkLabel ?? "View all →"}
        </Link>
      )}
    </div>
  );
}

function MetricChip({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "14px",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: "26px", fontWeight: 800, color: color ?? "var(--text-primary)", letterSpacing: "-0.02em" }}>
        {value}
      </div>
      <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "3px" }}>
        {label}
      </div>
    </div>
  );
}

export default function CockpitPage() {
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
  const noData = cockpit?.status === "no_data";
  const hasData = !!cockpit && !noData;

  const pipelineReady = cockpit?.pipeline ?? null;

  return (
    <div>
      {/* ── Page title ─────────────────────────────────────────────────── */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "26px", fontWeight: 800, letterSpacing: "-0.02em", margin: "0 0 4px" }}>
          Cockpit
        </h1>
        <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0 }}>
          See the current inventory situation and the highest-priority actions.
        </p>
      </div>

      {loading && <LoadingState message="Loading cockpit..." />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && (
        <>
          {/* ── No-data state ──────────────────────────────────────────── */}
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
              <strong>No pipeline data found.</strong> Run the demo pipeline from the{" "}
              <Link href="/pipeline" style={{ color: "#92400e" }}>
                Pipeline Trace
              </Link>{" "}
              page to seed the demo dataset end-to-end. All metrics will populate after the pipeline completes.
            </div>
          )}

          {/* ── Situation Banner ───────────────────────────────────────── */}
          {hasData && cockpit && (
            <SituationBanner
              atRiskSkuStores={cockpit.inventory.at_risk_sku_stores ?? 0}
              estimatedLostSales={cockpit.risk.estimated_lost_sales}
              openRecommendations={cockpit.recommendations.open ?? 0}
              forecastQuality={qualityLabel}
              criticalCount={cockpit.risk.critical ?? 0}
              highRiskCount={cockpit.risk.high ?? 0}
            />
          )}

          {hasData && cockpit && (
            <>
              {/* ── Key metrics strip ──────────────────────────────────── */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                  gap: "10px",
                  marginBottom: "24px",
                }}
              >
                <MetricChip
                  label="Critical risks"
                  value={fmt(cockpit.risk.critical)}
                  color={(cockpit.risk.critical ?? 0) > 0 ? "#dc2626" : "#15803d"}
                />
                <MetricChip
                  label="High risks"
                  value={fmt(cockpit.risk.high)}
                  color={(cockpit.risk.high ?? 0) > 0 ? "#d97706" : "#15803d"}
                />
                <MetricChip
                  label="Open recommendations"
                  value={fmt(cockpit.recommendations.open)}
                />
                <MetricChip
                  label="Forecast trust"
                  value={qualityLabel}
                  color={
                    qualityLabel === "Strong" ? "#15803d" :
                    qualityLabel === "Directional" ? "#6d28d9" :
                    qualityLabel === "Weak / Demo signal" ? "#d97706" : "#6b7280"
                  }
                />
              </div>

              {/* ── Risk drivers + Reorder queue ───────────────────────── */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                  marginBottom: "24px",
                }}
              >
                <Panel>
                  <SectionLabel title="Top risk drivers" href="/risks" linkLabel="Risk Board →" />
                  <RiskDriverList
                    drivers={riskDrivers?.drivers ?? []}
                    disclaimer={riskDrivers?.disclaimer}
                  />
                </Panel>

                <Panel>
                  <SectionLabel title="Reorder queue" href="/recommendations" linkLabel="Full queue →" />
                  <ReorderQueueTable items={queue?.items ?? []} limit={4} compact />
                  {(queue?.items.length ?? 0) === 0 && (
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", padding: "12px 0" }}>
                      No open recommendations. Run the pipeline to generate reorder guidance.
                    </div>
                  )}
                </Panel>
              </div>

              {/* ── Inventory trend ────────────────────────────────────── */}
              <Panel style={{ marginBottom: "24px" }}>
                <SectionLabel title="Inventory trend — last 30 days" />
                {trend && trend.series.length > 0 ? (
                  <>
                    <InventoryTrendChart series={trend.series} height={200} />
                    {trend.metadata.reorder_point_note && (
                      <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "6px", fontStyle: "italic" }}>
                        {trend.metadata.reorder_point_note}
                      </p>
                    )}
                  </>
                ) : (
                  <InventoryTrendChart series={[]} height={200} />
                )}
              </Panel>

              {/* ── Pipeline trace strip ───────────────────────────────── */}
              {pipelineReady && (
                <div style={{ marginBottom: "16px" }}>
                  <TechnicalTrace
                    dataSeeded={pipelineReady.data_seeded === "ready"}
                    featuresBuilt={pipelineReady.features === "ready"}
                    forecastsReady={pipelineReady.forecasts === "ready"}
                    risksScored={pipelineReady.risks === "ready"}
                    recommendationsReady={pipelineReady.recommendations === "ready"}
                  />
                </div>
              )}

              {/* ── Demo scenario + Safety boundary ───────────────────── */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                  marginTop: "8px",
                }}
              >
                <DemoScenarioCard
                  products={cockpit.dataset.products ?? 0}
                  stores={cockpit.dataset.stores ?? 0}
                  days={180}
                />

                <div
                  style={{
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "10px",
                    padding: "18px",
                  }}
                >
                  <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", marginBottom: "10px" }}>
                    Safety boundary
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: "12px" }}>
                    DemandOS does not create purchase orders, contact suppliers, or trigger any external
                    action. All outputs are internal planning guidance computed from the synthetic demo dataset.
                  </div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "12px" }}>
                    <TrustBadge label="Synthetic demo" />
                    <TrustBadge label="No external actions" />
                  </div>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    <Link href="/model-performance" style={{ fontSize: "12px", color: "var(--accent)", textDecoration: "none" }}>Forecast Trust →</Link>
                    <Link href="/data-health" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none" }}>Data Quality →</Link>
                    <Link href="/scenarios" style={{ fontSize: "12px", color: "var(--text-secondary)", textDecoration: "none" }}>Scenarios →</Link>
                  </div>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
