"""Canonical, deterministic `report.json` (SPEC-004 §1).

Stable key order, findings in the analyzer's rank order (SPEC-002 §6), and **no
wall-clock timestamps** in the document body — the same input yields byte-
identical output (NFR3). Stdlib-only. Host-identity redaction of evidence is
layered on in M4-02.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import Build, Finding, FindingGroup, Report

SCHEMA_VERSION = "1.0"


def _build_dict(build: Build) -> dict[str, Any]:
    return {
        "component": build.component,
        "machine": build.machine,
        "distro": build.distro,
        "source": Path(build.source_path).name if build.source_path else "",
        "failure_count": len(build.failures),
    }


def _finding_dict(finding: Finding, groups: dict[str, FindingGroup]) -> dict[str, Any]:
    group = groups.get(finding.signature)
    return {
        "category": finding.category,
        "severity": finding.severity,
        "confidence": finding.confidence,
        "title": finding.title,
        "recipe": finding.recipe,
        "task": finding.task,
        "file": finding.file,
        "line": finding.line,
        "evidence": finding.evidence,
        "signature": finding.signature,
        "cascade_of": finding.cascade_of,
        "occurrences": group.occurrences if group else 1,
        "affected_recipes": (
            group.affected_recipes if group else ([finding.recipe] if finding.recipe else [])
        ),
    }


def report_document(report: Report, *, tool_version: str) -> dict[str, Any]:
    """The canonical `report.json` as a Python dict (SPEC-004 §1)."""
    groups = {g.signature: g for g in report.groups}
    by_category: dict[str, int] = {}
    for finding in report.findings:
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": tool_version,
        "builds": [_build_dict(b) for b in report.builds],
        "findings": [_finding_dict(f, groups) for f in report.findings],
        "summary": {
            "errors": sum(1 for f in report.findings if f.severity == "error"),
            "warnings": sum(1 for f in report.findings if f.severity == "warning"),
            "by_category": by_category,
        },
    }


def to_report_json(report: Report, *, tool_version: str) -> str:
    """Serialize the canonical `report.json` (deterministic, byte-stable)."""
    return json.dumps(report_document(report, tool_version=tool_version), indent=2, sort_keys=True)
