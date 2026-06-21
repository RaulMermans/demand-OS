"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import ApiKeyInput from "@/components/ApiKeyInput";
import StatusBadge from "@/components/StatusBadge";
import { getStoredApiKey } from "@/lib/apiKey";

interface MetricRow {
  metric_name: string;
  current_value: number | null;
  previous_value: number | null;
  relative_change_pct: number | null;
  threshold_status: string;
  model_name?: string;
}

interface MonitoringRun {
  run_id: string;
  status: string;
  model_health_status: string | null;
  data_health_status: string | null;
  overall_status: string | null;
  summary: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
}

const STATUS_BG: Record<string, string> = {
  green: "var(--success-soft)",
  yellow: "var(--warning-soft)",
  red: "var(--danger-soft)",
  unknown: "var(--surface-2)",
};

function StatusPill({ status }: { status: string | null }) {
  return <StatusBadge value={status || "unknown"} />;
}

function MetricTable({ metrics, title }: { metrics: MetricRow[]; title: string }) {
  if (metrics.length === 0) {
    return (
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "16px",
          marginBottom: "16px",
        }}
      >
        <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "8px" }}>{title}</div>
        <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
          No metrics available. Run monitoring first.
        </p>
      </div>
    );
  }
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "16px",
        marginBottom: "16px",
      }}
    >
      <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "12px" }}>{title}</div>
      <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th style={{ textAlign: "left", padding: "6px 8px" }}>Metric</th>
            <th style={{ textAlign: "right", padding: "6px 8px" }}>Current</th>
            <th style={{ textAlign: "right", padding: "6px 8px" }}>Previous</th>
            <th style={{ textAlign: "right", padding: "6px 8px" }}>Change %</th>
            <th style={{ textAlign: "left", padding: "6px 8px" }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr
              key={m.metric_name}
              style={{
                borderBottom: "1px solid var(--border)",
                background: STATUS_BG[m.threshold_status] || "transparent",
              }}
            >
              <td style={{ padding: "6px 8px", fontWeight: 600 }}>{m.metric_name.toUpperCase()}</td>
              <td style={{ padding: "6px 8px", textAlign: "right" }}>
                {m.current_value != null ? m.current_value.toFixed(4) : "—"}
              </td>
              <td style={{ padding: "6px 8px", textAlign: "right", color: "var(--text-secondary)" }}>
                {m.previous_value != null ? m.previous_value.toFixed(4) : "—"}
              </td>
              <td
                style={{
                  padding: "6px 8px",
                  textAlign: "right",
                  color:
                    m.relative_change_pct == null
                      ? "var(--text-secondary)"
                      : m.threshold_status === "green"
                      ? "var(--success)"
                      : m.threshold_status === "yellow"
                      ? "var(--warning)"
                      : "var(--danger)",
                }}
              >
                {m.relative_change_pct != null
                  ? `${m.relative_change_pct > 0 ? "+" : ""}${m.relative_change_pct.toFixed(1)}%`
                  : "—"}
              </td>
              <td style={{ padding: "6px 8px" }}>
                <StatusPill status={m.threshold_status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}

export default function MonitoringPage() {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  const [latest, setLatest] = useState<MonitoringRun | null>(null);
  const [modelMetrics, setModelMetrics] = useState<MetricRow[]>([]);
  const [dataMetrics, setDataMetrics] = useState<MetricRow[]>([]);
  const [runs, setRuns] = useState<MonitoringRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    const [latestR, modelR, dataR, runsR] = await Promise.all([
      fetch(`${base}/api/monitoring/latest`).then((r) => r.json()),
      fetch(`${base}/api/monitoring/model`).then((r) => r.json()),
      fetch(`${base}/api/monitoring/data`).then((r) => r.json()),
      fetch(`${base}/api/monitoring/runs`).then((r) => r.json()),
    ]);
    setLatest(latestR.latest_run || null);
    setModelMetrics(modelR.metrics || []);
    setDataMetrics(dataR.metrics || []);
    setRuns(runsR.runs || []);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function runMonitoring() {
    setRunning(true);
    setError("");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const apiKey = getStoredApiKey();
    if (apiKey) headers["X-DemandOS-API-Key"] = apiKey;
    try {
      const r = await fetch(`${base}/api/monitoring/run`, { method: "POST", headers });
      if (!r.ok) {
        const d = await r.json();
        setError(d.detail || "Run failed");
      } else {
        await load();
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Model monitoring"
        subtitle="Compare the latest model and data-health signals with the previous completed monitoring run."
        badge="Computed comparisons · no alerts sent"
      />
      <div className="notice notice-info" style={{ marginBottom: "20px" }}>
        Green means change is within 10%; yellow is 10–25%; red is above 25%.
        Unknown means there is no prior run available for comparison.
      </div>
      <ApiKeyInput />

      {/* Latest run summary */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "20px",
          marginBottom: "20px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "12px" }}>
              Latest Monitoring Run
            </div>
            {loading ? (
              <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Loading…</p>
            ) : !latest ? (
              <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                No monitoring runs yet. Click "Run Monitoring" to start.
              </p>
            ) : (
              <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", fontSize: "13px" }}>
                <div>
                  Overall: <StatusPill status={latest.overall_status} />
                </div>
                <div>
                  Model: <StatusPill status={latest.model_health_status} />
                </div>
                <div>
                  Data: <StatusPill status={latest.data_health_status} />
                </div>
                <div style={{ color: "var(--text-secondary)" }}>
                  {latest.started_at ? new Date(latest.started_at).toLocaleString() : ""}
                </div>
              </div>
            )}
          </div>

          <div>
            <button
              onClick={runMonitoring}
              disabled={running}
              className="button-primary"
            >
              {running ? "Running…" : "Run Monitoring"}
            </button>
          </div>
        </div>

        {error && (
          <div className="notice notice-danger" style={{ marginTop: "12px" }}>{error}</div>
        )}
      </div>

      {/* Threshold legend */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "12px 16px",
          marginBottom: "20px",
          fontSize: "12px",
          display: "flex",
          gap: "20px",
          flexWrap: "wrap",
        }}
      >
        <span style={{ color: "var(--success)" }}>● Green: change ≤ 10%</span>
        <span style={{ color: "var(--warning)" }}>● Yellow: 10–25%</span>
        <span style={{ color: "var(--danger)" }}>● Red: &gt; 25%</span>
        <span style={{ color: "var(--text-secondary)" }}>○ Unknown: no baseline</span>
      </div>

      <MetricTable metrics={modelMetrics} title="Model Performance Metrics" />
      <MetricTable metrics={dataMetrics} title="Data Distribution Metrics" />

      {/* Run history */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "16px",
        }}
      >
        <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "12px" }}>Run History</div>
        {runs.length === 0 ? (
          <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>No runs yet.</p>
        ) : (
          <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Run ID</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Status</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Overall</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Started</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "6px 8px", fontFamily: "monospace", fontSize: "11px" }}>
                    {r.run_id}
                  </td>
                  <td style={{ padding: "6px 8px" }}>{r.status}</td>
                  <td style={{ padding: "6px 8px" }}>
                    <StatusPill status={r.overall_status} />
                  </td>
                  <td style={{ padding: "6px 8px", color: "var(--text-secondary)" }}>
                    {r.started_at ? new Date(r.started_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  );
}
