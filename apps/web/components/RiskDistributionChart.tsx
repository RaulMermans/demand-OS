"use client";

interface Props {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

const CELLS = [
  { key: "critical", label: "Critical", bg: "#fee2e2", text: "#991b1b", value_color: "#dc2626" },
  { key: "high",     label: "High",     bg: "#ffedd5", text: "#9a3412", value_color: "#f97316" },
  { key: "medium",   label: "Medium",   bg: "#fef3c7", text: "#92400e", value_color: "#eab308" },
  { key: "low",      label: "Low",      bg: "#dcfce7", text: "#166534", value_color: "#16a34a" },
];

export default function RiskDistributionChart({ critical, high, medium, low }: Props) {
  const values: Record<string, number> = { critical, high, medium, low };
  const total = critical + high + medium + low;

  if (total === 0) {
    return (
      <div
        style={{
          padding: "24px",
          textAlign: "center",
          color: "var(--text-secondary)",
          fontSize: "13px",
          border: "1px dashed var(--border)",
          borderRadius: "8px",
        }}
      >
        No risk data available. Run the pipeline to score inventory risk.
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "10px",
      }}
    >
      {CELLS.map(({ key, label, bg, text, value_color }) => (
        <div
          key={key}
          style={{
            background: bg,
            border: `1px solid ${value_color}33`,
            borderRadius: "10px",
            padding: "14px 16px",
          }}
        >
          <div
            style={{
              fontSize: "11px",
              fontWeight: 700,
              color: text,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
              marginBottom: "6px",
            }}
          >
            {label}
          </div>
          <div
            style={{
              fontSize: "32px",
              fontWeight: 800,
              color: value_color,
              lineHeight: 1,
              letterSpacing: "-0.02em",
            }}
          >
            {values[key] ?? 0}
          </div>
          <div
            style={{
              fontSize: "10px",
              color: text,
              opacity: 0.8,
              marginTop: "4px",
            }}
          >
            SKU-stores
          </div>
        </div>
      ))}
    </div>
  );
}
