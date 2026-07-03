#!/usr/bin/env python3
"""Derive anonymized test fixtures from the real `error-reports/` corpus.

Fixtures are curated, privacy-scrubbed copies of real reports (one per failure
category, plus the SPEC-002 T3 "compile task that is really configure" case).
The *only* transform applied is scrubbing `local_conf`/`auto_conf` — every build
path in these samples is already `TOPDIR/...`-anchored by the reporter, so no
host identity leaks (verified: no /home, usernames, or emails in the corpus).

Run from the repo root:  python tests/fixtures/derive_fixtures.py
Requires the local `error-reports/` corpus (gitignored); the generated *.json
fixtures are committed so contributors without the corpus can still run tests.

Provenance is documented in tests/fixtures/README.md.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
CORPUS = REPO / "error-reports"
OUT = REPO / "tests" / "fixtures"

SCRUB_PLACEHOLDER = "<scrubbed for fixture — see tests/fixtures/README.md>"
SCRUB_KEYS = ("local_conf", "auto_conf")

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


def scrub(report: dict) -> dict:
    """Return a copy with sensitive config fields replaced by a placeholder."""
    out = dict(report)
    for key in SCRUB_KEYS:
        if key in out:
            out[key] = SCRUB_PLACEHOLDER
    return out


def main() -> int:
    if not CORPUS.is_dir():
        print(f"error: corpus not found at {CORPUS} (it is gitignored)")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    for source, output, category, why in MANIFEST:
        src = CORPUS / source
        report = json.loads(src.read_text(encoding="utf-8"))
        cleaned = scrub(report)
        text = json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n"
        (OUT / output).write_text(text, encoding="utf-8")
        print(f"[{category:17}] {source} -> {output}  ({why})")
    print(f"\nwrote {len(MANIFEST)} fixtures to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
