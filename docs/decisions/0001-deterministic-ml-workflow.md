# ADR 0001 — Deterministic ML Workflow, Not Agentic System

## Status
Accepted

## Context

DemandOS needs to compute demand forecasts and inventory risk scores reliably
and reproducibly. Two architectural approaches were considered:

**Option A — Agentic / LLM-driven system:**
An AI agent decides when to retrain, what features to use, how to handle anomalies,
and what recommendations to make. The agent adapts dynamically.

**Option B — Deterministic pipeline:**
A fixed sequence of steps: ingest → validate → aggregate → feature engineer →
forecast → risk score → recommend. Each step is code, not an agent. Configuration
changes the pipeline; code changes change behavior.

## Decision

DemandOS uses Option B: a deterministic, code-defined ML pipeline.

## Rationale

1. **Reproducibility**: given the same input data, the same code version produces
   the same outputs. This is essential for debugging, auditing, and regulatory compliance.

2. **Testability**: each pipeline stage is a function with clear inputs and outputs.
   Unit tests and integration tests are straightforward.

3. **Debuggability**: when a forecast is wrong, we can trace exactly which feature
   values, which training data, and which model version produced it.

4. **Safety**: inventory reorder recommendations affect real purchasing decisions.
   A deterministic system with human approval gates is safer than an agent that
   might autonomously decide to expand its own scope.

5. **Cost**: LLM inference per forecast would be expensive and slow at scale
   (50 SKUs × 5 stores × 28 days = 7,000 inference calls per run).

6. **Accuracy**: LightGBM trained on historical demand data outperforms LLM-based
   point forecasts for structured time-series data.

## Consequences

- The pipeline is less flexible in adapting to unexpected data shapes.
- Adding new features requires code changes, not prompt changes.
- Claude Code (AI assistant) is used to write and modify the pipeline code,
  not to run as an agent inside the pipeline at inference time.

## Non-Negotiable Implication

Connectors must supply raw operational records only.
The pipeline computes all derived values.
This rule must never be violated to "speed up" development.
