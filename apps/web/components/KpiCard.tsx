interface KpiCardProps {
  label: string;
  value: string | number;
  color?: string;
  sub?: string;
  onClick?: () => void;
}

export default function KpiCard({ label, value, color, sub, onClick }: KpiCardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "16px",
        textAlign: "center",
        cursor: onClick ? "pointer" : "default",
        transition: "border-color 0.15s",
      }}
    >
      <div
        style={{
          fontSize: "26px",
          fontWeight: 700,
          color: color ?? "var(--text-primary)",
          lineHeight: 1.1,
        }}
      >
        {value}
      </div>
      <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "4px" }}>
        {label}
      </div>
      {sub && (
        <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "2px" }}>
          {sub}
        </div>
      )}
    </div>
  );
}
