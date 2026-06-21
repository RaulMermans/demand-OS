#!/usr/bin/env python3
"""
DemandOS Production Smoke Test Script — Sprint 11

Usage:
  python scripts/smoke_production.py --base-url https://demand-os-three.vercel.app
  python scripts/smoke_production.py --base-url https://demand-os-three.vercel.app \
      --api-key "$DEMANDOS_API_KEY" --run-pipeline

Checks:
  1. GET /api/readiness
  2. GET /api/dashboard/overview   (homepage data endpoint)
  3. GET /api/overview             (overview/dashboard endpoint)
  4. GET /api/data-health          (data health endpoint)
  5. GET /api/dashboard/forecast-summary
  6. GET /api/dashboard/risk-summary
  7. GET /api/dashboard/recommendation-summary
  8. GET /api/dashboard/model-summary
  9. GET /api/demo/pipeline-runs/latest
 10. Verify deployed mode is vercel
 11. Verify demo scale is small
 12. Verify core counts are nonzero
 13. Verify recommendations count is nonzero
 14. Verify no endpoint leaks DEMANDOS_API_KEY value
 15. Verify no endpoint returns local SQLite path or secret DB URL

Only runs pipeline write actions when --run-pipeline is explicitly passed.
"""

import argparse
import json
import sys
import time
from typing import Any

try:
    import urllib.request
    import urllib.error
except ImportError:
    print("stdlib urllib not available — this script requires Python 3.x")
    sys.exit(1)


PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
SKIP = "\033[33mSKIP\033[0m"


