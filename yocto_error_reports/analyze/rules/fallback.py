"""Fallback rule (SPEC-002 §2): guarantee every failure yields >=1 finding.

Applied by the orchestrator only when no category rule matched, so nothing is
silently lost. Title is the first `ERROR` line, else the last `WARNING`, else the
failure's task/message. Category `unknown`; low confidence.
"""

from __future__ import annotations

from ...models import Failure, Finding, LogLine
from ..evidence import build_evidence
from ..signatures import Rule, set_fallback


def _pick_line(lines: list[LogLine]) -> tuple[LogLine | None, str]:
    error = next((line for line in lines if line.level == "ERROR"), None)
    if error is not None:
        return error, "error"
    warnings = [line for line in lines if line.level == "WARNING"]
    if warnings:
        return warnings[-1], "warning"
    return None, "error"


def _always(failure: Failure, lines: list[LogLine]) -> bool:
    return True


def _extract(failure: Failure, lines: list[LogLine]) -> Finding | None:
    line, severity = _pick_line(lines)
    if line is not None:
        title, focus = line.text, line.n
    else:
        title, focus = (failure.task or "unknown failure").strip(), None
    return Finding(
        category="unknown",
        severity=severity,
        title=title,
        recipe=failure.recipe or failure.package,
        task=failure.task if failure.kind == "task" else None,
        evidence=build_evidence(lines, focus),
        confidence=0.3,
    )


FALLBACK_RULE = Rule(
    name="fallback",
    category="unknown",
    severity="error",
    match=_always,
    extract=_extract,
    confidence=0.3,
    order=1000,
)

set_fallback(FALLBACK_RULE)
