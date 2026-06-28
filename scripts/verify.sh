#!/usr/bin/env bash
# verify.sh — Run all available verification checks for DemandOS.
# Usage: bash scripts/verify.sh

set -e

echo "DemandOS — Verification"
echo "========================"
echo ""

PASS=0
FAIL=0
SKIP=0

# -------------------------------------------------------------------
# 1. Check required root files exist
# -------------------------------------------------------------------
echo "1. Checking required root files..."
ROOT_FILES=(
  "README.md" "CLAUDE.md" "AGENTS.md" "DESIGN.md" "ROADMAP.md"
  "EVALS.md" "SECURITY.md" "DATA_POLICY.md" ".gitignore"
  ".env.example" "docker-compose.yml"
)
for f in "${ROOT_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL += 1))
  fi
done

echo ""

# -------------------------------------------------------------------
# 2. Check required docs exist
# -------------------------------------------------------------------
echo "2. Checking docs/..."
DOC_FILES=(
  "docs/architecture.md" "docs/product.md" "docs/data_contract.md"
  "docs/ml_plan.md" "docs/sprint_plan.md" "docs/evals.md"
  "docs/observability.md" "docs/security.md" "docs/roadmap.md"
  "docs/case_study_notes.md" "docs/reference_repositories.md"
  "docs/decisions/0001-deterministic-ml-workflow.md"
  "docs/demo_runbook.md"
  "docs/operator_runbook.md"
  "docs/deployment.md"
  "docs/case_study.md"
  "docs/demo_script.md"
  "docs/final_qa_checklist.md"
  "docs/case_study_assets.md"
  "docs/screenshots/README.md"
  "docs/release_notes.md"
)
for f in "${DOC_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL += 1))
  fi
done

echo ""

# -------------------------------------------------------------------
# 3. Check backend structure
# -------------------------------------------------------------------
echo "3. Checking backend structure..."
BACKEND_FILES=(
  "apps/api/app/main.py"
  "apps/api/app/config.py"
  "apps/api/app/api/auth.py"
  "apps/api/app/db/models.py"
  "apps/api/app/connectors/base.py"
  "apps/api/app/connectors/mock_commerce.py"
  "apps/api/app/schemas/raw.py"
  "apps/api/app/schemas/derived.py"
  "apps/api/app/schemas/api.py"
  "apps/api/app/services/ingestion_service.py"
  "apps/api/app/services/aggregation_service.py"
  "apps/api/app/services/forecasting_service.py"
  "apps/api/app/services/training_service.py"
  "apps/api/app/services/stockout_service.py"
  "apps/api/app/services/recommendation_service.py"
  "apps/api/app/api/aggregation.py"
  "apps/api/app/services/feature_service.py"
  "apps/api/app/api/features.py"
  "apps/api/app/api/forecasts.py"
  "apps/api/app/api/models.py"
  "apps/api/app/api/metrics.py"
  "apps/api/app/api/dashboard.py"
  "apps/api/tests/test_health.py"
  "apps/api/tests/test_connector_contract.py"
  "apps/api/tests/test_raw_data_rule.py"
  "apps/api/tests/test_aggregation.py"
  "apps/api/tests/test_features.py"
  "apps/api/tests/test_forecasting.py"
  "apps/api/tests/test_training.py"
  "apps/api/tests/test_stockout.py"
  "apps/api/pyproject.toml"
  "scripts/build_canonical_tables.py"
  "scripts/build_features.py"
  "scripts/run_baseline_forecast.py"
  "scripts/train_model.py"
  "scripts/run_planning_forecast.py"
  "scripts/run_stockout_risk.py"
  "scripts/run_recommendations.py"
  "apps/api/tests/test_recommendations.py"
  "apps/api/tests/test_api_contracts.py"
  "apps/api/tests/test_alembic.py"
  "apps/api/tests/test_api_key_guard.py"
  "apps/api/tests/test_demo_pipeline.py"
  "apps/api/app/services/demo_pipeline_service.py"
  ".github/workflows/ci.yml"
  ".github/dependabot.yml"
  "apps/api/alembic.ini"
  "apps/api/alembic/env.py"
  "apps/api/alembic/script.py.mako"
)
for f in "${BACKEND_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL += 1))
  fi
done

echo ""

# -------------------------------------------------------------------
# 4. Run pytest
# -------------------------------------------------------------------
echo "4. Running pytest..."
cd apps/api

if command -v python3 &>/dev/null; then
  if python3 -c "import fastapi" 2>/dev/null; then
    if python3 -m pytest tests/ -v --tb=short; then
      echo ""
      echo "   ✅ All pytest tests passed"
      ((PASS += 1))
    else
      echo ""
      echo "   ❌ pytest tests FAILED"
      ((FAIL += 1))
    fi
  else
    echo "   ⚠️  SKIP — Python dependencies not installed."
    echo "   Run: cd apps/api && pip install -e '.[dev]'"
    ((SKIP += 1))
  fi
else
  echo "   ⚠️  SKIP — python3 not found."
  ((SKIP++))
fi

cd ../..
echo ""

