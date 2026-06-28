interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  onClick?: () => void;
}

export default function KpiCard({ label, value, sub, color, onClick }: KpiCardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "10px",
        padding: "16px",
        cursor: onClick ? "pointer" : "default",
        boxShadow: "var(--shadow-sm)",
        transition: "border-color 0.15s, transform 0.15s",
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
          fontSize: "28px",
          fontWeight: 700,
          color: color ?? "var(--text-primary)",
          lineHeight: 1.1,
          letterSpacing: "-0.02em",
        }}
      >
        {value}
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
