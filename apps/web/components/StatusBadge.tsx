"use client";

const COLORS: Record<string, { bg: string; text: string }> = {
  // Risk / urgency tiers
  critical: { bg: "#fef2f2", text: "#dc2626" },
  high:     { bg: "#fff7ed", text: "#c2410c" },
  medium:   { bg: "#fefce8", text: "#a16207" },
  low:      { bg: "#f0fdf4", text: "#15803d" },
  unknown:  { bg: "var(--surface-2)", text: "var(--text-secondary)" },
  // Pipeline statuses
  completed: { bg: "#f0fdf4", text: "#15803d" },
  success:   { bg: "#f0fdf4", text: "#15803d" },
  ok:        { bg: "#f0fdf4", text: "#15803d" },
  running:   { bg: "#eff6ff", text: "#1d4ed8" },
  failed:    { bg: "#fef2f2", text: "#dc2626" },
  warning:   { bg: "#fefce8", text: "#a16207" },
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
        padding: "2px 8px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: 600,
        letterSpacing: "0.02em",
        background: colors.bg,
        color: colors.text,
      }}
    >
      {display}
    </span>
  );
}
