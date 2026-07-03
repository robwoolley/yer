"""Summarize: project a ranked `Report` into a token-bounded `Summary` (SPEC-005).

Selection (§1): top-K findings by rank, ≤ M tail-biased evidence lines each,
**always keeping** the rank-1 root cause even under a tiny budget. An honest
`truncated` accounting (findings omitted, log lines dropped) records what was cut.
No network calls; stdlib-only. Budget bounding is refined in M3-02; privacy
redaction of evidence in M3-05.
"""

from __future__ import annotations

from dataclasses import replace

from .models import Finding, Report, Summary

CHARS_PER_TOKEN = 4  # rough token estimate (SPEC-005 §5 chars/4 heuristic)
DEFAULT_BUDGET = 4000
DEFAULT_TOP_K = 5
DEFAULT_MAX_EVIDENCE = 8


def _estimate_tokens(finding: Finding) -> int:
    text = "\n".join([finding.title, *finding.evidence])
    return len(text) // CHARS_PER_TOKEN


def _trim_evidence(finding: Finding, max_evidence: int) -> Finding:
    if max_evidence >= 0 and len(finding.evidence) > max_evidence:
        # tail-biased: the real error sits near the end, before the BB backtrace
        return replace(finding, evidence=finding.evidence[-max_evidence:])
    return replace(finding, evidence=list(finding.evidence))


def _count_lines(log: str) -> int:
    return log.count("\n") + 1 if log else 0


def summarize(
    report: Report,
    *,
    budget: int = DEFAULT_BUDGET,
    top_k: int = DEFAULT_TOP_K,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> Summary:
    """Select a token-bounded subset of the ranked findings into a `Summary`."""
    selected: list[Finding] = []
    used = 0
    for finding in report.findings[:top_k]:
        trimmed = _trim_evidence(finding, max_evidence)
        cost = _estimate_tokens(trimmed)
        # always keep rank-1 (the root cause); stop adding once over budget
        if selected and used + cost > budget:
            break
        selected.append(trimmed)
        used += cost

    findings_omitted = len(report.findings) - len(selected)
    total_log_lines = sum(
        _count_lines(failure.log) for build in report.builds for failure in build.failures
    )
    kept_evidence = sum(len(f.evidence) for f in selected)
    log_lines_dropped = max(0, total_log_lines - kept_evidence)
    build = report.builds[0] if report.builds else None

    return Summary(
        build=build,
        findings=selected,
        findings_omitted=findings_omitted,
        log_lines_dropped=log_lines_dropped,
    )
