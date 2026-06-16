# DemandOS — Observability Plan

## Pipeline Events

Every significant pipeline step emits a `PipelineEvent` row to the DB:
- event_type: ingestion_started, ingestion_completed, validation_error,
  aggregation_started, aggregation_completed, feature_computed,
  forecast_run_started, forecast_run_completed, stockout_computed, recommendation_generated
- severity: info / warning / error
- entity_type + entity_id: affected record
- message: human-readable description

## Ingestion Runs

Each ingestion attempt creates an `IngestionRun` row:
- connector name, start/end timestamps, record counts
- status: running / success / failed
- error_message if failed

## Logging Strategy

- Structured JSON logs via Python `logging` + optional structlog
- Log levels: INFO for normal pipeline steps, WARNING for data quality issues, ERROR for failures
- No PII or raw record values in logs (log IDs and counts only)
- Log retention: 30 days in dev, configurable in prod

## Metrics (Sprint 6+)

- Pipeline duration per stage (ingestion, aggregation, feature, forecast)
- Record counts per ingestion run
- Validation error rate (errors / records_checked)
- Forecast SMAPE per model version
- Stockout risk tier distribution over time

## Alerting (Sprint 6+)

Triggers:
- Ingestion failure (status=failed)
- Validation error rate > 5%
- Critical stockout risk detected (risk_tier=critical, not in recommendations)
- Model SMAPE > threshold (model degradation alert)

Channels (Sprint 7+): Slack webhook, email, PagerDuty