# -------------------------------------------------------------------
# 5. Check frontend structure
# -------------------------------------------------------------------
echo "5. Checking frontend structure..."
FRONTEND_FILES=(
  "apps/web/package.json"
  "apps/web/tsconfig.json"
  "apps/web/next.config.js"
  "apps/web/app/layout.tsx"
  "apps/web/app/page.tsx"
  "apps/web/app/overview/page.tsx"
  "apps/web/app/forecasts/page.tsx"
  "apps/web/app/risks/page.tsx"
  "apps/web/app/recommendations/page.tsx"
  "apps/web/app/model-performance/page.tsx"
  "apps/web/app/data-health/page.tsx"
  "apps/web/app/pipeline/page.tsx"
  "apps/web/components/AppShell.tsx"
  "apps/web/components/LoadingState.tsx"
  "apps/web/components/ErrorState.tsx"
  "apps/web/components/EmptyState.tsx"
  "apps/web/components/StatusBadge.tsx"
  "apps/web/components/DataTable.tsx"
  "apps/web/components/KpiCard.tsx"
  "apps/web/components/ChartCard.tsx"
  "apps/web/components/BarChartPanel.tsx"
  "apps/web/components/LineChartPanel.tsx"
  "apps/web/components/PipelineControlButton.tsx"
  "apps/web/components/ApiKeyInput.tsx"
  "apps/web/components/PageHeader.tsx"
  "apps/web/lib/api.ts"
  "apps/web/lib/types.ts"
  "apps/web/lib/apiKey.ts"
  "apps/web/vercel.json"
  "apps/web/.env.example"
)
for f in "${FRONTEND_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL += 1))
  fi
done

echo ""

# -------------------------------------------------------------------
# 6. Check no forbidden derived fields in raw schema class bodies
# Greps for actual Pydantic field declarations (name: type) not comments/constants.
# Pytest test_raw_data_rule.py is the authoritative enforcement.
# -------------------------------------------------------------------
echo "6. Checking raw schema field declarations for derived fields..."
FORBIDDEN_FIELDS=(
  "lag_7d" "lag_14d" "lag_28d" "rolling_mean" "rolling_std"
  "predicted_units" "risk_score" "stockout_probability"
  "recommended_reorder" "safety_stock" "reorder_point" "economic_order_qty"
)
RAW_SCHEMA="apps/api/app/schemas/raw.py"
SCHEMA_CLEAN=true
for field in "${FORBIDDEN_FIELDS[@]}"; do
  # Match lines like "    lag_7d:" or "    lag_7d =" (actual field declarations)
  if grep -qE "^[[:space:]]+${field}[[:space:]]*[:=]" "$RAW_SCHEMA" 2>/dev/null; then
    echo "   ❌ FORBIDDEN field declaration found in $RAW_SCHEMA: $field"
    SCHEMA_CLEAN=false
    ((FAIL += 1))
  fi
done
if [ "$SCHEMA_CLEAN" = true ]; then
  echo "   ✅ No forbidden derived field declarations in raw schema"
  echo "   ℹ️  (Authoritative check: pytest tests/test_raw_data_rule.py)"
  ((PASS++))
fi

echo ""

# -------------------------------------------------------------------
# 7a. Sprint 10 — check full pipeline endpoint and env docs
# -------------------------------------------------------------------
echo "7a. Checking Sprint 10 additions..."

# Check full pipeline endpoint in demo.py
if grep -q "run-full-pipeline" apps/api/app/api/demo.py 2>/dev/null; then
  echo "   ✅ POST /api/demo/run-full-pipeline present in demo.py"
  ((PASS += 1))
else
  echo "   ❌ POST /api/demo/run-full-pipeline MISSING from demo.py"
  ((FAIL += 1))
fi

# Check DemoPipelineRun model
if grep -q "DemoPipelineRun" apps/api/app/db/models.py 2>/dev/null; then
  echo "   ✅ DemoPipelineRun model present in models.py"
  ((PASS += 1))
else
  echo "   ❌ DemoPipelineRun model MISSING from models.py"
  ((FAIL += 1))
fi

# Check pipeline page imports full pipeline function
if grep -q "runFullDemoPipeline\|run-full-pipeline" apps/web/app/pipeline/page.tsx 2>/dev/null; then
  echo "   ✅ Full demo pipeline control present in pipeline page"
  ((PASS += 1))
else
  echo "   ❌ Full demo pipeline control MISSING from pipeline page"
  ((FAIL += 1))
fi

# Check NEXT_PUBLIC_API_BASE_URL is documented
if grep -q "NEXT_PUBLIC_API_BASE_URL" apps/web/.env.example 2>/dev/null; then
  echo "   ✅ NEXT_PUBLIC_API_BASE_URL documented in apps/web/.env.example"
  ((PASS += 1))
else
  echo "   ❌ NEXT_PUBLIC_API_BASE_URL MISSING from apps/web/.env.example"
  ((FAIL += 1))
fi

# Check product drilldown page exists
if [ -f "apps/web/app/products/[productId]/page.tsx" ]; then
  echo "   ✅ Product drilldown page exists"
  ((PASS += 1))
else
  echo "   ❌ Product drilldown page MISSING"
  ((FAIL += 1))
fi

echo ""

# -------------------------------------------------------------------
# 7. Check Alembic migrations
# -------------------------------------------------------------------
echo "7. Checking Alembic migration files..."
if [ -d "apps/api/alembic/versions" ]; then
  MIGRATION_COUNT=$(find apps/api/alembic/versions -name "*.py" | wc -l | tr -d ' ')
  if [ "$MIGRATION_COUNT" -ge 1 ]; then
    echo "   ✅ alembic/versions/ has $MIGRATION_COUNT migration(s)"
    ((PASS += 1))
  else
    echo "   ❌ alembic/versions/ exists but contains no migration files"
    ((FAIL += 1))
  fi
else
  echo "   ❌ alembic/versions/ directory missing"
  ((FAIL += 1))