def _request(method: str, url: str, headers: dict | None = None,
             body: bytes | None = None, timeout: int = 60) -> tuple[int, dict | str]:
    req = urllib.request.Request(url, method=method, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except Exception as exc:
        return 0, str(exc)


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = PASS if ok else FAIL
    suffix = f" — {detail}" if detail else ""
    print(f"  {status}  {label}{suffix}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="DemandOS production smoke test")
    parser.add_argument("--base-url", required=True, help="Base URL of deployed app")
    parser.add_argument("--api-key", default="", help="DEMANDOS_API_KEY for write endpoints")
    parser.add_argument("--run-pipeline", action="store_true",
                        help="Run the full demo pipeline (requires --api-key)")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    api_key = args.api_key.strip()
    run_pipeline = args.run_pipeline

    read_headers: dict[str, str] = {}
    write_headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        write_headers["X-DemandOS-API-Key"] = api_key

    results: list[bool] = []

    print()
    print("DemandOS Production Smoke Test")
    print(f"Target: {base}")
    print("=" * 60)
    print()

    # -----------------------------------------------------------------------
    # 1. GET /api/readiness
    # -----------------------------------------------------------------------
    print("[ 1 ] Readiness probe")
    status, body = _request("GET", f"{base}/api/readiness", read_headers)
    ok1 = check("GET /api/readiness returns 200", status == 200, f"HTTP {status}")
    ready_data: dict[str, Any] = body if isinstance(body, dict) else {}
    ok2 = check("ready field is present", "ready" in ready_data, str(ready_data)[:80])
    ok3 = check("ready is true", ready_data.get("ready") is True,
                f"ready={ready_data.get('ready')}")
    results += [ok1, ok2, ok3]

    # -----------------------------------------------------------------------
    # 2. Homepage data endpoint (GET /api/dashboard/overview)
    # -----------------------------------------------------------------------
    print()
    print("[ 2 ] Homepage data endpoint")
    status, body = _request("GET", f"{base}/api/dashboard/overview", read_headers)
    ok = check("GET /api/dashboard/overview returns 200", status == 200, f"HTTP {status}")
    results.append(ok)

    # -----------------------------------------------------------------------
    # 3. GET /api/overview
    # -----------------------------------------------------------------------
    print()
    print("[ 3 ] Overview endpoint")
    status, body = _request("GET", f"{base}/api/overview", read_headers)
    ok = check("GET /api/overview returns 200", status == 200, f"HTTP {status}")
    overview_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)

    # -----------------------------------------------------------------------
    # 4. GET /api/data-health
    # -----------------------------------------------------------------------
    print()
    print("[ 4 ] Data health endpoint")
    status, body = _request("GET", f"{base}/api/data-health", read_headers)
    ok = check("GET /api/data-health returns 200", status == 200, f"HTTP {status}")
    dh_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)

    # -----------------------------------------------------------------------
    # 5. GET /api/dashboard/forecast-summary
    # -----------------------------------------------------------------------
    print()
    print("[ 5 ] Forecast summary endpoint")
    status, body = _request("GET", f"{base}/api/dashboard/forecast-summary", read_headers)
    ok = check("GET /api/dashboard/forecast-summary returns 200", status == 200, f"HTTP {status}")
    forecast_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)

    # -----------------------------------------------------------------------
    # 6. GET /api/dashboard/risk-summary
    # -----------------------------------------------------------------------
    print()
    print("[ 6 ] Risk summary endpoint")
    status, body = _request("GET", f"{base}/api/dashboard/risk-summary", read_headers)
    ok = check("GET /api/dashboard/risk-summary returns 200", status == 200, f"HTTP {status}")
    risk_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)

    # -----------------------------------------------------------------------
    # 7. GET /api/dashboard/recommendation-summary
    # -----------------------------------------------------------------------
    print()
    print("[ 7 ] Recommendation summary endpoint")
    status, body = _request("GET", f"{base}/api/dashboard/recommendation-summary", read_headers)
    ok = check("GET /api/dashboard/recommendation-summary returns 200", status == 200, f"HTTP {status}")
    rec_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)

    # -----------------------------------------------------------------------
    # 8. GET /api/dashboard/model-summary
    # -----------------------------------------------------------------------
    print()
    print("[ 8 ] Model summary endpoint")
    status, body = _request("GET", f"{base}/api/dashboard/model-summary", read_headers)
    ok = check("GET /api/dashboard/model-summary returns 200", status == 200, f"HTTP {status}")
    model_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)

    # -----------------------------------------------------------------------
    # 9. GET /api/demo/pipeline-runs/latest
    # -----------------------------------------------------------------------
    print()
    print("[ 9 ] Pipeline latest run endpoint")
    status, body = _request("GET", f"{base}/api/demo/pipeline-runs/latest", read_headers)
    ok = check("GET /api/demo/pipeline-runs/latest returns 200 or 404",
               status in (200, 404), f"HTTP {status}")
    pipeline_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)

    # -----------------------------------------------------------------------
    # 10. Verify deployed mode is vercel
    # -----------------------------------------------------------------------
    print()
    print("[ 10 ] Runtime mode")
    runtime_mode = ready_data.get("runtime_mode")
    ok = check("runtime_mode is vercel", runtime_mode == "vercel",
               f"runtime_mode={runtime_mode!r}")
    results.append(ok)

    # -----------------------------------------------------------------------
    # 11. Verify demo scale is small
    # -----------------------------------------------------------------------
    print()
    print("[ 11 ] Demo scale")
    demo_scale = ready_data.get("demo_scale")
    ok = check("demo_scale is small", demo_scale == "small",
               f"demo_scale={demo_scale!r}")
    results.append(ok)

    # -----------------------------------------------------------------------
    # 12. Verify core counts are nonzero (only meaningful after pipeline ran)
    # -----------------------------------------------------------------------
    print()
    print("[ 12 ] Core data counts")
    raw_counts: dict[str, Any] = {}
    # Try to get from dashboard/overview
    status, body = _request("GET", f"{base}/api/dashboard/overview", read_headers)
    if isinstance(body, dict):
        raw_counts = body.get("raw_counts", {})
    products_count = raw_counts.get("products", 0)
    orders_count = raw_counts.get("orders", 0)

    if products_count == 0 and orders_count == 0:
        check("core counts (products, orders)",
              False, "0 products and 0 orders — pipeline may not have run yet")
        results.append(False)
    else:
        ok_products = check("products count > 0", products_count > 0,
                            f"products={products_count}")
        ok_orders = check("orders count > 0", orders_count > 0,
                          f"orders={orders_count}")
        results += [ok_products, ok_orders]

    # -----------------------------------------------------------------------
    # 13. Verify recommendations count is nonzero
    # -----------------------------------------------------------------------
    print()
    print("[ 13 ] Recommendations count")
    status, body = _request("GET", f"{base}/api/dashboard/recommendation-summary", read_headers)
    rec_summary: dict[str, Any] = body if isinstance(body, dict) else {}
    has_rec_run = rec_summary.get("has_recommendation_run", False)
    if not has_rec_run:
        check("recommendations (pipeline not yet run)", False,
              "No recommendation run found — run pipeline first")
        results.append(False)
    else:
        rows = rec_summary.get("latest_run", {}).get("rows_created", 0) or 0
        ok = check("recommendation rows > 0", rows > 0, f"rows_created={rows}")
        results.append(ok)

    # -----------------------------------------------------------------------
    # 14. Verify no endpoint leaks the API key value
    # -----------------------------------------------------------------------
    print()
    print("[ 14 ] Secret leak check — API key")
    endpoints_to_scan = [
        "/api/readiness",
        "/api/overview",
        "/api/data-health",
        "/api/dashboard/overview",
        "/api/dashboard/forecast-summary",
        "/api/dashboard/risk-summary",
        "/api/dashboard/recommendation-summary",
        "/api/dashboard/model-summary",
        "/api/observability/runs-summary",
    ]
    key_leaked = False
    leak_source = ""
    for ep in endpoints_to_scan:
        _, raw_body = _request("GET", f"{base}{ep}", read_headers)
        raw_str = json.dumps(raw_body) if isinstance(raw_body, dict) else str(raw_body)
        if api_key and len(api_key) >= 8 and api_key in raw_str:
            key_leaked = True
            leak_source = ep
            break
        # Check for generic API key field with value
        if '"DEMANDOS_API_KEY"' in raw_str and api_key and api_key in raw_str:
            key_leaked = True
            leak_source = ep
            break
    if api_key:
        ok = check("API key not found in any response body", not key_leaked,
                   f"Leaked in {leak_source}" if key_leaked else "")
    else:
        print(f"  {SKIP}  API key leak check (no --api-key provided; skipping value check)")
        ok = True
    results.append(ok)

    # -----------------------------------------------------------------------
    # 15. Verify no endpoint returns local SQLite path or secret database URL
    # -----------------------------------------------------------------------
    print()
    print("[ 15 ] Secret leak check — database URL / SQLite path")
    db_leaked = False
    db_leak_source = ""
    db_patterns = [
        "sqlite:///", "sqlite://",
        "postgresql://", "postgres://",
        "@neon.tech", "DATABASE_URL",
        "demandos_dev.db",
        "/var/", "C:\\Users\\",
    ]
    for ep in endpoints_to_scan:
        _, raw_body = _request("GET", f"{base}{ep}", read_headers)
        raw_str = json.dumps(raw_body) if isinstance(raw_body, dict) else str(raw_body)
        for pattern in db_patterns:
            if pattern.lower() in raw_str.lower():
                db_leaked = True
                db_leak_source = f"{ep} ({pattern!r})"
                break
        if db_leaked:
            break
    ok = check("No DB URL or SQLite path in responses", not db_leaked,
               f"Found in {db_leak_source}" if db_leaked else "")
    results.append(ok)

    # -----------------------------------------------------------------------
    # Sprint 13 — read-only checks for new endpoints
    # -----------------------------------------------------------------------
    print()
    print("[ S13-1 ] Connector status")
    status, body = _request("GET", f"{base}/api/connectors/status", read_headers)
    ok = check("GET /api/connectors/status returns 200", status == 200, f"HTTP {status}")
    conn_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)
    if ok:
        ok2 = check("live_sync_enabled is False",
                    conn_data.get("live_sync_enabled") is False,
                    f"live_sync_enabled={conn_data.get('live_sync_enabled')!r}")
        results.append(ok2)

    print()
    print("[ S13-2 ] Monitoring latest")
    status, body = _request("GET", f"{base}/api/monitoring/latest", read_headers)
    ok = check("GET /api/monitoring/latest returns 200", status == 200, f"HTTP {status}")
    mon_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)
    if ok:
        ok2 = check("monitoring response has has_monitoring_run",
                    "has_monitoring_run" in mon_data,
                    str(mon_data)[:80])
        results.append(ok2)

    print()
    print("[ S13-3 ] Scenario runs latest")
    status, body = _request("GET", f"{base}/api/scenarios/runs/latest", read_headers)
    ok = check("GET /api/scenarios/runs/latest returns 200", status == 200, f"HTTP {status}")
    scen_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)
    if ok:
        ok2 = check("scenario response has has_scenario_run",
                    "has_scenario_run" in scen_data,
                    str(scen_data)[:80])
        ok3 = check("simulated label present", scen_data.get("simulated") is True or
                    (not scen_data.get("has_scenario_run")),
                    f"simulated={scen_data.get('simulated')!r}")
        results += [ok2, ok3]

    print()
    print("[ S13-4 ] CSV uploads latest")
    status, body = _request("GET", f"{base}/api/csv/uploads/latest", read_headers)
    ok = check("GET /api/csv/uploads/latest returns 200", status == 200, f"HTTP {status}")
    csv_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)
    if ok:
        ok2 = check("csv response has has_uploads",
                    "has_uploads" in csv_data,
                    str(csv_data)[:80])
        results.append(ok2)

    print()
    print("[ S13-5 ] CSV templates")
    status, body = _request("GET", f"{base}/api/csv/templates", read_headers)
    ok = check("GET /api/csv/templates returns 200", status == 200, f"HTTP {status}")
    tmpl_data: dict[str, Any] = body if isinstance(body, dict) else {}
    results.append(ok)
    if ok:
        ok2 = check("templates has products",
                    "products" in tmpl_data.get("templates", {}),
                    "")
        results.append(ok2)

    # -----------------------------------------------------------------------
    # Optional: run full pipeline (only with --run-pipeline)
    # -----------------------------------------------------------------------
    if run_pipeline:
        print()
        print("[ + ] Running full demo pipeline (--run-pipeline set)")
        if not api_key:
            print(f"  {SKIP}  Pipeline run skipped — no --api-key provided")
        else:
            payload = json.dumps({}).encode("utf-8")
            print("      Triggering POST /api/demo/run-full-pipeline ...")
            start = time.time()
            status, body = _request("POST", f"{base}/api/demo/run-full-pipeline",
                                    write_headers, payload, timeout=120)
            elapsed = round(time.time() - start, 1)
            ok = check(f"Pipeline run completed in {elapsed}s",
                       status == 200 and isinstance(body, dict) and body.get("status") in ("completed", "ok"),
                       f"HTTP {status}, status={body.get('status', '?') if isinstance(body, dict) else '?'}")
            results.append(ok)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print()
    print("=" * 60)
    passed = sum(results)
    failed = len(results) - passed
    print(f"Results: {passed} passed, {failed} failed")
    print()
    if failed == 0:
        print("\033[32m✅ All smoke checks PASSED\033[0m")
        return 0
    else:
        print(f"\033[31m❌ {failed} smoke check(s) FAILED\033[0m")
        return 1


if __name__ == "__main__":
    sys.exit(main())
