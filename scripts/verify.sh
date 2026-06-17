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
    ((PASS++))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL++))
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
)
for f in "${DOC_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS++))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL++))
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
  "apps/api/app/db/models.py"
  "apps/api/app/connectors/base.py"
  "apps/api/app/connectors/mock_commerce.py"
  "apps/api/app/schemas/raw.py"
  "apps/api/app/schemas/derived.py"
  "apps/api/app/services/ingestion_service.py"
  "apps/api/app/services/aggregation_service.py"
  "apps/api/app/services/forecasting_service.py"
  "apps/api/app/services/stockout_service.py"
  "apps/api/app/services/recommendation_service.py"
  "apps/api/app/api/aggregation.py"
  "apps/api/tests/test_health.py"
  "apps/api/tests/test_connector_contract.py"
  "apps/api/tests/test_raw_data_rule.py"
  "apps/api/tests/test_aggregation.py"
  "apps/api/pyproject.toml"
  "scripts/build_canonical_tables.py"
)
for f in "${BACKEND_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS++))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL++))
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
      ((PASS++))
    else
      echo ""
      echo "   ❌ pytest tests FAILED"
      ((FAIL++))
    fi
  else
    echo "   ⚠️  SKIP — Python dependencies not installed."
    echo "   Run: cd apps/api && pip install -e '.[dev]'"
    ((SKIP++))
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
  "apps/web/app/forecasts/page.tsx"
  "apps/web/app/risks/page.tsx"
  "apps/web/components/AppShell.tsx"
  "apps/web/lib/api.ts"
)
for f in "${FRONTEND_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "   ✅ $f"
    ((PASS++))
  else
    echo "   ❌ $f — MISSING"
    ((FAIL++))
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
    ((FAIL++))
  fi
done
if [ "$SCHEMA_CLEAN" = true ]; then
  echo "   ✅ No forbidden derived field declarations in raw schema"
  echo "   ℹ️  (Authoritative check: pytest tests/test_raw_data_rule.py)"
  ((PASS++))
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
