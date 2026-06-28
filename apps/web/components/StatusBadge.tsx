"use client";

const COLORS: Record<string, { bg: string; text: string }> = {
  critical:    { bg: "#fee2e2", text: "#991b1b" },
  high:        { bg: "#ffedd5", text: "#9a3412" },
  medium:      { bg: "#fef3c7", text: "#92400e" },
  warning:     { bg: "#fef3c7", text: "#92400e" },
  low:         { bg: "#dcfce7", text: "#166534" },
  healthy:     { bg: "#dcfce7", text: "#166534" },
  ready:       { bg: "#dcfce7", text: "#166534" },
  strong:      { bg: "#dcfce7", text: "#166534" },
  completed:   { bg: "#dcfce7", text: "#166534" },
  passed:      { bg: "#dcfce7", text: "#166534" },
  success:     { bg: "#dcfce7", text: "#166534" },
  ok:          { bg: "#dcfce7", text: "#166534" },
  directional: { bg: "#dbeafe", text: "#1e40af" },
  running:     { bg: "#dbeafe", text: "#1e40af" },
  open:        { bg: "#dbeafe", text: "#1e40af" },
  pending:     { bg: "#f1f5f9", text: "#475569" },
  weak:        { bg: "#f1f5f9", text: "#475569" },
  failed:      { bg: "#f1f5f9", text: "#475569" },
  no_data:     { bg: "#f1f5f9", text: "#475569" },
  no_model:    { bg: "#f1f5f9", text: "#475569" },
  unknown:     { bg: "#f1f5f9", text: "#475569" },
  incomplete:  { bg: "#f1f5f9", text: "#475569" },
  ignored:     { bg: "#f1f5f9", text: "#475569" },
  synthetic:   { bg: "#e0e7ff", text: "#3730a3" },
  demo:        { bg: "#e0e7ff", text: "#3730a3" },
};

interface StatusBadgeProps {
  value: string | null | undefined;
  label?: string;
}

export default function StatusBadge({ value, label }: StatusBadgeProps) {
  const raw = value ?? "unknown";
  const key = raw.toLowerCase().replace(/[\s/]+/g, "_");
  const colors = COLORS[key] ?? COLORS.unknown;
  const display = label ?? raw;

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
        whiteSpace: "nowrap",
      }}
    >
      {display}
    </span>
  );
}
