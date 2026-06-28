"use client";

interface Props {
  products: number;
  stores: number;
  days: number;
}

export default function DemoScenarioCard({ products, stores, days }: Props) {
  return (
    <div
      style={{
        background: "#eef2ff",
        border: "1px solid #c7d2fe",
        borderRadius: "12px",
        padding: "20px 24px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
        <span
          style={{
            display: "inline-block",
            padding: "3px 9px",
            borderRadius: "999px",
            fontSize: "10px",
            fontWeight: 700,
            letterSpacing: "0.04em",
            background: "#e0e7ff",
            color: "#3730a3",
          }}
        >
          Synthetic demo
        </span>
      </div>

      <div
        style={{
          fontSize: "14px",
          fontWeight: 700,
          color: "#3730a3",
          marginBottom: "6px",
        }}
      >
        Demo Scenario
      </div>

      <div
        style={{
          fontSize: "13px",
          fontWeight: 600,
          color: "#4338ca",
          marginBottom: "8px",
        }}
      >
        {products} products · {stores} stores · {days} days of synthetic data
      </div>

      <div
        style={{
          fontSize: "12px",
          color: "#4338ca",
          opacity: 0.8,
          lineHeight: 1.6,
        }}
      >
        Generated from raw orders, inventory snapshots, suppliers, purchase orders, and promotions.
        No real business data.
      </div>
    </div>
  );
}
