"use client";

const TRUST_STYLES: Record<string, { bg: string; color: string }> = {
  strong:              { bg: "#dcfce7", color: "#15803d" },
  ready:               { bg: "#dcfce7", color: "#15803d" },
  directional:         { bg: "#ede9fe", color: "#6d28d9" },
  weak:                { bg: "#fef3c7", color: "#92400e" },
  "weak / demo signal": { bg: "#fef3c7", color: "#92400e" },
  stale:               { bg: "#fef3c7", color: "#92400e" },
  "no model":          { bg: "#f1f5f9", color: "#475569" },
  incomplete:          { bg: "#f1f5f9", color: "#475569" },
  "synthetic demo":    { bg: "#e0e7ff", color: "#3730a3" },
  "no external actions": { bg: "#e0e7ff", color: "#3730a3" },
};

const SIZE_STYLES = {
  sm:  { fontSize: "10px", padding: "2px 8px" },
  md:  { fontSize: "12px", padding: "4px 12px" },
  lg:  { fontSize: "13px", padding: "5px 14px" },
};

interface Props {
  label: string;
  size?: "sm" | "md" | "lg";
}

export default function TrustBadge({ label, size = "sm" }: Props) {
  const key = label.toLowerCase();
  const style = TRUST_STYLES[key] ?? { bg: "#f1f5f9", color: "#475569" };
  const sz = SIZE_STYLES[size];

  return (
    <span
      style={{
        display: "inline-block",
        padding: sz.padding,
        borderRadius: "999px",
        fontSize: sz.fontSize,
        fontWeight: 700,
        background: style.bg,
        color: style.color,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}