fi

echo ""

# -------------------------------------------------------------------
# 8. Sprint 10B — check single Vercel project deployment files
# -------------------------------------------------------------------
echo "8. Checking Sprint 10B Vercel deployment adapter..."

VERCEL_FILES=(
  "vercel.json"
  "requirements.txt"
  "api/index.py"
  "api/__init__.py"
)
for f in "${VERCEL_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING (required for single Vercel project mode)"
    ((FAIL += 1))
  fi
done

# vercel.json must contain /api route
if grep -q '"api/index.py"' vercel.json 2>/dev/null; then
  echo "   ✅ vercel.json routes /api/* to api/index.py"
  ((PASS += 1))
else
  echo "   ❌ vercel.json does not route to api/index.py"
  ((FAIL += 1))
fi

# api/index.py must import from app.main
if grep -q "from app.main import app" api/index.py 2>/dev/null; then
  echo "   ✅ api/index.py imports FastAPI app from app.main"
  ((PASS += 1))
else
  echo "   ❌ api/index.py does not import from app.main"
  ((FAIL += 1))
fi

# requirements.txt must list FastAPI, multipart upload, and Postgres runtime packages
if grep -q "fastapi" requirements.txt 2>/dev/null && \
   grep -q "python-multipart" requirements.txt 2>/dev/null && \
   grep -q "psycopg2" requirements.txt 2>/dev/null; then
  echo "   ✅ requirements.txt contains FastAPI, multipart, and Postgres runtime dependencies"
  ((PASS += 1))
else
  echo "   ❌ requirements.txt missing FastAPI, multipart, or Postgres runtime dependencies"
  ((FAIL += 1))
fi

# config.py must define runtime_mode and demo_scale
if grep -q "demandos_runtime_mode" apps/api/app/config.py 2>/dev/null && \
   grep -q "demandos_demo_scale" apps/api/app/config.py 2>/dev/null; then
  echo "   ✅ config.py defines DEMANDOS_RUNTIME_MODE and DEMANDOS_DEMO_SCALE"
  ((PASS += 1))
else
  echo "   ❌ config.py missing DEMANDOS_RUNTIME_MODE or DEMANDOS_DEMO_SCALE"
  ((FAIL += 1))
fi

# Check test_vercel_deployment.py exists
if [ -f "apps/api/tests/test_vercel_deployment.py" ]; then
  echo "   ✅ tests/test_vercel_deployment.py exists"
  ((PASS += 1))
else
  echo "   ❌ tests/test_vercel_deployment.py MISSING"
  ((FAIL += 1))
fi

# Check docs/deployment.md documents Vercel single project mode
if grep -q "single Vercel project\|vercel_ephemeral\|Neon" docs/deployment.md 2>/dev/null; then
  echo "   ✅ docs/deployment.md documents single Vercel project mode"
  ((PASS += 1))
else
  echo "   ❌ docs/deployment.md does not document single Vercel project mode"
  ((FAIL += 1))
fi

echo ""

# -------------------------------------------------------------------
# 9. Sprint 11 — Observability, Smoke Script, Readiness Polish, UI, Docs
# -------------------------------------------------------------------
echo "9. Checking Sprint 11 additions..."

# Smoke production script
if [ -f "scripts/smoke_production.py" ]; then
  echo "   ✅ scripts/smoke_production.py exists"
  ((PASS += 1))
else
  echo "   ❌ scripts/smoke_production.py MISSING"
  ((FAIL += 1))
fi

# Smoke script has --run-pipeline flag (read-only by default)
if grep -q "run-pipeline" scripts/smoke_production.py 2>/dev/null && \
   grep -q "store_true" scripts/smoke_production.py 2>/dev/null; then
  echo "   ✅ smoke_production.py has read-only default (--run-pipeline gated)"
  ((PASS += 1))
else
  echo "   ❌ smoke_production.py missing --run-pipeline flag or store_true"
  ((FAIL += 1))
fi

# Observability API file exists
if [ -f "apps/api/app/api/observability.py" ]; then
  echo "   ✅ apps/api/app/api/observability.py exists"
  ((PASS += 1))
else
  echo "   ❌ apps/api/app/api/observability.py MISSING"
  ((FAIL += 1))
fi

# Observability routes present
if grep -q "runs-summary" apps/api/app/api/observability.py 2>/dev/null && \
   grep -q "failure-summary" apps/api/app/api/observability.py 2>/dev/null; then
  echo "   ✅ observability endpoints (runs-summary, failure-summary) present"
  ((PASS += 1))
else
  echo "   ❌ observability endpoints missing from observability.py"
  ((FAIL += 1))
fi

# Observability router registered in main.py
if grep -q "observability" apps/api/app/main.py 2>/dev/null; then
  echo "   ✅ observability router registered in main.py"
  ((PASS += 1))
else
  echo "   ❌ observability router not registered in main.py"
  ((FAIL += 1))
fi

# Readiness endpoint includes api_key_guard_enabled
if grep -q "api_key_guard_enabled" apps/api/app/api/health.py 2>/dev/null; then
  echo "   ✅ /api/readiness includes api_key_guard_enabled field"
  ((PASS += 1))
else
  echo "   ❌ /api/readiness missing api_key_guard_enabled field"
  ((FAIL += 1))
fi

# Runtime/check endpoint exists
if grep -q "runtime/check" apps/api/app/api/health.py 2>/dev/null; then
  echo "   ✅ /api/runtime/check endpoint present in health.py"
  ((PASS += 1))
