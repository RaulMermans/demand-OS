"use client";

import { useEffect, useState } from "react";
import { getDataHealth } from "@/lib/api";
import type { DataHealthResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";

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
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "4px" }}>Data Health</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Record counts and validation status for every pipeline layer
      </p>

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
          {/* Validation checks */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Validation Checks
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden" }}>
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
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>{check.detail}</div>
                    )}
                  </div>
                  <StatusBadge value={check.status} />
                </div>
              ))}
            </div>
          </section>

          {/* Raw layer counts */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Raw Layer
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px" }}>
              {[
                { label: "Products", value: fmt(data.products_count) },
                { label: "Stores", value: fmt(data.stores_count) },
                { label: "Orders", value: fmt(data.orders_count) },
                { label: "Inventory snapshots", value: fmt(data.inventory_snapshots_count) },
                { label: "Promotions", value: fmt(data.promotions_count) },
                { label: "Suppliers", value: fmt(data.suppliers_count) },
                { label: "Purchase orders", value: fmt(data.purchase_orders_count) },
              ].map((m) => (
                <div key={m.label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "12px 16px" }}>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{m.label}</div>
                  <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "4px" }}>{m.value}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Canonical + feature counts */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Canonical &amp; Feature Layers
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px" }}>
              {[
                { label: "Sales daily", value: fmt(data.canonical_counts?.sales_daily) },
                { label: "Inventory daily", value: fmt(data.canonical_counts?.inventory_daily) },
                { label: "Product store daily", value: fmt(data.canonical_counts?.product_store_daily) },
                { label: "Feature matrix rows", value: fmt(data.feature_counts?.feature_matrix) },
              ].map((m) => (
                <div key={m.label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px", padding: "12px 16px" }}>
                  <div style={{ color: "var(--text-secondary)", fontSize: "11px" }}>{m.label}</div>
                  <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "4px" }}>{m.value}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Model/forecast/risk/rec counts */}
          <section style={{ marginBottom: "32px" }}>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Model, Risk &amp; Recommendation Layers
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              {[
                { label: "Forecast runs", value: fmt(data.forecast_counts?.forecast_runs) },
                { label: "Forecast rows", value: fmt(data.forecast_counts?.forecasts) },
                { label: "Model metrics", value: fmt(data.forecast_counts?.model_metrics) },
                { label: "Model versions", value: fmt(data.model_counts?.model_versions) },
                { label: "Stockout risk runs", value: fmt(data.risk_counts?.stockout_risk_runs) },
                { label: "Stockout risks", value: fmt(data.risk_counts?.stockout_risks) },
                { label: "Recommendation runs", value: fmt(data.recommendation_counts?.recommendation_runs) },
                { label: "Reorder recommendations", value: fmt(data.recommendation_counts?.reorder_recommendations) },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", padding: "10px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <span style={{ fontWeight: 600 }}>{row.value}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Latest runs */}
          <section>
            <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
              Latest Run Statuses
            </h2>
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              {[
                { label: "Latest ingestion", info: data.latest_ingestion_run },
                { label: "Latest aggregation", info: data.latest_aggregation_run },
                { label: "Latest feature run", info: data.latest_feature_run },
                { label: "Latest forecast run", info: data.latest_forecast_run },
                { label: "Latest model version", info: data.latest_model_version },
                { label: "Latest risk run", info: data.latest_stockout_risk_run },
                { label: "Latest recommendation run", info: data.latest_recommendation_run },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 20px", borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{row.label}</span>
                  <StatusBadge
                    value={(row.info as Record<string, unknown>)?.status as string ?? "warning"}
                    label={(row.info as Record<string, unknown>)?.status as string ?? "Not run"}
                  />
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
