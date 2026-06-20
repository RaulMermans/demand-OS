"use client";

import { useCallback, useEffect, useState } from "react";
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
} from "@/lib/api";
import type { DashboardPipelineStatusResponse } from "@/lib/types";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import PipelineControlButton from "@/components/PipelineControlButton";
import ApiKeyInput from "@/components/ApiKeyInput";

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

type StepResult = { result?: string; error?: string };

export default function PipelinePage() {
  const [pipelineStatus, setPipelineStatus] =
    useState<DashboardPipelineStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [runningStep, setRunningStep] = useState<string | null>(null);
  const [stepResults, setStepResults] = useState<Record<string, StepResult>>({});

  const [fullPipelineRunning, setFullPipelineRunning] = useState(false);
  const [fullPipelineLog, setFullPipelineLog] = useState<string[]>([]);

  const loadStatus = useCallback(() => {
    setStatusLoading(true);
    setStatusError(null);
    getDashboardPipelineStatus()
      .then(setPipelineStatus)
      .catch((e) => setStatusError(e.message))
      .finally(() => setStatusLoading(false));
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

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
      // Refresh pipeline status
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
    setFullPipelineLog([]);

    const log = (msg: string) =>
      setFullPipelineLog((prev) => [...prev, msg]);

    const steps: Array<{ label: string; fn: RunFn }> = [
      { label: "Reset Demo Data", fn: runDemoReset },
      { label: "Aggregation", fn: runAggregation },
      { label: "Feature Build", fn: runFeatureBuild },
      { label: "Baseline Forecast", fn: runBaselineForecast },
      { label: "ML Model Training", fn: runModelTrain },
      { label: "Planning Forecast", fn: runPlanningForecast },
      { label: "Stockout Risk", fn: runStockoutRisk },
      { label: "Recommendations", fn: runRecommendations },
    ];

    for (const step of steps) {
      log(`▶ ${step.label}…`);
      try {
        const res = (await step.fn()) as Record<string, unknown>;
        const msg = (res?.message as string) ?? (res?.status as string) ?? "done";
        log(`  ✓ ${step.label}: ${msg}`);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        log(`  ✗ ${step.label} FAILED: ${msg}`);
        log("Pipeline stopped.");
        setFullPipelineRunning(false);
        getDashboardPipelineStatus().then(setPipelineStatus).catch(() => {});
        return;
      }
    }

    log("✓ Full pipeline complete.");
    setFullPipelineRunning(false);
    getDashboardPipelineStatus().then(setPipelineStatus).catch(() => {});
  };

  return (
    <div>
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "4px" }}>
        Pipeline Controls
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Manually trigger each pipeline stage. All actions are safe and internal — no
        purchase orders or external calls are made.
      </p>

      <ApiKeyInput />

      {statusLoading && <LoadingState />}
      {statusError && (
        <ErrorState message={statusError} onRetry={loadStatus} />
      )}

      {!statusLoading && (
        <>
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
              Pipeline Steps
            </h2>
            {STEPS.map(({ step, label, fn, confirmMessage }) => {
              const sr = stepResults[step] ?? {};
              return (
                <PipelineControlButton
                  key={step}
                  label={label}
                  status={getStepStatus(step)}
                  running={runningStep === step}
                  disabled={fullPipelineRunning || runningStep !== null && runningStep !== step}
                  onRun={() => handleRun(step, fn, confirmMessage)}
                  result={sr.result}
                  error={sr.error}
                />
              );
            })}
          </section>

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

              {fullPipelineLog.length > 0 && (
                <div
                  style={{
                    marginTop: "16px",
                    padding: "12px",
                    background: "var(--surface-2)",
                    borderRadius: "6px",
                    fontFamily: "monospace",
                    fontSize: "11px",
                    color: "var(--text-primary)",
                    maxHeight: "240px",
                    overflowY: "auto",
                    lineHeight: 1.7,
                  }}
                >
                  {fullPipelineLog.map((line, i) => (
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
            </div>
          </section>
        </>
      )}
    </div>
  );
}