else
  echo "   ❌ /api/runtime/check endpoint MISSING from health.py"
  ((FAIL += 1))
fi

# Sidebar label updated (no longer says Sprint 9)
if grep -q "Sprint 9" apps/web/components/AppShell.tsx 2>/dev/null; then
  echo "   ❌ AppShell.tsx still says 'Sprint 9' — update the sidebar label"
  ((FAIL += 1))
else
  echo "   ✅ AppShell.tsx sidebar label updated (no 'Sprint 9')"
  ((PASS += 1))
fi

# Sidebar label says Deployed MVP or similar (Sprint 17: cockpit redesign uses "Inventory decision cockpit" or "DemandOS")
if grep -qE "Deployed MVP|Vercel Prototype|Demo Mode|Production|Inventory decision cockpit|DemandOS" apps/web/components/AppShell.tsx 2>/dev/null; then
  echo "   ✅ AppShell.tsx has current sidebar label"
  ((PASS += 1))
else
  echo "   ❌ AppShell.tsx sidebar label not updated to current sprint/mode"
  ((FAIL += 1))
fi

# Sprint 11 test file exists
if [ -f "apps/api/tests/test_sprint11.py" ]; then
  echo "   ✅ apps/api/tests/test_sprint11.py exists"
  ((PASS += 1))
else
  echo "   ❌ apps/api/tests/test_sprint11.py MISSING"
  ((FAIL += 1))
fi

# Case study docs
for doc in \
  "docs/case_study.md" \
  "docs/demo_script.md" \
  "docs/final_qa_checklist.md" \
  "docs/case_study_assets.md"; do
  if [ -f "$doc" ]; then
    echo "   ✅ $doc"
    ((PASS += 1))
  else
    echo "   ❌ $doc MISSING"
    ((FAIL += 1))
  fi
done

# Vercel deployment is documented in deployment.md (already checked in Sprint 10B)
if grep -q "single Vercel project\|Single Vercel" docs/deployment.md 2>/dev/null; then
  echo "   ✅ docs/deployment.md documents single Vercel project deployment"
  ((PASS += 1))
else
  echo "   ❌ docs/deployment.md does not document single Vercel project mode"
  ((FAIL += 1))
fi

echo ""

# -------------------------------------------------------------------
# 10. Sprint 12 — MVP Closeout checks
# -------------------------------------------------------------------
echo "10. Checking Sprint 12 MVP closeout..."

# README has live demo section
if grep -q "demand-os-three.vercel.app" README.md 2>/dev/null; then
  echo "   ✅ README.md contains live demo URL"
  ((PASS += 1))
else
  echo "   ❌ README.md missing live demo URL"
  ((FAIL += 1))
fi

# README has architecture section
if grep -q "mermaid\|Architecture" README.md 2>/dev/null; then
  echo "   ✅ README.md has architecture section"
  ((PASS += 1))
else
  echo "   ❌ README.md missing architecture section"
  ((FAIL += 1))
fi

# README has safety boundaries section
if grep -q "Safety Bound\|safety bound\|No real purchase" README.md 2>/dev/null; then
  echo "   ✅ README.md has safety boundaries section"
  ((PASS += 1))
else
  echo "   ❌ README.md missing safety boundaries section"
  ((FAIL += 1))
fi

# Case study has final status section
if grep -q "Final Status\|MVP: COMPLETE\|MVP is complete" docs/case_study.md 2>/dev/null; then
  echo "   ✅ docs/case_study.md has final status section"
  ((PASS += 1))
else
  echo "   ❌ docs/case_study.md missing final status section"
  ((FAIL += 1))
fi

# Final QA checklist has Sprint 12 section
if grep -q "Sprint 12" docs/final_qa_checklist.md 2>/dev/null; then
  echo "   ✅ docs/final_qa_checklist.md has Sprint 12 execution section"
  ((PASS += 1))
else
  echo "   ❌ docs/final_qa_checklist.md missing Sprint 12 section"
  ((FAIL += 1))
fi

# Screenshots README lists all 12 screenshot filenames
SCREENSHOT_COUNT=$(grep -c "\.png" docs/screenshots/README.md 2>/dev/null || echo 0)
if [ "$SCREENSHOT_COUNT" -ge 12 ]; then
  echo "   ✅ docs/screenshots/README.md lists $SCREENSHOT_COUNT screenshot entries"
  ((PASS += 1))
else
  echo "   ❌ docs/screenshots/README.md lists only $SCREENSHOT_COUNT screenshot entries (expected ≥12)"
  ((FAIL += 1))
fi

# Deployment doc has single Vercel + Neon documented
if grep -q "Neon\|neon" docs/deployment.md 2>/dev/null; then
  echo "   ✅ docs/deployment.md documents Neon Postgres integration"
  ((PASS += 1))
else
  echo "   ❌ docs/deployment.md missing Neon Postgres documentation"
  ((FAIL += 1))
fi

# No docs contain a known production API key pattern (basic guard)
# We check for the literal string pattern of a high-entropy key, not real values
if grep -rq "DEMANDOS_API_KEY=sk-\|DEMANDOS_API_KEY=[a-f0-9]\{32\}" docs/ README.md 2>/dev/null; then
  echo "   ❌ docs/ may contain an exposed API key value"
  ((FAIL += 1))
else
  echo "   ✅ No obvious API key values found in docs/"
  ((PASS += 1))
fi

