#!/usr/bin/env python3
"""Audit version-controlled DemandOS files for public-release hygiene risks."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_TEXT_BYTES = 2_000_000
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
FORBIDDEN_FILENAMES = {".env", ".env.local", ".DS_Store"}
FORBIDDEN_SUFFIXES = {
    ".csv",
    ".db",
    ".joblib",
    ".parquet",
    ".pickle",
    ".pkl",
    ".sqlite",
    ".sqlite3",
}
IGNORED_PARTS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
CONTENT_RULES = {
    "private key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "live secret key": re.compile(r"\b(?:sk|pk)_live_[A-Za-z0-9_-]+"),
    "Vercel token value": re.compile(r"\bVERCEL_TOKEN\s*=\s*[^\s#<][^\s#]*"),
    "Neon API key value": re.compile(r"\bNEON_API_KEY\s*=\s*[^\s#<][^\s#]*"),
    "DemandOS API key value": re.compile(
        r"^\s*DEMANDOS_API_KEY\s*=\s*(?!$|<|\$\{|\$DEMANDOS_API_KEY)[^\s#]+",
        re.MULTILINE,
    ),
    "credential-bearing database URL": re.compile(
        r"postgres(?:ql)?://[^\s<>'\"]+@[^\s<>'\"]+",
        re.IGNORECASE,
    ),
}


def candidate_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = ROOT / raw.decode("utf-8", errors="surrogateescape")
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        paths.append(path)
    return paths


def is_text_candidate(path: Path) -> bool:
    return (
        path.suffix.lower() in TEXT_SUFFIXES
        or path.name in {".gitignore", ".env.example"}
    )


def main() -> int:
    failures: list[str] = []
    paths = candidate_paths()

    for path in paths:
        rel = path.relative_to(ROOT)
        if path.name in FORBIDDEN_FILENAMES:
            failures.append(f"forbidden file: {rel}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"generated data/model artifact: {rel}")
        if re.search(r" (?:2|3)(?:\.[^.]+)?$", path.name):
            failures.append(f"duplicate-style filename: {rel}")

        if not is_text_candidate(path) or path.stat().st_size > MAX_TEXT_BYTES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if rel == Path("scripts/public_readiness_check.py"):
            continue
        content_rule_exempt = (
            rel.parts[:3] == ("apps", "api", "tests")
            or rel == Path("scripts/verify.sh")
        )
        for label, pattern in CONTENT_RULES.items():
            if content_rule_exempt:
                continue
            if (
                rel == Path("docker-compose.yml")
                and label == "credential-bearing database URL"
                and "changeme@db" in text
            ):
                continue
            if pattern.search(text):
                failures.append(f"{label}: {rel}")

        if (rel == Path("README.md") or rel.parts[:1] == ("docs",)) and re.search(
            r"postgres(?:ql)?://", text, re.IGNORECASE
        ):
            failures.append(f"raw database URL syntax in public docs: {rel}")

    if failures:
        print("DemandOS public-readiness audit FAILED")
        for failure in sorted(set(failures)):
            print(f"  - {failure}")
        return 1

    print(
        "DemandOS public-readiness audit PASSED "
        f"({len(paths)} tracked/unignored files checked)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
