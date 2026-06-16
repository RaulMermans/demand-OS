# AGENTS.md — DemandOS Agent Guidelines

General guidance for all AI coding agents (Claude, Codex, Gemini, etc.) working in this repository.

---

## How to Work in This Repo

1. **Read CLAUDE.md first** — it contains non-negotiable rules.
2. **Read the relevant service file** before modifying it.
3. **Run tests before and after** every change: `cd apps/api && pytest`
4. **Update docs** when you change architecture or data contracts.
5. **Do not implement sprints ahead of schedule** without explicit instruction.

---

## Allowed Changes (Without Asking)

- Add or improve tests in `apps/api/tests/`
- Fix bugs in existing service implementations
- Add docstrings or inline comments to clarify non-obvious logic
- Update scaffold TODO comments to note sprint number or rationale
- Improve error messages and logging
- Fix TypeScript types in the frontend

## Changes That Require Explicit Instruction

- Adding new connector methods to `BaseCommerceConnector`
- Adding new fields to raw schemas in `schemas/raw.py`
- Adding new API endpoints
- Adding new dependencies to `pyproject.toml` or `package.json`
- Implementing a service that is currently a scaffold stub
- Changing the pipeline sequence
- Adding authentication or authorization logic
- Modifying database migrations

---

## Verification Commands

```bash
# Backend tests (always run after changes)
cd apps/api && pytest

# Verify raw data rule specifically
cd apps/api && pytest tests/test_raw_data_rule.py -v

# Verify connector contract
cd apps/api && pytest tests/test_connector_contract.py -v

# Full verification
bash scripts/verify.sh

# Frontend type check
cd apps/web && npm run type-check
```

---

## Coding Standards

**Python (backend):**
- Python 3.11+ type hints everywhere
- Pydantic v2 for all schemas
- SQLAlchemy 2.0 ORM style (no legacy patterns)
- FastAPI dependency injection via `Depends()`
- No raw SQL strings — use SQLAlchemy query builders
- No `print()` in production code — use `logging`

**TypeScript (frontend):**
- Strict TypeScript (`strict: true` in tsconfig)
- No `any` type without a comment explaining why
- API calls go through `lib/api.ts` only
- No hardcoded API URLs — use environment variables

**General:**
- Functions do one thing
- No function longer than 60 lines without strong justification
- No file longer than 300 lines without strong justification

---

## Testing Standards

- Use `pytest` for all backend tests
- Test file names: `test_<module_name>.py`
- Test function names: `test_<what_it_does>()`
- No test should hit a real external API
- No test should write to production DB
- Tests use SQLite in-memory or test fixtures

---

## Documentation Standards

- Code comments explain WHY, not WHAT
- Docstrings on public service methods
- Sprint TODOs formatted as: `# Sprint N TODO: description`
- Architecture changes → update `docs/architecture.md`
- Data contract changes → update `docs/data_contract.md`

---

## Do Not

- Introduce LLM/agent calls inside the ML pipeline (it's deterministic code, not agentic)
- Add real external API calls to stub connectors
- Store secrets or credentials anywhere in code or DB
- Create automatic purchase orders or send automated emails
- Add hardcoded business metrics to dashboard components
- Skip tests to "save time"
- Use deprecated SQLAlchemy 1.x patterns
- Implement features that belong to a future sprint without instruction
