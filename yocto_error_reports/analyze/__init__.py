"""Analyze: classify failures into ranked, deduplicated `Finding`s (SPEC-002).

This module is the orchestrator: `analyze(builds)` runs each failure's parsed
`LogLine[]` through the registered rules and assembles a `Report`. Per-failure
selection (root-cause vs cascade), signatures, and dedup groups are layered in by
later M2 tasks (§4, §5); this skeleton (§1, §6) collects rule hits and carries
ingest-time parse findings through. Stdlib-only per SPEC-000 NFR1.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .. import parse
from ..models import Build, Finding, Report
from .dedup import collapse_evidence, compute_signature, group_findings
from .rank import mark_cascades, rank
from .signatures import Rule, fallback_rule, register, registered_rules

__all__ = ["analyze", "Rule", "register", "registered_rules"]


def _ordered(rules: Sequence[Rule]) -> tuple[Rule, ...]:
    return tuple(sorted(rules, key=lambda rule: (rule.order, rule.name)))


def analyze(builds: Iterable[Build], *, rules: Sequence[Rule] | None = None) -> Report:
    """Run the rules over every failure and return a deterministic `Report`.

    `rules` defaults to the module registry (with the fallback applied when no
    category rule hits). Pass an explicit list to analyze a failure against
    specific rules in isolation, with no implicit fallback (used by rule tests).
    """
    build_list = list(builds)
    if rules is None:
        active = registered_rules()
        fallback = fallback_rule()
    else:
        active = _ordered(rules)
        fallback = None

    findings: list[Finding] = []
    for build in build_list:
        build_findings: list[Finding] = list(build.findings)  # ingest parse findings
        for failure in build.failures:
            lines = parse.parse_log(failure.log)
            hits: list[Finding] = []
            for rule in active:
                if rule.match(failure, lines):
                    found = rule.extract(failure, lines)
                    if found is not None:
                        hits.append(found)
            if not hits and fallback is not None and fallback.match(failure, lines):
                found = fallback.extract(failure, lines)
                if found is not None:
                    hits.append(found)
            build_findings.extend(hits)

        # dedup + cascade within the build, in log/failure order (SPEC-002 §4, §5)
        for finding in build_findings:
            finding.evidence = collapse_evidence(finding.evidence)
            finding.signature = compute_signature(finding)
        mark_cascades(build_findings)
        findings.extend(build_findings)

    groups = group_findings(findings)
    return Report(builds=build_list, findings=rank(findings), groups=groups)


# Importing the rule modules self-registers them (SPEC-002 §2). Kept at the end
# to avoid an import cycle with the orchestrator above; aliased so it does not
# shadow the `rules` parameter.
from . import rules as _register_rules  # noqa: E402,F401
