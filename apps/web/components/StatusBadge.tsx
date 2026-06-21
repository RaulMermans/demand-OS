"use client";

const COLORS: Record<string, { bg: string; text: string }> = {
  // Risk / urgency tiers
  critical: { bg: "var(--danger-soft)", text: "var(--danger)" },
  high:     { bg: "#fff7ed", text: "#c2410c" },
  medium:   { bg: "var(--warning-soft)", text: "#a16207" },
  low:      { bg: "var(--success-soft)", text: "var(--success)" },
  unknown:  { bg: "var(--surface-2)", text: "var(--text-secondary)" },
  // Pipeline statuses
  completed: { bg: "var(--success-soft)", text: "var(--success)" },
  success:   { bg: "var(--success-soft)", text: "var(--success)" },
  ok:        { bg: "var(--success-soft)", text: "var(--success)" },
  green:     { bg: "var(--success-soft)", text: "var(--success)" },
  running:   { bg: "var(--info-soft)", text: "var(--info)" },
  failed:    { bg: "var(--danger-soft)", text: "var(--danger)" },
  red:       { bg: "var(--danger-soft)", text: "var(--danger)" },
  warning:   { bg: "var(--warning-soft)", text: "var(--warning)" },
  yellow:    { bg: "var(--warning-soft)", text: "var(--warning)" },
  // Recommendation statuses
  open:              { bg: "#eff6ff", text: "#1d4ed8" },
  reviewed:          { bg: "#fefce8", text: "#a16207" },
  approved_internal: { bg: "#f0fdf4", text: "#15803d" },
  ignored:           { bg: "var(--surface-2)", text: "var(--text-secondary)" },
  resolved:          { bg: "#f0fdf4", text: "#15803d" },
  // Confidence
  high_confidence:   { bg: "#f0fdf4", text: "#15803d" },
  low_confidence:    { bg: "#fef2f2", text: "#dc2626" },
};

interface StatusBadgeProps {
  value: string | null | undefined;
  label?: string;
}

export default function StatusBadge({ value, label }: StatusBadgeProps) {
  const key = (value ?? "unknown").toLowerCase();
  const colors = COLORS[key] ?? COLORS.unknown;
  const display = label ?? (value ?? "—");

  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 9px",
        borderRadius: "999px",
        fontSize: "10px",
        fontWeight: 700,
        letterSpacing: "0.02em",
        background: colors.bg,
        color: colors.text,
      }}
    >
      {display}
    </span>
  );
}
