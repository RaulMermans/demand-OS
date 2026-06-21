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
        borderRadius: "12px",
        padding: "17px 18px",
        cursor: onClick ? "pointer" : "default",
        boxShadow: "var(--shadow-sm)",
        transition: "border-color 0.15s, transform 0.15s",
      }}
    >
      <div style={{ fontSize: "10px", color: "var(--text-secondary)", fontWeight: 700, letterSpacing: "0.055em", textTransform: "uppercase" }}>
        {label}
      </div>
      <div
        style={{
          fontSize: "27px",
          fontWeight: 750,
          color: color ?? "var(--text-primary)",
          lineHeight: 1.15,
          marginTop: "9px",
          letterSpacing: "-0.025em",
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "5px" }}>
          {sub}
        </div>
      )}
    </div>
  );
}
