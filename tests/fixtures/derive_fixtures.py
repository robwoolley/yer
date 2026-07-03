#!/usr/bin/env python3
"""Derive anonymized test fixtures from the real `error-reports/` corpus.

Fixtures are curated, privacy-scrubbed copies of real reports (one per failure
category, plus the SPEC-002 T3 "compile task that is really configure" case).

Two scrubbing passes are applied (see tests/fixtures/README.md):
  1. `local_conf`/`auto_conf` are replaced wholesale with a placeholder.
  2. Host-identity tokens are redacted from **all** string values. The reporter
     anchors most build paths to `TOPDIR/...`, but it does NOT anonymize
     `do_fetch` environment dumps (an ssh-agent socket path) or the dependency
     `RPROVIDES` message (an absolute build root), which leak a username /
     hostname. These are redacted by **structure**, so this script names no
     specific host, mount, or user.

An optional, git-ignored `redactions.local` (JSON list of `[regex, replacement]`)
can add site-specific pairs without committing them.

Run from the repo root:  python tests/fixtures/derive_fixtures.py
Requires the local `error-reports/` corpus (gitignored); the generated *.json
fixtures are committed so contributors without the corpus can still run tests.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent.parent
CORPUS = REPO / "error-reports"
OUT = REPO / "tests" / "fixtures"
LOCAL_REDACTIONS = OUT / "redactions.local"  # git-ignored, optional

SCRUB_PLACEHOLDER = "<scrubbed for fixture — see tests/fixtures/README.md>"
SCRUB_KEYS = ("local_conf", "auto_conf")

# Structural host-identity redactions — named by shape, not by any real token:
#   * an `SSH_AUTH_SOCK` value (leaks a user + home layout);
#   * an absolute `/<seg>/<seg>/<YYYY-MM-DD>/...` build root (leaks host + user).
_REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'SSH_AUTH_SOCK="[^"]*"'), 'SSH_AUTH_SOCK="<redacted>"'),
    (re.compile(r"/[\w.+-]+/[\w.+-]+/\d{4}-\d{2}-\d{2}"), "HOSTDIR"),
]

# Anything matching this after redaction is a residual host-identity leak.
_LEAK_SCAN = re.compile(
    r'SSH_AUTH_SOCK="(?!<redacted>)'
    r"|/[\w.+-]+/[\w.+-]+/\d{4}-\d{2}-\d{2}/"
    r"|/\w[\w.+-]*/\w[\w.+-]*/\.(?:gnupg|ssh)/"
)

# (source report, output fixture, category, why this sample)
MANIFEST = [
    ("error_report_20260701233825.txt", "compile_nanoflann.json", "compile",
     "single do_compile; genuine gcc error `cc1plus: error: unknown value 'native'`"),
    ("error_report_20260701180755.txt", "configure_gz-gui9.json", "configure",
     "single do_configure; Qt6 NOT FOUND + BB backtrace block (SPEC-001 T6)"),
    ("error_report_20260701102212.txt", "patch_ogre-next.json", "patch",
     "single do_patch; Hunk failure in OgreMathlibNEON.h line 601 (SPEC-002 T4)"),
    ("error_report_20260701170335.txt", "qa_gz-physics-vendor.json", "qa",
     "single do_package_qa; many near-identical symlink QA lines (SPEC-002 T2)"),
    ("error_report_20260630205004.txt", "fetch_dartsim.json", "fetch",
     "the corpus's only do_fetch (dartsim); multi-failure, also large compile logs"),
    ("error_report_20260701200813.txt", "dependency_moveit.json", "dependency",
     "`Nothing provides ...`; recipe absent -> kind=message (SPEC-001 T3/T4)"),
    ("error_report_20260701151947.txt", "compile_gz-sim-vendor.json", "compile/configure",
     "do_compile that classifies as configure (Qt6 NOT FOUND) — SPEC-002 T3"),
]


def _load_local_redactions() -> list[tuple[re.Pattern[str], str]]:
    if not LOCAL_REDACTIONS.exists():
        return []
    pairs = json.loads(LOCAL_REDACTIONS.read_text(encoding="utf-8"))
    return [(re.compile(pat), repl) for pat, repl in pairs]


def _redact_text(text: str, extra: list[tuple[re.Pattern[str], str]]) -> str:
    for pattern, replacement in (*_REDACTIONS, *extra):
        text = pattern.sub(replacement, text)
    return text


def scrub(obj: Any, extra: list[tuple[re.Pattern[str], str]]) -> Any:
    """Recursively scrub config keys and host-identity tokens from a report."""
    if isinstance(obj, dict):
        return {
            key: SCRUB_PLACEHOLDER if key in SCRUB_KEYS else scrub(value, extra)
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [scrub(item, extra) for item in obj]
    if isinstance(obj, str):
        return _redact_text(obj, extra)
    return obj


def main() -> int:
    if not CORPUS.is_dir():
        print(f"error: corpus not found at {CORPUS} (it is gitignored)")
        return 2
    extra = _load_local_redactions()
    OUT.mkdir(parents=True, exist_ok=True)
    leaked = []
    for source, output, category, why in MANIFEST:
        report = json.loads((CORPUS / source).read_text(encoding="utf-8"))
        text = json.dumps(scrub(report, extra), indent=2, ensure_ascii=False) + "\n"
        if _LEAK_SCAN.search(text):
            leaked.append(output)
        (OUT / output).write_text(text, encoding="utf-8")
        print(f"[{category:17}] {source} -> {output}  ({why})")
    if leaked:
        print(f"\nERROR: residual host-identity leak in: {leaked}")
        return 1
    print(f"\nwrote {len(MANIFEST)} fixtures to {OUT} (no host-identity leaks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
