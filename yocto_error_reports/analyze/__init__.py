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
from .signatures import Rule, register, registered_rules

__all__ = ["analyze", "Rule", "register", "registered_rules"]


def _ordered(rules: Sequence[Rule]) -> tuple[Rule, ...]:
    return tuple(sorted(rules, key=lambda rule: (rule.order, rule.name)))


def analyze(builds: Iterable[Build], *, rules: Sequence[Rule] | None = None) -> Report:
    """Run the rules over every failure and return a deterministic `Report`.

    `rules` defaults to the module registry; pass an explicit list to analyze a
    failure against specific rules in isolation (used by rule tests).
    """
    build_list = list(builds)
    active = registered_rules() if rules is None else _ordered(rules)

    findings: list[Finding] = []
    for build in build_list:
        findings.extend(build.findings)  # ingest-time parse findings (M1-03)
        for failure in build.failures:
            lines = parse.parse_log(failure.log)
            for rule in active:
                if rule.match(failure, lines):
                    found = rule.extract(failure, lines)
                    if found is not None:
                        findings.append(found)

    return Report(builds=build_list, findings=findings, groups=[])
