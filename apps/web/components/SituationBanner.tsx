"use client";

import Link from "next/link";
import StatusBadge from "./StatusBadge";

interface Props {
  atRiskSkuStores: number;
  estimatedLostSales: number | null;
  openRecommendations: number;
  forecastQuality: string;
  criticalCount: number;
  highRiskCount: number;
}

export default function SituationBanner({
  atRiskSkuStores,
  estimatedLostSales,
  openRecommendations,
  forecastQuality,
  criticalCount,
  highRiskCount,
}: Props) {
  const hasRisk = atRiskSkuStores > 0 || criticalCount > 0 || highRiskCount > 0;

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "14px",
        padding: "28px 32px",
        boxShadow: "var(--shadow-card)",
        marginBottom: "32px",
      }}
    >
      <div
        style={{
          fontSize: "44px",
          fontWeight: 800,
          color: hasRisk ? "var(--danger)" : "var(--success)",
          lineHeight: 1,
          letterSpacing: "-0.03em",
          marginBottom: "8px",
        }}
      >
        {atRiskSkuStores.toLocaleString()}
      </div>

      <div
        style={{
          fontSize: "17px",
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: "12px",
        }}
      >
        SKU-store combinations need attention.
      </div>

      <div
        style={{
          fontSize: "14px",
          color: "var(--text-secondary)",
          marginBottom: "6px",
          display: "flex",
          flexWrap: "wrap",
          gap: "4px",
          alignItems: "center",
        }}
      >
        {estimatedLostSales != null ? (
          <span>
            Estimated lost-sales exposure:{" "}
            <strong style={{ color: "var(--text-primary)" }}>
              €{Math.round(estimatedLostSales).toLocaleString()}
            </strong>
          </span>
        ) : (
          <span>No lost-sales estimate yet.</span>
        )}
        <span style={{ margin: "0 4px", opacity: 0.4 }}>·</span>
        <span>
          <strong style={{ color: "var(--text-primary)" }}>{openRecommendations}</strong>{" "}
          {openRecommendations === 1 ? "recommendation" : "recommendations"} ready for review.
        </span>
      </div>

      <div
        style={{
          fontSize: "13px",
          color: "var(--text-secondary)",
          marginBottom: "24px",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        Forecast trust:
        <StatusBadge value={forecastQuality} />
      </div>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
        <Link
          href="/recommendations"
          style={{
            display: "inline-block",
            padding: "10px 22px",
            borderRadius: "9px",
            background: "var(--accent)",
            color: "#fff",
            fontSize: "13px",
            fontWeight: 700,
            textDecoration: "none",
          }}
        >
          Review Reorder Queue
        </Link>
        <Link
          href="/risks"
          style={{
            display: "inline-block",
            padding: "10px 22px",
            borderRadius: "9px",
            background: "var(--surface-2)",
            color: "var(--text-primary)",
            border: "1px solid var(--border)",
            fontSize: "13px",
            fontWeight: 600,
            textDecoration: "none",
          }}
        >
          View Risk Board
        </Link>
      </div>
    </div>
  );
}
