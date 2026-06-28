interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  trend?: "up" | "down" | "flat";
}

const TREND_ICONS: Record<string, string> = {
  up: "↑",
  down: "↓",
  flat: "→",
};

const TREND_COLORS: Record<string, string> = {
  up: "var(--success)",
  down: "var(--danger)",
  flat: "var(--text-secondary)",
};

export default function MetricCard({ label, value, sub, color, trend }: MetricCardProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "10px",
        padding: "16px",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          color: "var(--text-secondary)",
          fontWeight: 600,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          marginBottom: "8px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: "8px",
        }}
      >
        <div
          style={{
            fontSize: "28px",
            fontWeight: 700,
            color: color ?? "var(--text-primary)",
            lineHeight: 1.1,
            letterSpacing: "-0.02em",
          }}
        >
          {value}
        </div>
        {trend && (
          <span
            style={{
              fontSize: "16px",
              fontWeight: 700,
              color: TREND_COLORS[trend],
            }}
          >
            {TREND_ICONS[trend]}
          </span>
        )}
      </div>
      {sub && (
        <div
          style={{
            fontSize: "11px",
            color: "var(--text-secondary)",
            marginTop: "6px",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}
