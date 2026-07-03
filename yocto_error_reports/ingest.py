"""Ingest: load `error-report.txt` files into schema-tolerant `Build` objects.

SPEC-001 §1. Parsing is **defensive** (data-format §"Robustness rules"): the file
extension is opaque (detect via JSON parse), every field is optional and accessed
with `.get()`, unknown keys are preserved in `Build.raw`, and `failures` may be
absent or empty. Stdlib-only per SPEC-000 NFR1.

M1-01 covers loading a single well-formed report; M1-02 adds multi-source
resolution (paths, globs, directories, stdin). Malformed input (SPEC-001 §1
error handling / T2) is handled in M1-03.
"""

from __future__ import annotations

import glob as _glob
import json
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .models import Build, Failure

STDIN = "-"


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


def _try_report_dict(path: Path) -> dict[str, Any] | None:
    """Return the parsed report dict if `path` looks like a report, else None.

    Used for directory scanning: a report is a JSON **object**. Non-JSON or
    non-object files (READMEs, scripts, binaries) are skipped, not errors.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _iter_dir_reports(root: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        data = _try_report_dict(path)
        if data is not None:
            yield path, data


def _load_stdin() -> Build:
    data = json.loads(sys.stdin.read())
    return build_from_report(data, STDIN)


def load_reports(sources: Iterable[str | Path]) -> list[Build]:
    """Resolve mixed input sources into `Build`s, in stable input order.

    Each source is one of (SPEC-001 §1):
      - ``-``        → one report read from stdin;
      - a directory  → every file under it that parses as a report;
      - a file path or shell glob → the matching report file(s).

    Files reached more than once (glob overlap, a file inside a scanned dir) are
    de-duplicated by resolved path. Directory scans skip non-report files;
    explicitly named files are always loaded (malformed handling: M1-03).
    """
    builds: list[Build] = []
    seen: set[Path] = set()

    def _add(path: Path, build: Build) -> None:
        key = path.resolve()
        if key not in seen:
            seen.add(key)
            builds.append(build)

    for source in sources:
        if str(source) == STDIN:
            builds.append(_load_stdin())  # stdin has no path to de-dup on
            continue
        candidate = Path(source)
        if candidate.is_dir():
            for path, data in _iter_dir_reports(candidate):
                _add(path, build_from_report(data, str(path)))
        else:
            for match in sorted(_glob.glob(str(source), recursive=True)):
                mp = Path(match)
                if mp.is_file():
                    _add(mp, load_report(mp))
    return builds
