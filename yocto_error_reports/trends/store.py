"""Append-only run store for cross-run trends (SPEC-006 §1).

Each run is projected to one **privacy-safe** JSON-Lines record keyed by the
stable `signature` (SPEC-002 §4): redacted title + signature + minimal metadata
and counts — **never** evidence, `local_conf`/`auto_conf`, or input paths.
Appending never rewrites earlier lines; reading tolerates an absent/empty store
and skips malformed lines. Stdlib-only; the store is a local file (gitignored).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..models import Report
from ..redact import redact_host_identity

# Default local store; gitignored (never committed).
DEFAULT_STORE = Path(".yer/trends.jsonl")


@dataclass
class FindingRow:
    """The privacy-safe projection of one finding into the store."""

    signature: str = ""
    category: str = "unknown"
    severity: str = "error"
    recipe: str | None = None
    title: str = ""  # host-identity redacted before storage


@dataclass
class RunRecord:
    """One recorded run (§1). `recorded_at` is wall-clock — the store is history."""

    run_id: str = ""
    recorded_at: str = ""
    tool_version: str = ""
    source_count: int = 0
    findings: list[FindingRow] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_id(signatures: list[str], tool_version: str) -> str:
    """Stable id from the sorted signature set + tool version (§1)."""
    payload = "\n".join(sorted(signatures)) + "\n" + tool_version
    return "sha1:" + hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _summary(report: Report) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    for finding in report.findings:
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
    return {
        "errors": sum(1 for f in report.findings if f.severity == "error"),
        "warnings": sum(1 for f in report.findings if f.severity == "warning"),
        "by_category": by_category,
    }


def build_record(report: Report, *, tool_version: str, recorded_at: str | None = None) -> RunRecord:
    """Project a `Report` into a `RunRecord` (redacted, evidence-free)."""
    rows = [
        FindingRow(
            signature=f.signature,
            category=f.category,
            severity=f.severity,
            recipe=f.recipe,
            title=redact_host_identity(f.title),  # §1: titles stored redacted
        )
        for f in report.findings
    ]
    return RunRecord(
        run_id=_run_id([f.signature for f in report.findings], tool_version),
        recorded_at=recorded_at or _now_utc(),
        tool_version=tool_version,
        source_count=len(report.builds),  # a count, never the paths
        findings=rows,
        summary=_summary(report),
    )


def _record_to_dict(record: RunRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "recorded_at": record.recorded_at,
        "tool_version": record.tool_version,
        "source_count": record.source_count,
        "findings": [
            {
                "signature": row.signature,
                "category": row.category,
                "severity": row.severity,
                "recipe": row.recipe,
                "title": row.title,
            }
            for row in record.findings
        ],
        "summary": record.summary,
    }


def _record_from_dict(data: dict[str, Any]) -> RunRecord:
    findings = [
        FindingRow(
            signature=row.get("signature", ""),
            category=row.get("category", "unknown"),
            severity=row.get("severity", "error"),
            recipe=row.get("recipe"),
            title=row.get("title", ""),
        )
        for row in data.get("findings", [])
        if isinstance(row, dict)
    ]
    return RunRecord(
        run_id=data.get("run_id", ""),
        recorded_at=data.get("recorded_at", ""),
        tool_version=data.get("tool_version", ""),
        source_count=data.get("source_count", 0),
        findings=findings,
        summary=data.get("summary", {}),
    )


def record_run(
    report: Report,
    *,
    store_path: Path | str = DEFAULT_STORE,
    tool_version: str,
    recorded_at: str | None = None,
) -> RunRecord:
    """Append one run record to the JSONL store and return it (§1)."""
    record = build_record(report, tool_version=tool_version, recorded_at=recorded_at)
    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_record_to_dict(record), sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return record


def load_runs(store_path: Path | str = DEFAULT_STORE) -> list[RunRecord]:
    """Read all run records in chronological (file) order (§1).

    An absent/empty store yields `[]`; malformed lines are skipped defensively.
    """
    path = Path(store_path)
    if not path.is_file():
        return []
    runs: list[RunRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue  # skip junk, never fatal
        if isinstance(data, dict):
            runs.append(_record_from_dict(data))
    return runs