# No docs contain raw Neon database URL patterns
if grep -rqE "postgresql://.*@.*neon\.tech|postgres://.*@.*neon\.tech" docs/ README.md 2>/dev/null; then
  echo "   ❌ docs/ contains a raw Neon database URL"
  ((FAIL += 1))
else
  echo "   ✅ No raw Neon database URLs found in docs/"
  ((PASS += 1))
fi

# Portfolio landing page draft exists
if [ -f "docs/portfolio_landing_page_draft.md" ]; then
  echo "   ✅ docs/portfolio_landing_page_draft.md exists"
  ((PASS += 1))
else
  echo "   ❌ docs/portfolio_landing_page_draft.md MISSING"
  ((FAIL += 1))
fi

# Screenshot capture script exists
if [ -f "scripts/capture_screenshots.py" ]; then
  echo "   ✅ scripts/capture_screenshots.py exists"
  ((PASS += 1))
else
  echo "   ❌ scripts/capture_screenshots.py MISSING"
  ((FAIL += 1))
fi

echo ""

# -------------------------------------------------------------------
# Sprint 13 — CSV upload, monitoring, scenarios, connector prep
# -------------------------------------------------------------------
echo "Sprint 13 backend files..."
SPRINT13_BACKEND=(
  "apps/api/app/api/csv_upload.py"
  "apps/api/app/api/monitoring.py"
  "apps/api/app/api/scenarios.py"
  "apps/api/app/api/connectors.py"
  "apps/api/app/services/csv_ingestion_service.py"
  "apps/api/app/services/monitoring_service.py"
  "apps/api/app/services/scenario_service.py"
  "apps/api/app/schemas/csv_upload.py"
  "apps/api/app/schemas/scenarios.py"
  "apps/api/app/schemas/connectors.py"
  "apps/api/app/validation/csv_validators.py"
  "apps/api/app/connectors/shopify.py"
  "apps/api/app/connectors/woocommerce.py"
  "apps/api/tests/test_csv_upload.py"
  "apps/api/tests/test_monitoring.py"
  "apps/api/tests/test_scenarios.py"
  "apps/api/tests/test_connector_prep.py"
)
for f in "${SPRINT13_BACKEND[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 13 frontend pages..."
SPRINT13_FRONTEND=(
  "apps/web/app/csv-upload/page.tsx"
  "apps/web/app/monitoring/page.tsx"
  "apps/web/app/scenarios/page.tsx"
  "apps/web/app/connectors/page.tsx"
)
for f in "${SPRINT13_FRONTEND[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 13 — nav labels in AppShell (Sprint 17: Connectors→Data Sources, Monitoring merged into Trust section)..."
# Sprint 17 renamed Connectors→Data Sources and merged Monitoring into Forecast Trust/Data Quality
for label in "CSV Upload" "Scenarios"; do
  if grep -q "$label" apps/web/components/AppShell.tsx 2>/dev/null; then
    echo "   ✅ AppShell has '$label' nav item"
    ((PASS += 1))
  else
    echo "   ❌ AppShell missing '$label' nav item"
    ((FAIL += 1))
  fi
done
# Sprint 17: Connectors renamed to Data Sources
if grep -qE "Data Sources|Connectors" apps/web/components/AppShell.tsx 2>/dev/null; then
  echo "   ✅ AppShell has Data Sources (or legacy Connectors) nav item"
  ((PASS += 1))
else
  echo "   ❌ AppShell missing Data Sources nav item"
  ((FAIL += 1))
fi
# Sprint 17: Monitoring merged — check page file still exists for backend tests
if [ -f "apps/web/app/monitoring/page.tsx" ]; then
  echo "   ✅ Monitoring page file exists (merged into Trust nav in Sprint 17)"
  ((PASS += 1))
else
  echo "   ❌ Monitoring page file MISSING"
  ((FAIL += 1))
fi

echo ""
echo "Sprint 13 — API routes registered in main.py..."
for route in "csv_upload" "monitoring" "scenarios" "connector_api"; do
  if grep -q "$route" apps/api/app/main.py 2>/dev/null; then
    echo "   ✅ main.py includes $route router"
    ((PASS += 1))
  else
    echo "   ❌ main.py missing $route router"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 13 — security checks on new files..."
if grep -rqE 'DEMANDOS_API_KEY=[a-zA-Z0-9]{16,}' apps/api/app/api/csv_upload.py apps/api/app/api/monitoring.py apps/api/app/api/scenarios.py apps/api/app/api/connectors.py 2>/dev/null; then
  echo "   ❌ Possible API key value found in Sprint 13 API files"
  ((FAIL += 1))
else
  echo "   ✅ No API key values in Sprint 13 API files"
  ((PASS += 1))
fi

if grep -qE 'postgresql://|@neon\.tech' apps/api/app/connectors/shopify.py apps/api/app/connectors/woocommerce.py 2>/dev/null; then
  echo "   ❌ Raw database URL found in connector stubs"
  ((FAIL += 1))
else
  echo "   ✅ No raw database URLs in connector stubs"
  ((PASS += 1))
fi

echo ""

# -------------------------------------------------------------------
# Sprint 14 — public release readiness
# -------------------------------------------------------------------
echo "Sprint 14 — public release readiness..."

if python3 scripts/public_readiness_check.py; then
  echo "   ✅ Public readiness audit passed"
  ((PASS += 1))
else
  echo "   ❌ Public readiness audit failed"
  ((FAIL += 1))
fi

for section in "Live demo" "Advanced Features" "Safety Boundaries" "Public portfolio prototype"; do
  if grep -qi "$section" README.md 2>/dev/null; then
    echo "   ✅ README includes '$section'"
    ((PASS += 1))
  else
    echo "   ❌ README missing '$section'"
    ((FAIL += 1))
  fi
