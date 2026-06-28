"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getProductForecast } from "@/lib/api";
import type { ProductForecastResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import Link from "next/link";

export default function ProductDrilldownPage() {
  const params = useParams();
  const productId = params?.productId as string;

  const [forecast, setForecast] = useState<ProductForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    getProductForecast(productId, { limit: 90 })
      .then(setForecast)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [productId]);

  return (
    <div>
      <div style={{ marginBottom: "20px" }}>
        <Link href="/forecasts" style={{ fontSize: "13px", color: "var(--accent)", textDecoration: "none" }}>
          ← Forecasts
        </Link>
      </div>

      <h1 style={{ fontSize: "22px", fontWeight: 800, letterSpacing: "-0.02em", marginBottom: "4px" }}>
        Product forecast
      </h1>
      <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "20px", fontFamily: "monospace" }}>
        {productId}
      </div>

      {loading && <LoadingState message="Loading product forecast..." />}
      {error && <ErrorState message={error} />}

      {!loading && !error && forecast && (
        <div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px", marginBottom: "16px" }}>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "8px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Forecast summary
            </div>
            <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              {forecast.rows.length} forecasted demand points
            </div>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  {["Date", "Type", "p50 demand", "p10", "p90", "Actual"].map((h) => (
                    <th key={h} style={{ padding: "8px", textAlign: "left", color: "var(--text-secondary)", fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {forecast.rows.slice(0, 50).map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "7px 8px" }}>{String(row.forecast_date ?? "").slice(0, 10)}</td>
                    <td style={{ padding: "7px 8px", color: "var(--text-secondary)" }}>{String(row.forecast_type ?? "")}</td>
                    <td style={{ padding: "7px 8px", fontWeight: 600 }}>{row.p50_units?.toFixed(1) ?? "—"}</td>
                    <td style={{ padding: "7px 8px", color: "var(--text-secondary)" }}>{row.p10_units?.toFixed(1) ?? "—"}</td>
                    <td style={{ padding: "7px 8px", color: "var(--text-secondary)" }}>{row.p90_units?.toFixed(1) ?? "—"}</td>
                    <td style={{ padding: "7px 8px" }}>{row.actual_units?.toFixed(1) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {forecast.rows.length > 50 && (
              <div style={{ marginTop: "8px", fontSize: "11px", color: "var(--text-secondary)" }}>
                Showing 50 of {forecast.rows.length} rows
              </div>
            )}
          </div>
        </div>
      )}

      {!loading && !error && !forecast && (
        <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
          No forecast data found for this product.
        </div>
      )}
    </div>
  );
}
