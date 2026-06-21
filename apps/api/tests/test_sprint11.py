"""
Sprint 11 tests — Production Smoke Validation, Observability Polish, and Case Study Prep.

Tests cover:
  J1.  smoke script exists
  J2.  smoke script has read-only default mode (no pipeline run without --run-pipeline)
  J3.  smoke script only triggers pipeline with explicit --run-pipeline flag
  J4.  readiness endpoint does not expose secrets
  J5.  runtime/check endpoint does not expose secrets
  J6.  observability/runs-summary endpoint exists and returns expected keys
  J7.  observability/runs-summary has bounded results (no unbounded queries exposed)
  J8.  observability/failure-summary endpoint exists and returns expected keys
  J9.  sidebar label no longer says "Sprint 9"
  J10. docs/case_study.md exists
  J11. docs/demo_script.md exists
  J12. docs/final_qa_checklist.md exists
  J13. docs/case_study_assets.md exists
  J14. readiness includes api_key_guard_enabled and external_side_effects_enabled
  J15. runtime/check includes model_artifact_mode and active_connector
"""

import ast
import os
import sys

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@pytest.fixture(autouse=True)
def isolated_db(override_db):
    yield


client = TestClient(app)


# ---------------------------------------------------------------------------
# J1. Smoke script exists
# ---------------------------------------------------------------------------

def test_smoke_script_exists():
    path = os.path.join(ROOT, "scripts", "smoke_production.py")
    assert os.path.isfile(path), "scripts/smoke_production.py must exist"


# ---------------------------------------------------------------------------
# J2. Smoke script has read-only default (no --run-pipeline arg by default)
# ---------------------------------------------------------------------------

def test_smoke_script_has_argparse_with_run_pipeline_flag():
    path = os.path.join(ROOT, "scripts", "smoke_production.py")
    with open(path) as f:
        source = f.read()
    assert "--run-pipeline" in source, (
        "smoke_production.py must expose a --run-pipeline flag"
    )
    assert "action=\"store_true\"" in source or "store_true" in source, (
        "--run-pipeline must be a boolean flag (store_true), not a required argument"
    )


# ---------------------------------------------------------------------------
# J3. Pipeline write only triggered when --run-pipeline is present
# ---------------------------------------------------------------------------

def test_smoke_script_pipeline_gated_by_flag():
    path = os.path.join(ROOT, "scripts", "smoke_production.py")
    with open(path) as f:
        source = f.read()
    # The run_pipeline path must be inside the `if run_pipeline:` branch
    assert "if run_pipeline:" in source or "if args.run_pipeline" in source, (
        "Pipeline write actions must be gated on run_pipeline flag"
    )
    # Confirm that run-full-pipeline is only referenced inside that gate,
    # not unconditionally at top level
    lines = source.splitlines()
    inside_gate = False
    unconditional_trigger = False
    for line in lines:
        stripped = line.strip()
        if "if run_pipeline" in stripped or "if args.run_pipeline" in stripped:
            inside_gate = True
        if not inside_gate and "run-full-pipeline" in stripped:
            unconditional_trigger = True
    assert not unconditional_trigger, (
        "run-full-pipeline call must be inside the --run-pipeline gate"
    )


# ---------------------------------------------------------------------------
# J4. Readiness endpoint does not expose secrets
# ---------------------------------------------------------------------------

def test_readiness_does_not_expose_database_url(monkeypatch):
    from app import config as cfg
    from app.config import Settings

    fake_settings = Settings(
        database_url="postgresql://user:s3cr3t@host/db",
        demandos_api_key="super-secret-api-key",
        demandos_runtime_mode="vercel",
        demandos_demo_scale="small",
    )
    monkeypatch.setattr(cfg, "get_settings", lambda: fake_settings)

    response = client.get("/api/readiness")
    assert response.status_code == 200
    body = response.json()
    body_str = str(body)

    assert "s3cr3t" not in body_str, "DATABASE_URL password must not appear in readiness response"
    assert "super-secret-api-key" not in body_str, "API key value must not appear in readiness response"
    assert "postgresql://user" not in body_str, "Full DATABASE_URL must not appear in readiness response"


def test_readiness_includes_required_sprint11_fields():
    response = client.get("/api/readiness")
    assert response.status_code == 200
    body = response.json()
    assert "ready" in body
    assert "status" in body
    assert "runtime_mode" in body
    assert "demo_scale" in body
    assert "database" in body
    assert "api_key_guard_enabled" in body
    assert "external_side_effects_enabled" in body
    assert "checks" in body
    assert isinstance(body["checks"], list)