done

for feature in "CSV upload" "monitoring" "scenario planning" "disabled connector"; do
  if grep -qi "$feature" docs/case_study.md 2>/dev/null; then
    echo "   ✅ Case study includes '$feature'"
    ((PASS += 1))
  else
    echo "   ❌ Case study missing '$feature'"
    ((FAIL += 1))
  fi
done

for screenshot in "13-csv-upload.png" "14-monitoring.png" "15-scenarios.png" "16-connectors.png"; do
  if grep -q "$screenshot" docs/screenshots/README.md 2>/dev/null; then
    echo "   ✅ Screenshot docs include $screenshot"
    ((PASS += 1))
  else
    echo "   ❌ Screenshot docs missing $screenshot"
    ((FAIL += 1))
  fi
done

if grep -qE "Deployed MVP|Inventory decision cockpit|Operator Cockpit" apps/web/components/AppShell.tsx 2>/dev/null; then
  echo "   ✅ Sidebar uses public-release label (Sprint 17: operator cockpit branding)"
  ((PASS += 1))
else
  echo "   ❌ Sidebar label is stale — expected 'Deployed MVP', 'Inventory decision cockpit', or 'Operator Cockpit'"
  ((FAIL += 1))
fi

if find . -path './.git' -prune -o -name '.env.local' -print | grep -q .; then
  echo "   ❌ .env.local found in repository tree"
  ((FAIL += 1))
else
  echo "   ✅ No .env.local file found"
  ((PASS += 1))
fi

echo ""

# -------------------------------------------------------------------
# Sprint 15 — Data science explainability + ML Insights polish
# -------------------------------------------------------------------
echo "Sprint 15 backend files..."
SPRINT15_BACKEND=(
  "apps/api/app/schemas/data_science.py"
  "apps/api/app/services/data_science_summary_service.py"
  "apps/api/app/api/data_science.py"
  "apps/api/tests/test_data_science.py"
)
for f in "${SPRINT15_BACKEND[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 15 frontend pages..."
SPRINT15_FRONTEND=(
  "apps/web/app/data-science/page.tsx"
)
for f in "${SPRINT15_FRONTEND[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS += 1))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 15 — nav and content checks..."

# Sprint 17: ML Insights merged into Forecast Trust — check page still exists (not required in nav)
if [ -f "apps/web/app/data-science/page.tsx" ]; then
  echo "   ✅ ML Insights page (data-science) exists — accessible via Forecast Trust cross-link (Sprint 17)"
  ((PASS += 1))
else
  echo "   ❌ ML Insights page (data-science) MISSING"
  ((FAIL += 1))
fi

if grep -q "getAnalyticsCockpit\|Analytics cockpit\|CockpitPage\|SituationBanner" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Home page has analytics cockpit / operator cockpit (Sprint 16/17 redesign)"
  ((PASS += 1))
else
  echo "   ❌ Home page missing analytics cockpit"
  ((FAIL += 1))
fi

if grep -q "Safety boundary\|no external actions\|Synthetic demo" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Home page has safety/context section"
  ((PASS += 1))
else
  echo "   ❌ Home page missing safety or context section"
  ((FAIL += 1))
fi

if grep -q "Forecast quality\|forecast_quality_label\|getAnalyticsCockpit" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Home page has forecast quality indicator"
  ((PASS += 1))
else
  echo "   ❌ Home page missing forecast quality indicator"
  ((FAIL += 1))
fi

if grep -q "About these forecasts" apps/web/app/forecasts/page.tsx 2>/dev/null; then
  echo "   ✅ Forecast page has explainer"
  ((PASS += 1))
else
  echo "   ❌ Forecast page missing explainer"
  ((FAIL += 1))
fi

if grep -q "Model Leaderboard" apps/web/app/model-performance/page.tsx 2>/dev/null; then
  echo "   ✅ Model performance page has leaderboard"
  ((PASS += 1))
else
  echo "   ❌ Model performance page missing leaderboard"
  ((FAIL += 1))
fi

if grep -q "How risk scores are computed" apps/web/app/risks/page.tsx 2>/dev/null; then
  echo "   ✅ Risk page has decision guidance"
  ((PASS += 1))
else
  echo "   ❌ Risk page missing decision guidance"
  ((FAIL += 1))
fi

if grep -q "Why these recommendations exist" apps/web/app/recommendations/page.tsx 2>/dev/null; then
  echo "   ✅ Recommendations page has context"
  ((PASS += 1))
else
  echo "   ❌ Recommendations page missing context"
  ((FAIL += 1))
fi

if grep -q "No purchase order is created" apps/web/app/recommendations/page.tsx 2>/dev/null; then
  echo "   ✅ Recommendations page has safety note"
  ((PASS += 1))
else
  echo "   ❌ Recommendations page missing safety note"
  ((FAIL += 1))
fi

if grep -q "Data Lineage" apps/web/app/data-health/page.tsx 2>/dev/null; then
  echo "   ✅ Data health page has lineage section"
  ((PASS += 1))
else
  echo "   ❌ Data health page missing lineage section"
  ((FAIL += 1))
fi

echo ""
echo "Sprint 15 — API routes registered..."
if grep -q "data_science" apps/api/app/main.py 2>/dev/null; then
  echo "   ✅ main.py includes data_science router"
  ((PASS += 1))
else
  echo "   ❌ main.py missing data_science router"
  ((FAIL += 1))
