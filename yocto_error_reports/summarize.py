"""Summarize: project a ranked `Report` into a token-bounded `Summary` (SPEC-005).

Selection (§1): top-K findings by rank, ≤ M tail-biased evidence lines each,
trimmed so the whole summary fits the token budget (chars/4 heuristic) while
**always keeping** the rank-1 root cause (its title + at least the root error
line) even under a tiny budget. An honest `truncated` accounting records what was
cut. No network calls; stdlib-only. Privacy redaction of evidence lands in M3-05.
"""

from __future__ import annotations

from dataclasses import replace

from .models import Finding, Report, Summary

CHARS_PER_TOKEN = 4  # rough token estimate (SPEC-005 §5 chars/4 heuristic)
DEFAULT_BUDGET = 4000
DEFAULT_TOP_K = 5
DEFAULT_MAX_EVIDENCE = 8


def _tokens(text: str) -> int:
    return -(-len(text) // CHARS_PER_TOKEN)  # ceil division


def _finding_tokens(finding: Finding) -> int:
    return _tokens("\n".join([finding.title, *finding.evidence]))


def estimate_tokens(summary: Summary) -> int:
    """Approximate token size of a summary's findings (chars/4)."""
    return sum(_finding_tokens(f) for f in summary.findings)


def _count_lines(log: str) -> int:
    return log.count("\n") + 1 if log else 0


def _fit_finding(
    finding: Finding, max_evidence: int, token_budget: int, *, is_root: bool
) -> Finding:
    """Trim evidence (tail-biased) so title+evidence fits `token_budget`.

    The rank-1 root cause always keeps at least the last (root) evidence line.
    """
    if 0 <= max_evidence < len(finding.evidence):
        evidence = finding.evidence[-max_evidence:]
    else:
        evidence = list(finding.evidence)
    # drop leading lines until it fits (keep the tail — the real error)
    while evidence and _tokens("\n".join([finding.title, *evidence])) > token_budget:
        evidence = evidence[1:]
    if is_root and not evidence and finding.evidence:
        evidence = [finding.evidence[-1]]  # never drop the root error line
    return replace(finding, evidence=evidence)


def summarize(
    report: Report,
    *,
    budget: int = DEFAULT_BUDGET,
    top_k: int = DEFAULT_TOP_K,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> Summary:
    """Select a token-bounded subset of the ranked findings into a `Summary`."""
    selected: list[Finding] = []
    remaining = budget
    for index, finding in enumerate(report.findings[:top_k]):
        is_root = index == 0
        if not is_root and _tokens(finding.title) > remaining:
            break  # no room for another finding's essentials
        trimmed = _fit_finding(finding, max_evidence, remaining, is_root=is_root)
        selected.append(trimmed)
        remaining -= _finding_tokens(trimmed)
        if remaining <= 0:
            break

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
