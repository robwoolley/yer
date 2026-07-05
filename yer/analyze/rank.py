"""Ranking + root-cause vs cascade (SPEC-002 §5).

Sort by `(severity_rank, phase_order, -confidence, recipe, signature)`. Within one
build, a repeated **identical** error (same signature) is marked a cascade of the
first occurrence rather than dropped. Conservative v1: only identical repeats are
cascades, so independent same-category failures are not falsely linked.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..models import Finding

_SEVERITY_RANK = {"error": 0, "failure": 1, "warning": 2, "anomaly": 3}

# fetch < patch < configure < compile < qa (SPEC-002 §5); a dependency
# (provider-resolution) failure precedes fetch, and unknown sorts last.
_PHASE_ORDER = {
    "dependency": 0,
    "fetch": 1,
    "patch": 2,
    "configure": 3,
    "compile": 4,
    "qa": 5,
    "unknown": 6,
}


def rank_key(finding: Finding) -> tuple[int, int, float, str, str]:
    return (
        _SEVERITY_RANK.get(finding.severity, 9),
        _PHASE_ORDER.get(finding.category, 9),
        -finding.confidence,
        finding.recipe or "",
        finding.signature,
    )


def rank(findings: Iterable[Finding]) -> list[Finding]:
    """Deterministically ordered findings (root-cause phases first)."""
    return sorted(findings, key=rank_key)


def mark_cascades(build_findings: list[Finding]) -> None:
    """Mark repeated identical errors within one build as cascades of the first."""
    roots: set[str] = set()
    for finding in build_findings:
        if finding.severity != "error":
            continue
        if finding.signature in roots:
            finding.cascade_of = finding.signature  # cascade of the earlier root
        else:
            roots.add(finding.signature)