fi

echo ""
echo "Sprint 15 — no secrets in new files..."
if grep -rqE 'DEMANDOS_API_KEY=[a-zA-Z0-9]{16,}' \
  apps/api/app/api/data_science.py \
  apps/api/app/services/data_science_summary_service.py 2>/dev/null; then
  echo "   ❌ Possible API key value in Sprint 15 files"
  ((FAIL += 1))
else
  echo "   ✅ No API key values in Sprint 15 files"
  ((PASS += 1))
fi

echo ""
echo "Sprint 15 — screenshot docs..."
if grep -q "17-ml-insights" docs/screenshots/README.md 2>/dev/null; then
  echo "   ✅ Screenshot docs include 17-ml-insights"
  ((PASS += 1))
else
  echo "   ⚠️  Screenshot docs missing 17-ml-insights (SKIP — manual capture pending)"
  ((SKIP += 1))
fi

echo ""
echo "Sprint 16 — analytics cockpit API files..."
for f in \
  apps/api/app/schemas/analytics.py \
  apps/api/app/services/analytics_cockpit_service.py \
  apps/api/app/api/analytics.py \
  apps/api/tests/test_analytics_cockpit.py; do
  if [ -f "$f" ]; then
    echo "   ✅ $f exists"
    ((PASS += 1))
  else
    echo "   ❌ $f missing"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 16 — analytics router registered..."
if grep -q "analytics" apps/api/app/main.py 2>/dev/null; then
  echo "   ✅ main.py includes analytics router"
  ((PASS += 1))
else
  echo "   ❌ main.py missing analytics router"
  ((FAIL += 1))
fi

echo ""
echo "Sprint 16 — analytics endpoints exist..."
for ep in "cockpit" "inventory-trend" "risk-drivers" "reorder-queue" "executive-summary"; do
  if grep -q "$ep" apps/api/app/api/analytics.py 2>/dev/null; then
    echo "   ✅ /api/analytics/$ep defined"
    ((PASS += 1))
  else
    echo "   ❌ /api/analytics/$ep missing"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 16 — cockpit UI components..."
for f in \
  apps/web/components/InventoryTrendChart.tsx \
  apps/web/components/RiskDistributionChart.tsx \
  apps/web/components/RiskDriverList.tsx \
  apps/web/components/ReorderQueueTable.tsx; do
  if [ -f "$f" ]; then
    echo "   ✅ $f exists"
    ((PASS += 1))
  else
    echo "   ❌ $f missing"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 16 — home page uses analytics cockpit..."
if grep -q "getAnalyticsCockpit" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Home page calls getAnalyticsCockpit"
  ((PASS += 1))
else
  echo "   ❌ Home page missing getAnalyticsCockpit call"
  ((FAIL += 1))
fi

if grep -q "InventoryTrendChart" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Home page has InventoryTrendChart"
  ((PASS += 1))
else
  echo "   ❌ Home page missing InventoryTrendChart"
  ((FAIL += 1))
fi

if grep -q "RiskDriverList" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Home page has RiskDriverList"
  ((PASS += 1))
else
  echo "   ❌ Home page missing RiskDriverList"
  ((FAIL += 1))
fi

if grep -q "ReorderQueueTable" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Home page has ReorderQueueTable (reorder queue preview)"
  ((PASS += 1))
else
  echo "   ❌ Home page missing ReorderQueueTable"
  ((FAIL += 1))
fi

echo ""
echo "Sprint 16 — no hardcoded KPI constants in home page..."
for bad in "94%" "120,000" "9,516" "6,686" "7,751"; do
  if grep -qF "$bad" apps/web/app/page.tsx 2>/dev/null; then
    echo "   ❌ Hardcoded value '$bad' found in home page"
    ((FAIL += 1))
  else
    echo "   ✅ No hardcoded '$bad' in home page"
    ((PASS += 1))
  fi
done

echo ""
echo "Sprint 16 — no secrets in analytics files..."
if grep -rqE 'DEMANDOS_API_KEY=[a-zA-Z0-9]{16,}' \
  apps/api/app/api/analytics.py \
  apps/api/app/services/analytics_cockpit_service.py 2>/dev/null; then
  echo "   ❌ Possible API key value in Sprint 16 files"
  ((FAIL += 1))
else
  echo "   ✅ No API key values in Sprint 16 files"
  ((PASS += 1))
fi

echo ""
echo "Sprint 16 — screenshot docs (18-analytics-cockpit)..."
if grep -q "18-analytics-cockpit" docs/screenshots/README.md 2>/dev/null; then
  echo "   ✅ Screenshot docs include 18-analytics-cockpit"
  ((PASS += 1))
else
  echo "   ⚠️  Screenshot docs missing 18-analytics-cockpit (SKIP — manual capture pending)"
  ((SKIP += 1))
fi

echo ""

# -------------------------------------------------------------------
# Sprint 17 — Operator Cockpit IA Redesign
# -------------------------------------------------------------------
echo "Sprint 17 — Navigation structure (Operate / Trust / Setup)..."

# Section labels in AppShell
for section in "Operate" "Trust" "Setup"; do
  if grep -q "$section" apps/web/components/AppShell.tsx 2>/dev/null; then
    echo "   ✅ AppShell has '$section' nav section"
    ((PASS += 1))
  else
    echo "   ❌ AppShell missing '$section' nav section"
    ((FAIL += 1))
  fi
done

