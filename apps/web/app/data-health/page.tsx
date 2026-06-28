"use client";

import { useEffect, useState } from "react";
import { getDataHealth } from "@/lib/api";
import type { DataHealthResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import PageHeader from "@/components/PageHeader";

const LINEAGE_STEPS = [
  { label: "Raw Records", desc: "Orders, inventory, products, stores, suppliers" },
  { label: "Cleaned / Daily", desc: "Aggregated to daily (product, store, date) rows" },
  { label: "Feature Matrix", desc: "Lag, rolling, calendar, price, promo features" },
  { label: "Forecasts", desc: "Predicted demand — baseline + ML models" },
  { label: "Stockout Risk", desc: "Probability and days-until-stockout per item" },
  { label: "Recommendations", desc: "Internal reorder guidance + estimated costs" },
];

export default function DataHealthPage() {
  const [data, setData] = useState<DataHealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    getDataHealth()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const fmt = (n: number | null | undefined) =>
    n == null ? "—" : n.toLocaleString("en");

  return (
    <div>
      <PageHeader
        title="Data Quality"
        subtitle="Is the data ready and complete enough to trust the outputs?"
        kicker="Pipeline observability"
        badge="Read-only · no mutations"
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={load} />}

      {data && data.status === "no_data" && (
        <EmptyState
          title="No data ingested yet."
          message="Run POST /api/demo/reset to seed the demo dataset."
        />
      )}

      {data && data.status !== "no_data" && (
        <>
          {/* Data lineage visual */}
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "20px 24px",
              marginBottom: "24px",
            }}
          >
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "4px" }}>
              Data Lineage
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>
              Each stage of the pipeline transforms data from the previous layer. All stages must
              complete in order before recommendations can be generated.
            </p>
            <div
              style={{
                display: "flex",
                alignItems: "stretch",
                gap: "4px",
                overflowX: "auto",
                paddingBottom: "4px",
              }}
            >
              {LINEAGE_STEPS.map((step, i) => (
                <div key={step.label} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <div
                    style={{
                      background: "var(--border)",
                      borderRadius: "6px",
                      padding: "10px 12px",
                      minWidth: "100px",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontSize: "12px", fontWeight: 700 }}>{step.label}</div>
                    <div
                      style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "3px", lineHeight: 1.3 }}
                    >
                      {step.desc}
                    </div>
                  </div>
                  {i < LINEAGE_STEPS.length - 1 && (
                    <span style={{ fontSize: "14px", color: "var(--text-secondary)", flexShrink: 0 }}>→</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Validation checks */}
          <section style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "4px" }}>
              Pipeline Integrity Checks
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Automated checks that verify each layer has data and that counts are within expected ranges.
            </p>
            <div
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                overflow: "hidden",
              }}
            >
              {data.checks.map((check, i) => (
                <div
                  key={check.name}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 20px",
                    borderBottom: i < data.checks.length - 1 ? "1px solid var(--border)" : "none",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "13px" }}>{check.name.replace(/_/g, " ")}</div>
                    {check.detail && (
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                        {check.detail}
                      </div>
                    )}
                  </div>
                  <StatusBadge value={check.status} />
                </div>
              ))}
            </div>
          </section>

          {/* Raw layer */}
          <section style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "4px" }}>
              Raw Layer — Record Counts
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Operational records ingested from the connector (synthetic commerce data for this demo).
              These are the only records the pipeline consumes as input.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "12px" }}>
              {[
                { label: "Products", value: fmt(data.products_count) },
                { label: "Stores", value: fmt(data.stores_count) },
                { label: "Orders", value: fmt(data.orders_count) },
                { label: "Inventory snapshots", value: fmt(data.inventory_snapshots_count) },
                { label: "Promotions", value: fmt(data.promotions_count) },
                { label: "Suppliers", value: fmt(data.suppliers_count) },
                { label: "Purchase orders", value: fmt(data.purchase_orders_count) },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    padding: "12px 14px",
                  }}
                >
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{m.label}</div>
                  <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "4px" }}>{m.value}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Canonical + feature counts */}
          <section style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "4px" }}>
              Canonical &amp; Feature Layers
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Daily aggregates and the ML feature matrix. The feature matrix is the direct input to
              the forecasting models. All features are leakage-safe.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "12px" }}>
              {[
                { label: "Sales daily", value: fmt(data.canonical_counts?.sales_daily) },
                { label: "Inventory daily", value: fmt(data.canonical_counts?.inventory_daily) },
                { label: "Product store daily", value: fmt(data.canonical_counts?.product_store_daily) },
                { label: "Feature matrix rows", value: fmt(data.feature_counts?.feature_matrix) },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    padding: "12px 14px",
                  }}
                >
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{m.label}</div>
                  <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "4px" }}>{m.value}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Forecast / risk / rec counts */}
          <section style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "4px" }}>
              Forecast, Risk &amp; Recommendation Layers
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Computed outputs — derived entirely from the feature matrix and pipeline logic.
              No precomputed or hardcoded values.
            </p>
            <div
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
              }}
            >
              {[
                { label: "Forecast runs", value: fmt(data.forecast_counts?.forecast_runs) },
                { label: "Forecast rows", value: fmt(data.forecast_counts?.forecasts) },
                { label: "Model metrics", value: fmt(data.forecast_counts?.model_metrics) },
                { label: "Model versions", value: fmt(data.model_counts?.model_versions) },
                { label: "Stockout risk runs", value: fmt(data.risk_counts?.stockout_risk_runs) },
                { label: "Stockout risk rows", value: fmt(data.risk_counts?.stockout_risks) },
                { label: "Recommendation runs", value: fmt(data.recommendation_counts?.recommendation_runs) },
                { label: "Reorder recommendations", value: fmt(data.recommendation_counts?.reorder_recommendations) },
              ].map((row, i, arr) => (
                <div
                  key={row.label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "10px 18px",
                    borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <span style={{ fontWeight: 600 }}>{row.value}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Latest run timestamps */}
          <section style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "4px" }}>
              Latest Run Timestamps
            </h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Most recent status of each pipeline stage. All stages should show completed for a
              fully operational demo.
            </p>
            <div
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
              }}
            >
              {[
                { label: "Ingestion", info: data.latest_ingestion_run },
                { label: "Aggregation", info: data.latest_aggregation_run },
                { label: "Feature build", info: data.latest_feature_run },
                { label: "Forecast run", info: data.latest_forecast_run },
                { label: "Model training", info: data.latest_model_version },
                { label: "Stockout risk", info: data.latest_stockout_risk_run },
                { label: "Recommendations", info: data.latest_recommendation_run },
              ].map((row, i, arr) => (
                <div
                  key={row.label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "10px 18px",
                    borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none",
                  }}
                >
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <StatusBadge
                    value={(row.info as Record<string, unknown>)?.status as string ?? "warning"}
                    label={(row.info as Record<string, unknown>)?.status as string ?? "Not run"}
                  />
                </div>
              ))}
            </div>
          </section>

          {/* Data integrity note */}
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "12px 16px",
              fontSize: "12px",
              color: "var(--text-secondary)",
            }}
          >
            <strong>Data integrity:</strong> Raw records are never modified after ingestion. Derived
            tables (features, forecasts, risks, recommendations) are re-computed from scratch on each
            pipeline run. No precomputed or hardcoded output values exist in this system.
          </div>
        </>
      )}
    </div>
  );
}
