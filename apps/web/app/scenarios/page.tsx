"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import ApiKeyInput from "@/components/ApiKeyInput";
import StatusBadge from "@/components/StatusBadge";
import { getStoredApiKey } from "@/lib/apiKey";

interface ScenarioInputs {
  demand_multiplier: number;
  lead_time_multiplier: number;
  supplier_reliability_delta: number;
  promotion_lift_multiplier: number;
  inventory_adjustment_units: number;
  horizon_days: number;
}

interface ScenarioSummary {
  total_product_stores: number;
  high_risk_count: number;
  critical_risk_count: number;
  total_lost_sales_estimate: number;
  total_order_cost_estimate: number;
}

interface ScenarioRun {
  scenario_id: string;
  status: string;
  inputs: ScenarioInputs;
  baseline_summary: ScenarioSummary;
  scenario_summary: ScenarioSummary;
  delta_lost_sales: number | null;
  delta_order_cost: number | null;
  delta_high_risk_count: number | null;
  delta_critical_risk_count: number | null;
  top_impacted_product_stores: ScenarioImpact[];
  created_at: string | null;
  simulated: boolean;
}

interface ScenarioImpact {
  product_id?: string;
  store_id?: string;
  baseline_risk_tier?: string;
  scenario_risk_tier?: string;
}

const HORIZON_OPTIONS = [7, 14, 28, 56, 90];

function DeltaCell({ value }: { value: number | null }) {
  if (value == null) return <td style={{ padding: "6px 8px" }}>—</td>;
  const color = value > 0 ? "var(--danger)" : value < 0 ? "var(--success)" : "var(--text-secondary)";
  const prefix = value > 0 ? "+" : "";
  return (
    <td style={{ padding: "6px 8px", color, fontWeight: 600 }}>
      {prefix}{value.toFixed(2)}
    </td>
  );
}