# New nav labels
for label in "Cockpit" "Risk Board" "Reorder Queue" "Forecast Trust" "Data Quality" "Pipeline Trace" "Data Sources"; do
  if grep -q "$label" apps/web/components/AppShell.tsx 2>/dev/null; then
    echo "   ✅ AppShell has '$label' nav item"
    ((PASS += 1))
  else
    echo "   ❌ AppShell missing '$label' nav item"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 17 — New shared components..."
for f in \
  apps/web/components/SituationBanner.tsx \
  apps/web/components/DemoScenarioCard.tsx \
  apps/web/components/TrustBadge.tsx \
  apps/web/components/TechnicalTrace.tsx; do
  if [ -f "$f" ]; then
    echo "   ✅ $f exists"
    ((PASS += 1))
  else
    echo "   ❌ $f MISSING"
    ((FAIL += 1))
  fi
done

echo ""
echo "Sprint 17 — Cockpit page uses new components..."
if grep -q "SituationBanner" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Cockpit uses SituationBanner"
  ((PASS += 1))
else
  echo "   ❌ Cockpit missing SituationBanner"
  ((FAIL += 1))
fi
if grep -q "DemoScenarioCard" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Cockpit uses DemoScenarioCard"
  ((PASS += 1))
else
  echo "   ❌ Cockpit missing DemoScenarioCard"
  ((FAIL += 1))
fi
if grep -q "TechnicalTrace" apps/web/app/page.tsx 2>/dev/null; then
  echo "   ✅ Cockpit uses TechnicalTrace"
  ((PASS += 1))
else
  echo "   ❌ Cockpit missing TechnicalTrace"
  ((FAIL += 1))
fi

echo ""
echo "Sprint 17 — Page copy and framing..."

# Risk Board uses triage framing
if grep -q "Risk Board\|triage" apps/web/app/risks/page.tsx 2>/dev/null; then
  echo "   ✅ Risk page has Risk Board / triage framing"
  ((PASS += 1))
else
  echo "   ❌ Risk page missing Risk Board / triage framing"
  ((FAIL += 1))
fi

# Reorder Queue has internal-only safety copy
if grep -q "Reorder Queue\|internal.*review\|Approving internally" apps/web/app/recommendations/page.tsx 2>/dev/null; then
  echo "   ✅ Recommendations page has Reorder Queue / internal safety copy"
  ((PASS += 1))
else
  echo "   ❌ Recommendations page missing Reorder Queue framing"
  ((FAIL += 1))
fi

# Forecast Trust page has trust labels
if grep -q "Forecast Trust\|Strong\|Directional" apps/web/app/model-performance/page.tsx 2>/dev/null; then
  echo "   ✅ Model performance page has Forecast Trust labels"
  ((PASS += 1))
else
  echo "   ❌ Model performance page missing Forecast Trust labels"
  ((FAIL += 1))
fi

# Pipeline Trace has technical-review note
if grep -q "Pipeline Trace\|technical review\|start from" apps/web/app/pipeline/page.tsx 2>/dev/null; then
  echo "   ✅ Pipeline page has Pipeline Trace / technical review note"
  ((PASS += 1))
else
  echo "   ❌ Pipeline page missing Pipeline Trace / technical review note"
  ((FAIL += 1))
fi

# Scenarios page has simulated-only language
if grep -q "Simulated\|simulated only\|Simulated only" apps/web/app/scenarios/page.tsx 2>/dev/null; then
  echo "   ✅ Scenarios page has simulated-only language"
  ((PASS += 1))
else
  echo "   ❌ Scenarios page missing simulated-only language"
  ((FAIL += 1))
fi

# Data Quality label
if grep -q "Data Quality" apps/web/app/data-health/page.tsx 2>/dev/null; then
  echo "   ✅ Data health page uses 'Data Quality' label"
  ((PASS += 1))
else
  echo "   ❌ Data health page missing 'Data Quality' label"
  ((FAIL += 1))
fi

# Data Sources label
if grep -q "Data Sources" apps/web/app/connectors/page.tsx 2>/dev/null; then
  echo "   ✅ Connectors page uses 'Data Sources' label"
  ((PASS += 1))
else
  echo "   ❌ Connectors page missing 'Data Sources' label"
  ((FAIL += 1))
fi

echo ""
echo "Sprint 17 — No hardcoded cockpit KPI values..."
for bad in "18,400\|18.4K\|94%\|€120" ; do
  if grep -qE "$bad" apps/web/app/page.tsx 2>/dev/null; then
    echo "   ❌ Possible hardcoded KPI value '$bad' in Cockpit page"
    ((FAIL += 1))
  else
    echo "   ✅ No hardcoded '$bad' in Cockpit page"
    ((PASS += 1))
  fi
done

echo ""
echo "Sprint 17 — No secrets in new component files..."
if grep -rqE 'DEMANDOS_API_KEY=[a-zA-Z0-9]{16,}' \
  apps/web/components/SituationBanner.tsx \
  apps/web/components/DemoScenarioCard.tsx \
  apps/web/components/TrustBadge.tsx \
  apps/web/components/TechnicalTrace.tsx 2>/dev/null; then
  echo "   ❌ Possible API key value in Sprint 17 component files"
  ((FAIL += 1))
else
  echo "   ✅ No API key values in Sprint 17 component files"
  ((PASS += 1))
fi

echo ""

# -------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------
echo "========================"
echo "Summary: $PASS passed, $FAIL failed, $SKIP skipped"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo "✅ Verification PASSED"
  exit 0
else
  echo "❌ Verification FAILED — $FAIL check(s) need attention"
  exit 1
fi