def test_readiness_external_side_effects_always_false():
    response = client.get("/api/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["external_side_effects_enabled"] is False


def test_readiness_checks_contain_named_checks():
    response = client.get("/api/readiness")
    assert response.status_code == 200
    checks = response.json()["checks"]
    names = {c["name"] for c in checks}
    assert "database_connection" in names
    assert "runtime_mode" in names
    assert "demo_scale" in names
    assert "api_key_guard" in names
    assert "model_artifact_mode" in names


# ---------------------------------------------------------------------------
# J5. Runtime/check endpoint does not expose secrets
# ---------------------------------------------------------------------------

def test_runtime_check_exists():
    response = client.get("/api/runtime/check")
    assert response.status_code == 200


def test_runtime_check_does_not_expose_secrets(monkeypatch):
    from app import config as cfg
    from app.config import Settings

    fake_settings = Settings(
        database_url="postgresql://user:s3cr3t@host/db",
        demandos_api_key="another-secret-key",
        demandos_runtime_mode="local",
        demandos_demo_scale="full",
    )
    monkeypatch.setattr(cfg, "get_settings", lambda: fake_settings)

    response = client.get("/api/runtime/check")
    assert response.status_code == 200
    body_str = str(response.json())
    assert "s3cr3t" not in body_str, "DATABASE_URL password must not appear in runtime check"
    assert "another-secret-key" not in body_str, "API key value must not appear in runtime check"


def test_runtime_check_includes_expected_fields():
    response = client.get("/api/runtime/check")
    assert response.status_code == 200
    body = response.json()
    assert "runtime_mode" in body
    assert "demo_scale" in body
    assert "database" in body
    assert "api_key_guard_enabled" in body
    assert "external_side_effects_enabled" in body
    assert "model_artifact_mode" in body
    assert "active_connector" in body


# ---------------------------------------------------------------------------
# J6. observability/runs-summary exists and returns expected structure
# ---------------------------------------------------------------------------

def test_observability_runs_summary_exists():
    response = client.get("/api/observability/runs-summary")
    assert response.status_code == 200


def test_observability_runs_summary_has_stages():
    response = client.get("/api/observability/runs-summary")
    assert response.status_code == 200
    body = response.json()
    assert "stages" in body
    assert isinstance(body["stages"], list)
    assert len(body["stages"]) >= 7  # at least 7 pipeline stages


def test_observability_runs_summary_has_runtime_info():
    response = client.get("/api/observability/runs-summary")
    body = response.json()
    assert "runtime_mode" in body
    assert "demo_scale" in body


def test_observability_runs_summary_stage_structure():
    response = client.get("/api/observability/runs-summary")
    stages = response.json()["stages"]
    for stage in stages:
        assert "stage" in stage, f"Stage missing 'stage' key: {stage}"
        assert "status" in stage, f"Stage missing 'status' key: {stage}"


# ---------------------------------------------------------------------------
# J7. observability/runs-summary does not return unbounded results
# ---------------------------------------------------------------------------

def test_observability_runs_summary_is_bounded():
    response = client.get("/api/observability/runs-summary")
    body = response.json()
    # Stages should be a fixed-length list, not unbounded
    assert len(body["stages"]) <= 20, "runs-summary stages should be bounded"


# ---------------------------------------------------------------------------
# J8. observability/failure-summary exists and returns expected keys
# ---------------------------------------------------------------------------

def test_observability_failure_summary_exists():
    response = client.get("/api/observability/failure-summary")
    assert response.status_code == 200


def test_observability_failure_summary_has_expected_keys():
    response = client.get("/api/observability/failure-summary")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "failure_count" in body
    assert "failures" in body
    assert isinstance(body["failures"], list)


def test_observability_failure_summary_clean_when_no_runs():
    response = client.get("/api/observability/failure-summary")
    body = response.json()
    # With an empty DB, there should be no failures
    assert body["failure_count"] == 0
    assert body["status"] == "clean"


def test_observability_failure_summary_bounded():
    response = client.get("/api/observability/failure-summary")
    body = response.json()
    assert len(body["failures"]) <= 20, "failure-summary failures must be bounded"


# ---------------------------------------------------------------------------
# J9. Sidebar label no longer says "Sprint 9"
# ---------------------------------------------------------------------------

def test_sidebar_label_not_sprint9():
    appshell_path = os.path.join(
        ROOT, "apps", "web", "components", "AppShell.tsx"
    )
    assert os.path.isfile(appshell_path), "AppShell.tsx must exist"
    with open(appshell_path) as f:
        content = f.read()
    assert "Sprint 9" not in content, (
        "Sidebar label must not say 'Sprint 9' — update to current sprint/mode"
    )


def test_sidebar_label_says_deployed_mvp_or_similar():
    appshell_path = os.path.join(
        ROOT, "apps", "web", "components", "AppShell.tsx"
    )
    with open(appshell_path) as f:
        content = f.read()
    # Must contain one of the acceptable labels
    acceptable = ["Deployed MVP", "Vercel Prototype", "Demo Mode", "Production"]
    assert any(label in content for label in acceptable), (
        f"AppShell sidebar label must contain one of: {acceptable}"
    )


# ---------------------------------------------------------------------------
# J10. docs/case_study.md exists
# ---------------------------------------------------------------------------

def test_case_study_md_exists():
    path = os.path.join(ROOT, "docs", "case_study.md")
    assert os.path.isfile(path), "docs/case_study.md must exist"


def test_case_study_md_has_required_sections():
    path = os.path.join(ROOT, "docs", "case_study.md")
    with open(path) as f:
        content = f.read()
    required = [
        "Problem Statement",
        "Architecture",
        "Forecasting",
        "Stockout Risk",
        "Deployment",
        "Testing",
        "prototype",
    ]
    for section in required:
        assert section in content, f"case_study.md missing section/keyword: {section!r}"


# ---------------------------------------------------------------------------
# J11. docs/demo_script.md exists
# ---------------------------------------------------------------------------

def test_demo_script_md_exists():
    path = os.path.join(ROOT, "docs", "demo_script.md")
    assert os.path.isfile(path), "docs/demo_script.md must exist"


def test_demo_script_md_has_sections():
    path = os.path.join(ROOT, "docs", "demo_script.md")
    with open(path) as f:
        content = f.read()
    required = ["Pipeline Controls", "Forecasts", "Recommendations", "Safety"]
    for section in required:
        assert section in content, f"demo_script.md missing section: {section!r}"


# ---------------------------------------------------------------------------
# J12. docs/final_qa_checklist.md exists
# ---------------------------------------------------------------------------

def test_final_qa_checklist_exists():
    path = os.path.join(ROOT, "docs", "final_qa_checklist.md")
    assert os.path.isfile(path), "docs/final_qa_checklist.md must exist"


def test_final_qa_checklist_has_sections():
    path = os.path.join(ROOT, "docs", "final_qa_checklist.md")
    with open(path) as f:
        content = f.read()
    required = ["Deployment Checks", "Pipeline Execution", "Security", "API Key Guard"]
    for section in required:
        assert section in content, f"final_qa_checklist.md missing section: {section!r}"


# ---------------------------------------------------------------------------
# J13. docs/case_study_assets.md exists
# ---------------------------------------------------------------------------

def test_case_study_assets_exists():
    path = os.path.join(ROOT, "docs", "case_study_assets.md")
    assert os.path.isfile(path), "docs/case_study_assets.md must exist"


def test_case_study_assets_lists_screenshots():
    path = os.path.join(ROOT, "docs", "case_study_assets.md")
    with open(path) as f:
        content = f.read()
    assert "readiness" in content.lower()
    assert "pipeline" in content.lower()
    assert "forecasts" in content.lower()
    assert "risk" in content.lower()
    assert "recommendations" in content.lower()


# ---------------------------------------------------------------------------
# J14. Readiness includes api_key_guard_enabled and external_side_effects
# ---------------------------------------------------------------------------

def test_readiness_api_key_guard_enabled_field():
    response = client.get("/api/readiness")
    body = response.json()
    assert "api_key_guard_enabled" in body
    assert isinstance(body["api_key_guard_enabled"], bool)


def test_readiness_external_side_effects_field():
    response = client.get("/api/readiness")
    body = response.json()
    assert "external_side_effects_enabled" in body
    assert body["external_side_effects_enabled"] is False


# ---------------------------------------------------------------------------
# J15. runtime/check includes model_artifact_mode and active_connector
# ---------------------------------------------------------------------------

def test_runtime_check_model_artifact_mode():
    response = client.get("/api/runtime/check")
    body = response.json()
    assert "model_artifact_mode" in body
    assert body["model_artifact_mode"] in ("ephemeral_tmp", "filesystem")


def test_runtime_check_active_connector():
    response = client.get("/api/runtime/check")
    body = response.json()
    assert "active_connector" in body
    assert isinstance(body["active_connector"], str)
