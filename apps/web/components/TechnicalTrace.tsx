"use client";

interface Props {
  dataSeeded: boolean;
  featuresBuilt: boolean;
  forecastsReady: boolean;
  risksScored: boolean;
  recommendationsReady: boolean;
  lastRunLabel?: string;
}

const STEPS = [
  { key: "dataSeeded",           label: "Data" },
  { key: "featuresBuilt",        label: "Features" },
  { key: "forecastsReady",       label: "Forecasts" },
  { key: "risksScored",          label: "Risks" },
  { key: "recommendationsReady", label: "Recommendations" },
];

export default function TechnicalTrace({
  dataSeeded,
  featuresBuilt,
  forecastsReady,
  risksScored,
  recommendationsReady,
  lastRunLabel,
}: Props) {
  const values: Record<string, boolean> = {
    dataSeeded,
    featuresBuilt,
    forecastsReady,
    risksScored,
    recommendationsReady,
  };

  return (
    <div
      style={{
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        borderRadius: "10px",
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "6px",
      }}
    >
      {lastRunLabel && (
        <span
          style={{
            fontSize: "11px",
            color: "var(--text-secondary)",
            marginRight: "8px",
          }}
        >
          Last pipeline: <strong style={{ color: "var(--text-primary)" }}>{lastRunLabel}</strong>
        </span>
      )}
      {STEPS.map((step, i) => {
        const ok = values[step.key];
        return (
          <span key={step.key} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            {i > 0 || lastRunLabel ? (
              <span style={{ color: "var(--border-strong)", margin: "0 2px" }}>|</span>
            ) : null}
            <span
              style={{
                fontSize: "12px",
                fontWeight: ok ? 600 : 400,
                color: ok ? "var(--success)" : "var(--warning)",
              }}
            >
              {ok ? "✓" : "○"}
            </span>
            <span
              style={{
                fontSize: "12px",
                color: ok ? "var(--text-primary)" : "var(--text-secondary)",
                fontWeight: ok ? 500 : 400,
              }}
            >
              {step.label}
            </span>
          </span>
        );
      })}
    </div>
  );
}
