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

# requirements.txt must list fastapi and psycopg2-binary
if grep -q "fastapi" requirements.txt 2>/dev/null && grep -q "psycopg2" requirements.txt 2>/dev/null; then
  echo "   ✅ requirements.txt contains fastapi and psycopg2 runtime dependencies"
  ((PASS += 1))
else
  echo "   ❌ requirements.txt missing required runtime dependencies"
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
