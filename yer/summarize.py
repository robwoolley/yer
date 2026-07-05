"""Summarize: project a ranked `Report` into a token-bounded `Summary` (SPEC-005).

Selection (§1): top-K findings by rank, ≤ M tail-biased evidence lines each,
trimmed so the whole summary fits the token budget (chars/4 heuristic) while
**always keeping** the rank-1 root cause (its title + at least the root error
line) even under a tiny budget. An honest `truncated` accounting records what was
cut. No network calls; stdlib-only. Privacy redaction of evidence lands in M3-05.
"""

from __future__ import annotations

import json
from dataclasses import replace

from .models import Build, Finding, Report, Summary
from .redact import redact_host_identity, redact_secrets

# Per-category hint for the LLM (SPEC-005 §3 `likely_cause`).
_LIKELY_CAUSE = {
    "configure": "configure-time error; a dependency may be missing from the sysroot (DEPENDS)",
    "compile": "compilation error; inspect the first compiler diagnostic",
    "patch": "a patch does not apply cleanly to this source version",
    "qa": "a packaging QA check failed",
    "fetch": "the source could not be fetched (URI, network, or checksum)",
    "dependency": "unresolved provider; a required recipe/PROVIDES is missing",
    "unknown": "see the evidence for the failing step",
}

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
    # redact host identity before selection so the summary is shareable and the
    # token budget accounts for the redacted text (SPEC-005 §4).
    title = redact_host_identity(finding.title)
    if 0 <= max_evidence < len(finding.evidence):
        source = finding.evidence[-max_evidence:]
    else:
        source = finding.evidence
    evidence = [redact_host_identity(line) for line in source]
    # drop leading lines until it fits (keep the tail — the real error)
    while evidence and _tokens("\n".join([title, *evidence])) > token_budget:
        evidence = evidence[1:]
    if is_root and not evidence and finding.evidence:
        evidence = [redact_host_identity(finding.evidence[-1])]  # never drop the root line
    return replace(finding, title=title, evidence=evidence)


def _config_text(build: Build | None) -> str | None:
    """Extract local_conf/auto_conf from a build, redacted (SPEC-005 §4)."""
    if build is None:
        return None
    parts = [
        value
        for key in ("local_conf", "auto_conf")
        if isinstance(value := build.raw.get(key), str) and value.strip()
    ]
    if not parts:
        return None
    return redact_secrets(redact_host_identity("\n".join(parts)))


def summarize(
    report: Report,
    *,
    budget: int = DEFAULT_BUDGET,
    top_k: int = DEFAULT_TOP_K,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
    include_config: bool = False,
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
        config=_config_text(build) if include_config else None,
    )


def _finding_location(finding: Finding) -> str:
    if not finding.file:
        return ""
    loc = finding.file + (f":{finding.line}" if finding.line else "")
    return f" at {loc}"


def _metadata_lines(build: Build | None, root: Finding | None) -> list[str]:
    lines: list[str] = []
    if build is None:
        return lines
    row1 = [
        f"{label}: {value}"
        for label, value in (
            ("machine", build.machine),
            ("distro", build.distro),
            ("target", build.target_sys),
        )
        if value
    ]
    row2 = [
        f"{label}: {value}"
        for label, value in (("bitbake", build.bitbake_version), ("branch", build.branch_commit))
        if value
    ]
    if row1:
        lines.append("- " + " · ".join(row1))
    if row2:
        lines.append("- " + " · ".join(row2))
    return lines


def _truncation_note(summary: Summary) -> str | None:
    parts = []
    if summary.findings_omitted:
        parts.append(f"{summary.findings_omitted} further findings omitted")
    if summary.log_lines_dropped:
        parts.append(f"{summary.log_lines_dropped} log lines dropped")
    return f"({'; '.join(parts)})" if parts else None


def to_markdown(summary: Summary) -> str:
    """Render a `Summary` as human/model-pasteable Markdown (SPEC-005 §2)."""
    root = summary.findings[0] if summary.findings else None
    subject = (root.recipe if root and root.recipe else None) or (
        summary.build.component if summary.build and summary.build.component else "build"
    )
    task_suffix = f" ({root.task})" if root and root.task else ""

    lines = [f"# Yocto build failure — {subject}{task_suffix}"]
    lines += _metadata_lines(summary.build, root)
    lines.append("")

    for index, finding in enumerate(summary.findings, start=1):
        lines.append(
            f"## Finding {index} — {finding.category}-error "
            f"(confidence {finding.confidence:.2f})"
        )
        lines.append(f"Root cause: {finding.title}{_finding_location(finding)}")
        lines.append("")
        lines.append("```")
        lines.extend(finding.evidence)
        lines.append("```")
        lines.append("")

    if summary.config:
        lines.append("## Build config (secrets redacted)")
        lines.append("```")
        lines.extend(summary.config.splitlines())
        lines.append("```")
        lines.append("")

    note = _truncation_note(summary)
    if note:
        lines.append(note)
    return "\n".join(lines).rstrip() + "\n"


def finding_markdown(
    build: Build | None,
    finding: Finding,
    *,
    max_evidence: int = DEFAULT_MAX_EVIDENCE,
) -> str:
    """SPEC-005 Markdown for a single finding (host identity redacted).

    Used by the HTML "Copy for Claude" button (SPEC-004 §2): a self-contained,
    pasteable summary of one finding. Evidence is redacted and tail-biased via
    the same `_fit_finding` path as `summarize`, so no host identity leaks.
    """
    trimmed = _fit_finding(finding, max_evidence, DEFAULT_BUDGET, is_root=True)
    return to_markdown(Summary(build=build, findings=[trimmed]))


def _likely_cause(finding: Finding) -> str:
    return _LIKELY_CAUSE.get(finding.category, _LIKELY_CAUSE["unknown"])


def to_json(summary: Summary) -> str:
    """Render a `Summary` as deterministic, byte-stable JSON (SPEC-005 §3)."""
    build: dict[str, str] = {}
    if summary.build is not None:
        build_keys = (
            "component", "machine", "distro", "target_sys", "bitbake_version", "branch_commit",
        )
        for key in build_keys:
            value = getattr(summary.build, key)
            if value is not None:
                build[key] = value

    findings = [
        {
            "category": f.category,
            "confidence": f.confidence,
            "recipe": f.recipe,
            "task": f.task,
            "title": f.title,
            "file": f.file,
            "line": f.line,
            "likely_cause": _likely_cause(f),
            "evidence": f.evidence,
        }
        for f in summary.findings
    ]
    document = {
        "build": build,
        "findings": findings,
        "config": summary.config,
        "truncated": {
            "findings_omitted": summary.findings_omitted,
            "log_lines_dropped": summary.log_lines_dropped,
        },
    }
    return json.dumps(document, indent=2, sort_keys=True)
