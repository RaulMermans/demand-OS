"use client";

interface Props {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

const TIERS = [
  { key: "critical", label: "Critical", color: "#dc2626" },
  { key: "high", label: "High", color: "#ea580c" },
  { key: "medium", label: "Medium", color: "#d97706" },
  { key: "low", label: "Low", color: "#16a34a" },
];

export default function RiskDistributionChart({ critical, high, medium, low }: Props) {
  const values: Record<string, number> = { critical, high, medium, low };
  const total = critical + high + medium + low;

  if (total === 0) {
    return (
      <div
        style={{
          padding: "20px",
          textAlign: "center",
          color: "var(--text-secondary)",
          fontSize: "13px",
          border: "1px dashed var(--border)",
          borderRadius: "6px",
        }}
      >
        No risk data available.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {TIERS.map(({ key, label, color }) => {
        const val = values[key] ?? 0;
        const pct = total > 0 ? (val / total) * 100 : 0;
        return (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ width: "58px", fontSize: "11px", color: "var(--text-secondary)", flexShrink: 0 }}>
              {label}
            </span>
            <div
              style={{
                flex: 1,
                height: "10px",
                background: "var(--border)",
                borderRadius: "5px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: "100%",
                  background: color,
                  borderRadius: "5px",
                  transition: "width 0.4s ease",
                }}
              />
            </div>
            <span
              style={{
                width: "28px",
                fontSize: "13px",
                fontWeight: 700,
                color,
                textAlign: "right",
                flexShrink: 0,
              }}
            >
              {val}
            </span>
          </div>
        );
      })}
    </div>
  );
}
