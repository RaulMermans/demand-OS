# DemandOS Evals

See [docs/evals.md](docs/evals.md) for full evaluation plan per sprint.

## Current Test Coverage (Sprint 0)

| Test | Status |
|------|--------|
| `test_health.py` — health endpoint returns ok | ✅ |
| `test_health.py` — api/status returns scaffold_ready | ✅ |
| `test_health.py` — overview returns scaffold_ready | ✅ |
| `test_health.py` — data-health returns checks list | ✅ |
| `test_connector_contract.py` — all connectors have required methods | ✅ |
| `test_connector_contract.py` — mock connector returns lists | ✅ |
| `test_connector_contract.py` — csv connector raises NotImplementedError | ✅ |
| `test_connector_contract.py` — shopify connector raises NotImplementedError | ✅ |
| `test_raw_data_rule.py` — no forbidden derived fields in raw schemas | ✅ |
| `test_raw_data_rule.py` — all schemas have source_connector field | ✅ |
| `test_raw_data_rule.py` — all schemas have id field | ✅ |

## Run Evals

```bash
cd apps/api && pytest -v
```
