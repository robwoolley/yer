"""Deduplication: stable signatures + cross-report grouping (SPEC-002 §4).

`signature = sha1(normalize(category + "\\n" + title + "\\n" + top_evidence))`
using the shared `parse.normalize` (SPEC-001 §2), so the same failure dedups
within a report and across reports in one run. Conservative v1 normalization
(OQ1). Stdlib-only.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from ..models import Finding, FindingGroup
from ..parse import normalize


def compute_signature(finding: Finding) -> str:
    top_evidence = finding.evidence[0] if finding.evidence else ""
    basis = normalize(f"{finding.category}\n{finding.title}\n{top_evidence}")
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()
    return f"sha1:{digest}"


def collapse_evidence(evidence: list[str]) -> list[str]:
    """Collapse consecutive normalized-identical lines to `line (×N)` (§4)."""
    collapsed: list[str] = []
    i = 0
    while i < len(evidence):
        j = i
        while j + 1 < len(evidence) and normalize(evidence[j + 1]) == normalize(evidence[i]):
            j += 1
        count = j - i + 1
        collapsed.append(f"{evidence[i]} (x{count})" if count > 1 else evidence[i])
        i = j + 1
    return collapsed


def group_findings(findings: Iterable[Finding]) -> list[FindingGroup]:
    """Group findings across reports by `signature` (occurrence count + recipes)."""
    groups: dict[str, FindingGroup] = {}
    for finding in findings:
        group = groups.get(finding.signature)
        if group is None:
            group = FindingGroup(signature=finding.signature, occurrences=0, affected_recipes=[])
            groups[finding.signature] = group
        group.occurrences += 1
        if finding.recipe and finding.recipe not in group.affected_recipes:
            group.affected_recipes.append(finding.recipe)
    # deterministic: most frequent first, then signature
    return sorted(groups.values(), key=lambda g: (-g.occurrences, g.signature))
