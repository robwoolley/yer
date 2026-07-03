"""Ingest: load `error-report.txt` files into schema-tolerant `Build` objects.

SPEC-001 §1. Parsing is **defensive** (data-format §"Robustness rules"): the file
extension is opaque (detect via JSON parse), every field is optional and accessed
with `.get()`, unknown keys are preserved in `Build.raw`, and `failures` may be
absent or empty. Stdlib-only per SPEC-000 NFR1.

M1-01 covers loading a single well-formed report. Malformed input (SPEC-001 §1
error handling / T2) is handled in M1-03; multi-input resolution in M1-02.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Build, Failure


def _failure_from(obj: dict[str, Any]) -> Failure:
    task = obj.get("task")
    # A `do_*` task name is a real task failure; anything else (e.g. a
    # "Nothing provides '…'" message) is a dependency/parse failure. (SPEC-001 §1)
    kind = "task" if isinstance(task, str) and task.startswith("do_") else "message"
    log = obj.get("log")
    return Failure(
        task=task,
        package=obj.get("package"),
        recipe=obj.get("recipe"),
        log=log if isinstance(log, str) else "",
        kind=kind,
    )


def build_from_report(data: dict[str, Any], source_path: str) -> Build:
    """Map a parsed report dict onto a `Build`. Never indexes a missing key."""
    raw_failures = data.get("failures")
    failures = (
        [_failure_from(f) for f in raw_failures if isinstance(f, dict)]
        if isinstance(raw_failures, list)
        else []
    )
    return Build(
        component=data.get("component"),
        machine=data.get("machine"),
        distro=data.get("distro"),
        build_sys=data.get("build_sys"),
        target_sys=data.get("target_sys"),
        bitbake_version=data.get("bitbake_version"),
        branch_commit=data.get("branch_commit"),
        failures=failures,
        raw=data,
        source_path=source_path,
    )


def load_report(path: str | Path) -> Build:
    """Load one report file into a `Build`. Extension is opaque — detect by JSON.

    Raises on malformed JSON; SPEC-001 §1 error handling (a parse-finding `Build`
    instead of raising) arrives in M1-03.
    """
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return build_from_report(data, str(p))
