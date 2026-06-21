"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  getDashboardPipelineStatus,
  runDemoReset,
  runAggregation,
  runFeatureBuild,
  runBaselineForecast,
  runModelTrain,
  runPlanningForecast,
  runStockoutRisk,
  runRecommendations,
  runFullDemoPipeline,
  getLatestDemoPipelineRun,
} from "@/lib/api";
import type {
  DashboardPipelineStatusResponse,
  DemoPipelineRunRecord,
  DemoPipelineStepRecord,
} from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import PipelineControlButton from "@/components/PipelineControlButton";
import ApiKeyInput from "@/components/ApiKeyInput";
import StatusBadge from "@/components/StatusBadge";
import PageHeader from "@/components/PageHeader";

type RunFn = () => Promise<unknown>;

const STEPS: Array<{
  step: string;
  label: string;
  fn: RunFn;
  confirmMessage?: string;
}> = [
  {
    step: "reset_demo",
    label: "Reset Demo Data",
    fn: runDemoReset,
    confirmMessage:
      "This will DELETE all existing data and regenerate the demo dataset from scratch. Continue?",
  },
  { step: "aggregation", label: "Run Aggregation", fn: runAggregation },
  { step: "features", label: "Build Features", fn: runFeatureBuild },
  { step: "baseline_forecast", label: "Run Baseline Forecast", fn: runBaselineForecast },
  { step: "train_ml", label: "Train ML Model", fn: runModelTrain },
  { step: "planning_forecast", label: "Run Planning Forecast", fn: runPlanningForecast },
  { step: "stockout_risk", label: "Run Stockout Risk", fn: runStockoutRisk },
  { step: "recommendations", label: "Run Recommendations", fn: runRecommendations },
];

const PAGE_LINKS: Record<string, { href: string; label: string }> = {
  baseline_forecast: { href: "/forecasts", label: "View Forecasts" },
  train_ml: { href: "/model-performance", label: "View Model" },
  planning_forecast: { href: "/forecasts", label: "View Forecasts" },
  stockout_risk: { href: "/risks", label: "View Risks" },
  recommendations: { href: "/recommendations", label: "View Recommendations" },
};

type StepResult = { result?: string; error?: string };

function stepStatusColor(status: string): string {
  switch (status) {
    case "completed": return "#15803d";
    case "failed": return "#dc2626";
    case "running": return "#2563eb";
    case "skipped": return "#9ca3af";
    default: return "var(--text-secondary)";
  }
}

function StepStatusIcon({ status }: { status: string }) {
  const icons: Record<string, string> = {
    completed: "✓",
    failed: "✗",
    running: "▶",
    skipped: "—",
    pending: "○",
  };
  return (
    <span style={{ color: stepStatusColor(status), fontWeight: 700, width: "16px", display: "inline-block" }}>
      {icons[status] ?? "○"}
    </span>
  );
}

function DurableRunPanel({ run }: { run: DemoPipelineRunRecord }) {
  const durationSecs = run.started_at && run.completed_at
    ? Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000)
    : null;

  return (
    <div
      style={{
        background: "var(--surface)",
        border: `1px solid ${run.status === "completed" ? "#15803d44" : run.status === "failed" ? "#dc262644" : "var(--border)"}`,
        borderRadius: "8px",
        padding: "16px",
        marginBottom: "16px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
        <StatusBadge value={run.status} />
        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
          {run.started_at ? new Date(run.started_at).toLocaleString() : ""}
          {durationSecs !== null ? ` · ${durationSecs}s` : ""}
        </span>
        <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontFamily: "monospace" }}>
          {run.run_id.slice(0, 8)}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {run.steps.map((step: DemoPipelineStepRecord) => (
          <div key={step.step_name} style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
            <StepStatusIcon status={step.status} />
            <div style={{ flex: 1 }}>
              <span style={{ fontSize: "12px", fontWeight: 500 }}>{step.step_label}</span>
              {step.result_summary && step.status === "completed" && (
                <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginLeft: "8px" }}>
                  {step.result_summary}
                </span>
              )}
              {step.error_message && step.status === "failed" && (
                <div style={{ fontSize: "11px", color: "#dc2626", marginTop: "2px" }}>
                  {step.error_message}
                </div>
              )}
            </div>
            {step.status === "completed" && PAGE_LINKS[step.step_name] && (
              <Link
                href={PAGE_LINKS[step.step_name].href}
                style={{ fontSize: "11px", color: "var(--accent)", textDecoration: "none" }}
              >
                {PAGE_LINKS[step.step_name].label} →
              </Link>
            )}
          </div>
        ))}
      </div>

      {run.error_message && (
        <div style={{ marginTop: "10px", fontSize: "11px", color: "#dc2626", padding: "8px", background: "#fef2f2", borderRadius: "4px" }}>
          {run.error_message}
        </div>
      )}
    </div>
  );
}

