#!/usr/bin/env python3
"""
Capture portfolio screenshots from the deployed DemandOS Vercel app using Playwright.

Usage:
    python scripts/capture_screenshots.py --base-url https://demand-os-three.vercel.app
    python scripts/capture_screenshots.py --base-url http://localhost:3000

Screenshots are saved to docs/screenshots/.
"""
import argparse
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


BASE_URL = "https://demand-os-three.vercel.app"
OUT_DIR = Path(__file__).parent.parent / "docs" / "screenshots"

SCREENSHOTS = [
    {
        "filename": "01-readiness.png",
        "url": "/api/readiness",
        "wait": "networkidle",
        "desc": "Readiness JSON response — proves Vercel + Neon connected",
        "viewport": {"width": 1280, "height": 800},
    },
    {
        "filename": "02-home-dashboard.png",
        "url": "/",
        "wait": "networkidle",
        "desc": "Home dashboard with populated KPI cards",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "03-pipeline-completed.png",
        "url": "/pipeline",
        "wait": "networkidle",
        "desc": "Pipeline Controls page with completed run log",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "04-forecasts.png",
        "url": "/forecasts",
        "wait": "networkidle",
        "desc": "Forecasts page with p10/p50/p90 line chart",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "05-inventory-risk.png",
        "url": "/risks",
        "wait": "networkidle",
        "desc": "Inventory Risk page with risk tier queue",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "06-recommendations.png",
        "url": "/recommendations",
        "wait": "networkidle",
        "desc": "Recommendations page with urgency queue",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "07-model-performance.png",
        "url": "/model-performance",
        "wait": "networkidle",
        "desc": "Model Performance page — ML vs baseline comparison",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "08-data-health.png",
        "url": "/data-health",
        "wait": "networkidle",
        "desc": "Data Health page with table counts and checks",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "13-csv-upload.png",
        "url": "/csv-upload",
        "wait": "networkidle",
        "desc": "CSV upload page with raw-data constraints and validation workflow",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "14-monitoring.png",
        "url": "/monitoring",
        "wait": "networkidle",
        "desc": "Monitoring page with latest-vs-previous health comparisons",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "15-scenarios.png",
        "url": "/scenarios",
        "wait": "networkidle",
        "desc": "Scenario planning page with simulated before/after comparison",
        "viewport": {"width": 1440, "height": 900},
    },
    {
        "filename": "16-connectors.png",
        "url": "/connectors",
        "wait": "networkidle",
        "desc": "Disabled connector readiness and no-network dry-run controls",
        "viewport": {"width": 1440, "height": 900},
    },
]


def capture(base_url: str, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()

        for s in SCREENSHOTS:
            url = base_url.rstrip("/") + s["url"]
            outpath = out_dir / s["filename"]
            print(f"  Capturing {s['filename']} — {url}")
            try:
                page.set_viewport_size(s["viewport"])
                page.goto(url, timeout=30000)
                page.wait_for_load_state(s["wait"], timeout=20000)
                # Give charts time to render
                time.sleep(1.5)
                page.screenshot(path=str(outpath), full_page=False)
                results[s["filename"]] = "captured"
                print(f"    ✅ saved → {outpath}")
            except Exception as e:
                results[s["filename"]] = f"FAILED: {e}"
                print(f"    ❌ {e}")

        browser.close()

    return results


def product_drilldown(base_url: str, out_dir: Path) -> str:
    """Capture product drilldown — need to find a valid product ID first."""
    import urllib.request, json
    product_id = None

    # Try recommendations/latest (has 'recommendations' key)
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/recommendations/latest", timeout=10) as r:
            data = json.loads(r.read())
        recs = data.get("recommendations", data.get("rows", []))
        if recs:
            product_id = recs[0].get("product_id")
    except Exception:
        pass

    if not product_id:
        # Try risks/latest
        try:
            with urllib.request.urlopen(base_url.rstrip("/") + "/api/risks/latest", timeout=10) as r:
                data = json.loads(r.read())
            rows = data.get("risks", data.get("rows", []))
            if rows:
                product_id = rows[0].get("product_id")
        except Exception:
            pass

    if not product_id:
        print("  ⚠️  Could not determine product ID for drilldown — skipping 09-product-drilldown.png")
        return "SKIPPED: no product_id found"

    outpath = out_dir / "09-product-drilldown.png"
    url = base_url.rstrip("/") + f"/products/{product_id}"
    print(f"  Capturing 09-product-drilldown.png — {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(1.5)
            page.screenshot(path=str(outpath), full_page=False)
            print(f"    ✅ saved → {outpath}")
            result = "captured"
        except Exception as e:
            result = f"FAILED: {e}"
            print(f"    ❌ {e}")
        browser.close()

    return result


def main():
    parser = argparse.ArgumentParser(description="Capture DemandOS portfolio screenshots via Playwright")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    print(f"DemandOS Screenshot Capture")
    print(f"Target: {args.base_url}")
    print(f"Output: {out_dir}")
    print("=" * 60)
    print()

    results = capture(args.base_url, out_dir)

    print()
    print("  Capturing product drilldown...")
    results["09-product-drilldown.png"] = product_drilldown(args.base_url, out_dir)

    print()
    print("=" * 60)
    print("Screenshots 10-12 require manual capture:")
    print("  10-vercel-deployment.png  — Vercel project dashboard (redact secrets)")
    print("  11-neon-connection-redacted.png — Neon integration panel (redact connection string)")
    print("  12-ci-passing.png         — GitHub Actions latest run (all jobs green)")
    print()

    captured = sum(1 for v in results.values() if v == "captured")
    failed   = sum(1 for v in results.values() if v.startswith("FAILED"))
    skipped  = sum(1 for v in results.values() if v.startswith("SKIPPED"))

    print(f"Results: {captured} captured, {failed} failed, {skipped} skipped")
    print("Pending manual capture: 3 (10, 11, 12)")

    if failed > 0:
        print("\nFailed:")
        for k, v in results.items():
            if v.startswith("FAILED"):
                print(f"  {k}: {v}")
        sys.exit(1)


if __name__ == "__main__":
    main()
