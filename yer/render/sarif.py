"""SARIF 2.1.0 output for code-scanning (SPEC-004 §3).

Projects the analyzer's ranked findings into a single-`run` SARIF 2.1.0 document
so GitHub/GitLab can render code-scanning annotations. Deterministic (no
wall-clock timestamps; findings in rank order) and privacy-safe: titles are run
through the SPEC-004 §4 host-identity redaction, like the other artifacts.
Render-only module; the core stays stdlib-only.
"""

from __future__ import annotations

import json
from typing import Any

from ..models import Finding, Report
from ..redact import redact_host_identity

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
INFORMATION_URI = "https://github.com/robwoolley/yer"

# severity -> SARIF level (SPEC-004 §3). failure is fatal, so it maps to error;
# anomaly (and anything unknown) is advisory -> note.
_LEVEL = {"error": "error", "failure": "error", "warning": "warning", "anomaly": "note"}


def _level(severity: str) -> str:
    return _LEVEL.get(severity, "note")


def _rules(findings: list[Finding]) -> list[dict[str, Any]]:
    """One reportingDescriptor per distinct category, in first-appearance order."""
    seen: list[str] = []
    for finding in findings:
        if finding.category not in seen:
            seen.append(finding.category)
    return [{"id": category, "name": category} for category in seen]


def _result(finding: Finding) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ruleId": finding.category,
        "level": _level(finding.severity),
        "message": {"text": redact_host_identity(finding.title)},
    }
    # physicalLocation only when we actually have a file (SPEC-004 §3).
    if finding.file:
        physical: dict[str, Any] = {"artifactLocation": {"uri": finding.file}}
        if finding.line:
            physical["region"] = {"startLine": finding.line}
        result["locations"] = [{"physicalLocation": physical}]
    return result


def sarif_document(report: Report, *, tool_version: str) -> dict[str, Any]:
    """The SARIF 2.1.0 document as a Python dict (SPEC-004 §3)."""
    findings = report.findings
    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "yer",
                        "version": tool_version,
                        "informationUri": INFORMATION_URI,
                        "rules": _rules(findings),
                    }
                },
                "results": [_result(f) for f in findings],
            }
        ],
    }


def to_sarif(report: Report, *, tool_version: str) -> str:
    """Serialize the SARIF 2.1.0 document (deterministic, byte-stable)."""
    return json.dumps(sarif_document(report, tool_version=tool_version), indent=2, sort_keys=True)