export default function PipelinePage() {
  const [pipelineStatus, setPipelineStatus] =
    useState<DashboardPipelineStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [latestRun, setLatestRun] = useState<DemoPipelineRunRecord | null>(null);
  const [latestRunLoading, setLatestRunLoading] = useState(true);

  const [runningStep, setRunningStep] = useState<string | null>(null);
  const [stepResults, setStepResults] = useState<Record<string, StepResult>>({});

  const [fullPipelineRunning, setFullPipelineRunning] = useState(false);
  const [liveLog, setLiveLog] = useState<string[]>([]);
  const [liveRun, setLiveRun] = useState<DemoPipelineRunRecord | null>(null);

  const loadStatus = useCallback(() => {
    setStatusLoading(true);
    setStatusError(null);
    getDashboardPipelineStatus()
      .then(setPipelineStatus)
      .catch((e) => setStatusError(e.message))
      .finally(() => setStatusLoading(false));
  }, []);

  const loadLatestRun = useCallback(() => {
    setLatestRunLoading(true);
    getLatestDemoPipelineRun()
      .then((resp) => setLatestRun(resp.run))
      .catch(() => setLatestRun(null))
      .finally(() => setLatestRunLoading(false));
  }, []);

  useEffect(() => {
    loadStatus();
    loadLatestRun();
  }, [loadStatus, loadLatestRun]);

  const getStepStatus = (step: string) =>
    pipelineStatus?.steps.find((s) => s.step === step)?.status ?? "not_run";

  const handleRun = async (step: string, fn: RunFn, confirmMessage?: string) => {
    if (confirmMessage && !window.confirm(confirmMessage)) return;

    setRunningStep(step);
    setStepResults((prev) => ({ ...prev, [step]: {} }));

    try {
      const res = (await fn()) as Record<string, unknown>;
      const summary =
        (res?.message as string) ??
        (res?.status as string) ??
        JSON.stringify(res).slice(0, 200);
      setStepResults((prev) => ({ ...prev, [step]: { result: summary } }));
    } catch (e) {
      setStepResults((prev) => ({
        ...prev,
        [step]: { error: e instanceof Error ? e.message : String(e) },
      }));
    } finally {
      setRunningStep(null);
      getDashboardPipelineStatus().then(setPipelineStatus).catch(() => {});
    }
  };

  const handleFullPipeline = async () => {
    if (
      !window.confirm(
        "This will run the FULL demo pipeline:\n" +
          "Reset → Aggregation → Features → Baseline → ML Train → Planning → Risk → Recommendations\n\n" +
          "All existing data will be reset. Continue?"
      )
    )
      return;

    setFullPipelineRunning(true);
    setLiveLog([]);
    setLiveRun(null);

    const log = (msg: string) =>
      setLiveLog((prev) => [...prev, msg]);

    log("▶ Starting full demo pipeline…");

    try {
      const result = await runFullDemoPipeline({
        seed: 42,
        product_count: 50,
        store_count: 5,
        history_days: 730,
      });

      setLiveRun(result.run);

      if (result.status === "completed") {
        log("✓ Full pipeline complete.");
      } else {
        log(`✗ Pipeline stopped: ${result.message}`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      log(`✗ Pipeline failed: ${msg}`);
    } finally {
      setFullPipelineRunning(false);
      getDashboardPipelineStatus().then(setPipelineStatus).catch(() => {});
      loadLatestRun();
    }
  };

  return (
    <div>
      <PageHeader
        title="Pipeline controls"
        subtitle="Run the deterministic demo workflow end to end or execute individual stages with durable status tracking."
        badge="Protected writes · no external side effects"
      />

      <ApiKeyInput />

      {statusLoading && <LoadingState />}
      {statusError && (
        <ErrorState message={statusError} onRetry={loadStatus} />
      )}

      {!statusLoading && (
        <>
          {/* Full pipeline button */}
          <section style={{ marginBottom: "32px" }}>
            <h2
              style={{
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "12px",
              }}
            >
              Run Full Demo Pipeline
            </h2>
            <div
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "20px",
              }}
            >
              <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "16px" }}>
                Executes all 8 stages in sequence: Reset → Aggregation → Features →
                Baseline Forecast → ML Training → Planning Forecast → Stockout Risk →
                Recommendations. Stops on the first failure. Resets all demo data.
                A durable run record is saved and shown below.
              </p>
              <button
                onClick={handleFullPipeline}
                disabled={fullPipelineRunning || runningStep !== null}
                style={{
                  padding: "8px 24px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: 700,
                  cursor:
                    fullPipelineRunning || runningStep !== null ? "not-allowed" : "pointer",
                  border: "1px solid var(--accent)",
                  background:
                    fullPipelineRunning || runningStep !== null
                      ? "var(--surface-2)"
                      : "var(--accent)",
                  color:
                    fullPipelineRunning || runningStep !== null ? "var(--text-secondary)" : "#fff",
                  opacity: fullPipelineRunning || runningStep !== null ? 0.6 : 1,
                }}
              >
                {fullPipelineRunning ? "Running…" : "Run Full Demo Pipeline"}
              </button>

              {/* Live log */}
              {liveLog.length > 0 && (
                <div
                  style={{
                    marginTop: "16px",
                    padding: "12px",
                    background: "var(--surface-2)",
                    borderRadius: "6px",
                    fontFamily: "monospace",
                    fontSize: "11px",
                    color: "var(--text-primary)",
                    maxHeight: "120px",
                    overflowY: "auto",
                    lineHeight: 1.7,
                  }}
                >
                  {liveLog.map((line, i) => (
                    <div
                      key={i}
                      style={{
                        color: line.includes("✗")
                          ? "#dc2626"
                          : line.includes("✓")
                          ? "#15803d"
                          : "var(--text-secondary)",
                      }}
                    >
                      {line}
                    </div>
                  ))}
                </div>
              )}

              {/* Live run steps */}
              {liveRun && (
                <div style={{ marginTop: "16px" }}>
                  <DurableRunPanel run={liveRun} />
                </div>
              )}
            </div>
          </section>

          {/* Latest durable run */}
          <section style={{ marginBottom: "32px" }}>
            <h2
              style={{
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "12px",
              }}
            >
              Latest Pipeline Run
            </h2>
            {latestRunLoading ? (
              <LoadingState />
            ) : latestRun ? (
              <DurableRunPanel run={latestRun} />
            ) : (
              <div
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "20px",
                  textAlign: "center",
                  color: "var(--text-secondary)",
                  fontSize: "13px",
                }}
              >
                No pipeline runs yet. Click &ldquo;Run Full Demo Pipeline&rdquo; above to start.
              </div>
            )}
          </section>

          {/* Individual step controls */}
          <section style={{ marginBottom: "32px" }}>
            <h2
              style={{
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "12px",
              }}
            >
              Individual Pipeline Steps
            </h2>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "12px" }}>
              Run pipeline stages individually for debugging or partial updates.
            </p>
            {STEPS.map(({ step, label, fn, confirmMessage }) => {
              const sr = stepResults[step] ?? {};
              return (
                <PipelineControlButton
                  key={step}
                  label={label}
                  status={getStepStatus(step)}
                  running={runningStep === step}
                  disabled={fullPipelineRunning || (runningStep !== null && runningStep !== step)}
                  onRun={() => handleRun(step, fn, confirmMessage)}
                  result={sr.result}
                  error={sr.error}
                />
              );
            })}
          </section>

          {/* Quick navigation */}
          <section>
            <h2
              style={{
                fontSize: "14px",
                fontWeight: 600,
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                marginBottom: "12px",
              }}
            >
              Explore Results
            </h2>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {[
                { href: "/forecasts", label: "Forecasts" },
                { href: "/risks", label: "Risk Queue" },
                { href: "/recommendations", label: "Recommendations" },
                { href: "/model-performance", label: "Model Performance" },
                { href: "/data-health", label: "Data Health" },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  style={{
                    padding: "6px 14px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: 500,
                    border: "1px solid var(--border)",
                    background: "var(--surface)",
                    color: "var(--text-primary)",
                    textDecoration: "none",
                  }}
                >
                  {label} →
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
