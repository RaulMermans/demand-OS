"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getDashboardProduct } from "@/lib/api";
import type { DashboardProductResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import LineChartPanel from "@/components/LineChartPanel";

function fmt(val: number | null | undefined, digits = 0): string {
  if (val === null || val === undefined) return "—";
  return val.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function currency(val: number | null | undefined): string {
  if (val === null || val === undefined) return "—";
  return `€${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function ProductDrilldownPage() {
  const params = useParams();
  const productId = typeof params?.productId === "string" ? params.productId : "";

  const [data, setData] = useState<DashboardProductResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    getDashboardProduct(productId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data || data.status === "not_found") {
    return (
      <EmptyState
        title="Product not found"
        message={`No product with ID "${productId}" was found in the database.`}
        action={<Link href="/data-health" style={{ color: "var(--accent)", fontSize: "13px" }}>← Back to Data Health</Link>}
      />
    );
  }

  const { product, supplier, risk_rows, recommendation_rows, forecast_rows } = data;

  const forecastChartData = forecast_rows.map((r) => ({
    date: r.forecast_date ?? "",
    p50: r.p50_units ?? undefined,
    p10: r.p10_units ?? undefined,
    p90: r.p90_units ?? undefined,
    actual: r.actual_units ?? undefined,
  }));

  return (
    <div>
      {/* Breadcrumb */}
      <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "8px" }}>
        <Link href="/" style={{ color: "var(--accent)", textDecoration: "none" }}>Home</Link>
        {" / "}
        <span>Product</span>
        {" / "}
        <span style={{ color: "var(--text-primary)" }}>{product.sku}</span>
      </div>

      <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "2px" }}>
        {product.name}
      </h1>
      <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginBottom: "24px" }}>
        {product.sku} · {product.category ?? "—"} · {product.brand ?? "—"}
      </p>
      <div className="notice notice-info" style={{ marginBottom: "24px" }}>
        Product-level forecasts, risks, and internal reorder guidance are computed
        from the latest completed pipeline runs.
      </div>

      {/* Product metadata */}
      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
          Product Details
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
            gap: "12px",
          }}
        >
          {[
            { label: "Unit Cost", value: currency(product.unit_cost) },
            { label: "Unit Price", value: currency(product.unit_price) },
            { label: "Lead Time", value: product.lead_time_days != null ? `${product.lead_time_days} days` : "—" },
            { label: "Active", value: product.is_active ? "Yes" : "No" },
            { label: "Supplier", value: supplier?.name ?? (product.supplier_id ? product.supplier_id.slice(0, 8) : "—") },
            { label: "Reliability", value: supplier?.reliability_score != null ? `${(supplier.reliability_score * 100).toFixed(0)}%` : "—" },
          ].map(({ label, value }) => (
            <div
              key={label}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "12px",
                padding: "16px",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "4px" }}>{label}</div>
              <div style={{ fontSize: "16px", fontWeight: 600 }}>{value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Forecast chart */}
      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
          Forecast
        </h2>
        {forecastChartData.length > 0 ? (
          <LineChartPanel
            data={forecastChartData}
            series={[
              { key: "actual", label: "Actual", color: "#6366f1" },
              { key: "p50", label: "Forecast P50", color: "#2563eb" },
              { key: "p10", label: "P10", color: "#93c5fd", dashed: true },
              { key: "p90", label: "P90", color: "#93c5fd", dashed: true },
            ]}
            xKey="date"
          />
        ) : (
          <EmptyState
            title="No forecast data"
            message="Run the baseline or planning forecast to see forecast rows for this product."
            action={<Link href="/pipeline" style={{ color: "var(--accent)", fontSize: "13px" }}>Go to Pipeline Controls →</Link>}
          />
        )}
      </section>

      {/* Risk rows */}
      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
          Stockout Risk by Store
        </h2>
        {risk_rows.length === 0 ? (
          <EmptyState
            title="No risk data"
            message="Run the stockout risk engine to see per-store risk scores."
            action={<Link href="/pipeline" style={{ color: "var(--accent)", fontSize: "13px" }}>Go to Pipeline Controls →</Link>}
          />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Store", "Risk Tier", "Score", "Days Until Stockout", "On Hand", "Lost Sales Est.", "As Of"].map((h) => (
                    <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-secondary)", fontWeight: 600, fontSize: "11px", textTransform: "uppercase" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {risk_rows.map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)", background: i % 2 ? "transparent" : "var(--surface)" }}>
                    <td style={{ padding: "8px 12px", fontFamily: "monospace", fontSize: "11px" }}>{r.store_id.slice(0, 8)}</td>
                    <td style={{ padding: "8px 12px" }}><StatusBadge value={r.risk_tier ?? "unknown"} /></td>
                    <td style={{ padding: "8px 12px" }}>{fmt(r.risk_score)}</td>
                    <td style={{ padding: "8px 12px" }}>{r.days_until_stockout != null ? `${fmt(r.days_until_stockout, 1)} days` : "—"}</td>
                    <td style={{ padding: "8px 12px" }}>{fmt(r.current_available_units)}</td>
                    <td style={{ padding: "8px 12px" }}>{currency(r.lost_sales_value_estimate)}</td>
                    <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{r.as_of_date ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Recommendation rows */}
      <section>
        <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
          Reorder Recommendations by Store
        </h2>
        {recommendation_rows.length === 0 ? (
          <EmptyState
            title="No recommendations"
            message="Run the recommendation engine to see reorder suggestions for this product."
            action={<Link href="/pipeline" style={{ color: "var(--accent)", fontSize: "13px" }}>Go to Pipeline Controls →</Link>}
          />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Store", "Urgency", "Rec. Units", "Est. Cost", "Days Until Stockout", "Status", "Reason"].map((h) => (
                    <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-secondary)", fontWeight: 600, fontSize: "11px", textTransform: "uppercase" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recommendation_rows.map((r, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)", background: i % 2 ? "transparent" : "var(--surface)" }}>
                    <td style={{ padding: "8px 12px", fontFamily: "monospace", fontSize: "11px" }}>{r.store_id.slice(0, 8)}</td>
                    <td style={{ padding: "8px 12px" }}><StatusBadge value={r.urgency ?? "unknown"} /></td>
                    <td style={{ padding: "8px 12px", fontWeight: 600 }}>{fmt(r.recommended_units_rounded)}</td>
                    <td style={{ padding: "8px 12px" }}>{currency(r.estimated_order_cost)}</td>
                    <td style={{ padding: "8px 12px" }}>{r.days_until_stockout != null ? `${fmt(r.days_until_stockout, 1)} days` : "—"}</td>
                    <td style={{ padding: "8px 12px" }}><StatusBadge value={r.status} /></td>
                    <td style={{ padding: "8px 12px", color: "var(--text-secondary)", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {r.recommendation_reason ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
