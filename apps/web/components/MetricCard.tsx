interface MetricCardProps {
  label: string;
  value: string | number;
  note?: string;
  status?: "live" | "scaffold" | "warning";
}

export default function MetricCard({
  label,
  value,
  note,
  status = "scaffold",
}: MetricCardProps) {
  const borderColor =
    status === "live"
      ? "var(--success)"
      : status === "warning"
      ? "var(--warning)"
      : "var(--border)";

  return (
    <div
      style={{
        background: "var(--surface)",
        border: `1px solid ${borderColor}`,
        borderRadius: "8px",
        padding: "20px",
      }}
    >
      <div style={{ color: "var(--text-secondary)", fontSize: "12px", marginBottom: "8px" }}>
        {label}
      </div>
      <div style={{ fontSize: "28px", fontWeight: 700 }}>{value}</div>
      {note && (
        <div style={{ color: "var(--scaffold-text)", fontSize: "11px", marginTop: "6px" }}>
          {note}
        </div>
      )}
    </div>
  );
}