function fmt(n: number | undefined | null): string {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export default function ScenariosPage() {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "";

  const [inputs, setInputs] = useState<ScenarioInputs>({
    demand_multiplier: 1.0,
    lead_time_multiplier: 1.0,
    supplier_reliability_delta: 0.0,
    promotion_lift_multiplier: 1.0,
    inventory_adjustment_units: 0.0,
    horizon_days: 28,
  });

  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [latest, setLatest] = useState<ScenarioRun | null>(null);
  const [runs, setRuns] = useState<ScenarioRun[]>([]);

  async function load() {
    const [latestR, runsR] = await Promise.all([
      fetch(`${base}/api/scenarios/runs/latest`).then((r) => r.json()),
      fetch(`${base}/api/scenarios/runs`).then((r) => r.json()),
    ]);
    setLatest(latestR.latest_run || null);
    setRuns(runsR.runs || []);
  }

  useEffect(() => { load(); }, []);

  async function runScenario() {
    setRunning(true);
    setError("");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const apiKey = getStoredApiKey();
    if (apiKey) headers["X-DemandOS-API-Key"] = apiKey;
    try {
      const r = await fetch(`${base}/api/scenarios/run`, {
        method: "POST",
        headers,
        body: JSON.stringify(inputs),
      });
      const d = await r.json();
      if (!r.ok) {
        setError(typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail));
      } else {
        setLatest(d);
        await load();
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setRunning(false);
    }
  }

  function inputRow(
    label: string,
    key: keyof ScenarioInputs,
    min: number,
    max: number,
    step: number,
    hint: string
  ) {
    return (
      <div style={{ marginBottom: "12px" }}>
        <label style={{ fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "4px" }}>
          {label}
        </label>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={inputs[key] as number}
            onChange={(e) =>
              setInputs({ ...inputs, [key]: parseFloat(e.target.value) })
            }
            style={{ width: "180px" }}
          />
          <input
            type="number"
            min={min}
            max={max}
            step={step}
            value={inputs[key] as number}
            onChange={(e) =>
              setInputs({ ...inputs, [key]: parseFloat(e.target.value) || 0 })
            }
            style={{
              width: "80px",
              padding: "4px 8px",
              borderRadius: "4px",
              border: "1px solid var(--border)",
              background: "var(--surface-2)",
              color: "var(--text-primary)",
              fontSize: "13px",
            }}
          />
          <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{hint}</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Scenarios"
        subtitle="What happens if demand, lead time, or inventory changes?"
        badge="Simulated only · no real data modified"
      />
      <div className="notice notice-warning" style={{ marginBottom: "20px" }}>
        Scenario outputs are <strong>simulated only</strong>. They are stored separately for comparison only. They never mutate
        operational tables or trigger purchasing actions. Results are for planning exploration — not operational decisions.
      </div>
      <ApiKeyInput />

      <div className="two-column-grid" style={{ marginBottom: "20px" }}>
        {/* Scenario inputs */}
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "20px",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "12px" }}>
            Scenario Parameters
          </div>

          {/* Preset chips */}
          <div style={{ marginBottom: "16px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Demand change
            </div>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "10px" }}>
              {[0.8, 0.9, 1.0, 1.1, 1.2].map((v) => (
                <button
                  key={v}
                  onClick={() => setInputs((prev) => ({ ...prev, demand_multiplier: v }))}
                  style={{
                    padding: "4px 12px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    cursor: "pointer",
                    border: inputs.demand_multiplier === v ? "1px solid var(--accent)" : "1px solid var(--border)",
                    background: inputs.demand_multiplier === v ? "var(--accent-soft)" : "var(--surface)",
                    color: inputs.demand_multiplier === v ? "var(--accent)" : "var(--text-secondary)",
                    fontWeight: inputs.demand_multiplier === v ? 600 : 400,
                  }}
                >
                  {v === 1.0 ? "Base" : v < 1.0 ? `−${Math.round((1 - v) * 100)}%` : `+${Math.round((v - 1) * 100)}%`}
                </button>
              ))}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Supplier lead time
            </div>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "10px" }}>
              {[1.0, 1.25, 1.5].map((v) => (
                <button
                  key={v}
                  onClick={() => setInputs((prev) => ({ ...prev, lead_time_multiplier: v }))}
                  style={{
                    padding: "4px 12px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    cursor: "pointer",
                    border: inputs.lead_time_multiplier === v ? "1px solid var(--accent)" : "1px solid var(--border)",
                    background: inputs.lead_time_multiplier === v ? "var(--accent-soft)" : "var(--surface)",
                    color: inputs.lead_time_multiplier === v ? "var(--accent)" : "var(--text-secondary)",
                    fontWeight: inputs.lead_time_multiplier === v ? 600 : 400,
                  }}
                >
                  {v === 1.0 ? "Normal" : `+${Math.round((v - 1) * 100)}%`}
                </button>
              ))}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "6px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Inventory adjustment
            </div>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "14px" }}>
              {[0, -50, 50].map((v) => (
                <button
                  key={v}
                  onClick={() => setInputs((prev) => ({ ...prev, inventory_adjustment_units: v }))}
                  style={{
                    padding: "4px 12px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    cursor: "pointer",
                    border: inputs.inventory_adjustment_units === v ? "1px solid var(--accent)" : "1px solid var(--border)",
                    background: inputs.inventory_adjustment_units === v ? "var(--accent-soft)" : "var(--surface)",
                    color: inputs.inventory_adjustment_units === v ? "var(--accent)" : "var(--text-secondary)",
                    fontWeight: inputs.inventory_adjustment_units === v ? 600 : 400,
                  }}
                >
                  {v === 0 ? "Current" : v > 0 ? `+${v} units` : `${v} units`}
                </button>
              ))}
            </div>
          </div>

          <div style={{ borderTop: "1px solid var(--border)", paddingTop: "14px", marginBottom: "4px", fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Fine-tune
          </div>

          {inputRow("Demand Multiplier", "demand_multiplier", 0.5, 2.0, 0.05, "0.5×–2.0×")}
          {inputRow("Lead Time Multiplier", "lead_time_multiplier", 0.5, 2.0, 0.05, "0.5×–2.0×")}
          {inputRow(
            "Supplier Reliability Delta",
            "supplier_reliability_delta",
            -0.3,
            0.3,
            0.05,
            "−0.3 to +0.3"
          )}
          {inputRow(
            "Promotion Lift Multiplier",
            "promotion_lift_multiplier",
            0.5,
            2.0,
            0.05,
            "0.5×–2.0×"
          )}
          {inputRow(
            "Inventory Adjustment (units)",
            "inventory_adjustment_units",
            -1000,
            1000,
            10,
            "−1000 to +1000"
          )}

          <div style={{ marginBottom: "16px" }}>
            <label style={{ fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "4px" }}>
              Horizon Days
            </label>
            <select
              value={inputs.horizon_days}
              onChange={(e) => setInputs({ ...inputs, horizon_days: parseInt(e.target.value) })}
              style={{
                padding: "6px 10px",
                borderRadius: "4px",
                border: "1px solid var(--border)",
                background: "var(--surface-2)",
                color: "var(--text-primary)",
                fontSize: "13px",
              }}
            >
              {HORIZON_OPTIONS.map((h) => (
                <option key={h} value={h}>
                  {h} days
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={runScenario}
            disabled={running}
            className="button-primary"
          >
            {running ? "Running…" : "Run Scenario"}
          </button>

          {error && (
            <div className="notice notice-danger" style={{ marginTop: "12px" }}>{error}</div>
          )}
        </div>

        {/* Latest result */}
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "20px",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "16px" }}>
            Latest Scenario Result
          </div>

          {!latest ? (
            <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              No scenario run yet.
            </p>
          ) : (
            <>
              <div className="simulated-label" style={{ marginBottom: "12px" }}>
                Simulated output
              </div>

              <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <th style={{ textAlign: "left", padding: "4px 6px" }}>Metric</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Baseline</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Scenario</th>
                    <th style={{ textAlign: "right", padding: "4px 6px" }}>Delta</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "4px 6px" }}>High risk count</td>
                    <td style={{ textAlign: "right", padding: "4px 6px" }}>
                      {fmt(latest.baseline_summary?.high_risk_count)}
                    </td>
                    <td style={{ textAlign: "right", padding: "4px 6px" }}>
                      {fmt(latest.scenario_summary?.high_risk_count)}
                    </td>
                    <DeltaCell value={latest.delta_high_risk_count ?? null} />
                  </tr>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "4px 6px" }}>Critical risk count</td>
                    <td style={{ textAlign: "right", padding: "4px 6px" }}>
                      {fmt(latest.baseline_summary?.critical_risk_count)}
                    </td>
                    <td style={{ textAlign: "right", padding: "4px 6px" }}>
                      {fmt(latest.scenario_summary?.critical_risk_count)}
                    </td>
                    <DeltaCell value={latest.delta_critical_risk_count ?? null} />
                  </tr>
                  <tr>
                    <td style={{ padding: "4px 6px" }}>Est. lost sales</td>
                    <td style={{ textAlign: "right", padding: "4px 6px" }}>
                      ${fmt(latest.baseline_summary?.total_lost_sales_estimate)}
                    </td>
                    <td style={{ textAlign: "right", padding: "4px 6px" }}>
                      ${fmt(latest.scenario_summary?.total_lost_sales_estimate)}
                    </td>
                    <DeltaCell value={latest.delta_lost_sales ?? null} />
                  </tr>
                </tbody>
              </table>

              {latest.top_impacted_product_stores?.length > 0 && (
                <div style={{ marginTop: "16px" }}>
                  <div style={{ fontWeight: 600, fontSize: "12px", marginBottom: "6px" }}>
                    Top Impacted
                  </div>
                  <table style={{ width: "100%", fontSize: "11px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--border)" }}>
                        <th style={{ textAlign: "left", padding: "3px 6px" }}>Product</th>
                        <th style={{ textAlign: "left", padding: "3px 6px" }}>Store</th>
                        <th style={{ textAlign: "left", padding: "3px 6px" }}>Baseline</th>
                        <th style={{ textAlign: "left", padding: "3px 6px" }}>Scenario</th>
                      </tr>
                    </thead>
                    <tbody>
                      {latest.top_impacted_product_stores.slice(0, 5).map((row, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "3px 6px", fontFamily: "monospace" }}>
                            {row.product_id?.slice(0, 12)}…
                          </td>
                          <td style={{ padding: "3px 6px", fontFamily: "monospace" }}>
                            {row.store_id?.slice(0, 10)}…
                          </td>
                          <td style={{ padding: "3px 6px" }}><StatusBadge value={row.baseline_risk_tier} /></td>
                          <td style={{ padding: "3px 6px" }}><StatusBadge value={row.scenario_risk_tier} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Run history */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "16px",
        }}
      >
        <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "12px" }}>Scenario History</div>
        {runs.length === 0 ? (
          <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>No scenarios run yet.</p>
        ) : (
          <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>ID</th>
                <th style={{ textAlign: "right", padding: "6px 8px" }}>Δ High Risk</th>
                <th style={{ textAlign: "right", padding: "6px 8px" }}>Δ Critical</th>
                <th style={{ textAlign: "right", padding: "6px 8px" }}>Δ Lost Sales</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.scenario_id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "6px 8px", fontFamily: "monospace", fontSize: "11px" }}>
                    {r.scenario_id?.slice(0, 20)}…
                  </td>
                  <td style={{ textAlign: "right", padding: "6px 8px" }}>
                    {r.delta_high_risk_count != null
                      ? `${r.delta_high_risk_count > 0 ? "+" : ""}${r.delta_high_risk_count}`
                      : "—"}
                  </td>
                  <td style={{ textAlign: "right", padding: "6px 8px" }}>
                    {r.delta_critical_risk_count != null
                      ? `${r.delta_critical_risk_count > 0 ? "+" : ""}${r.delta_critical_risk_count}`
                      : "—"}
                  </td>
                  <td style={{ textAlign: "right", padding: "6px 8px" }}>
                    {r.delta_lost_sales != null
                      ? `$${r.delta_lost_sales > 0 ? "+" : ""}${r.delta_lost_sales.toFixed(0)}`
                      : "—"}
                  </td>
                  <td style={{ padding: "6px 8px", color: "var(--text-secondary)" }}>
                    {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
