"""Rule registry for the analyzer (SPEC-002 §1).

A `Rule` pairs a matcher with an extractor for one failure signature. Rules
register into a module-level registry; adding a category is a new `rules/` module
that calls `register(...)` on import — the orchestrator never changes.

Stdlib-only per SPEC-000 NFR1.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..models import Failure, Finding, LogLine

Matcher = Callable[[Failure, list[LogLine]], bool]
Extractor = Callable[[Failure, list[LogLine]], "Finding | None"]


@dataclass(frozen=True)
class Rule:
    name: str
    category: str  # compile|configure|patch|qa|fetch|dependency|unknown
    severity: str  # error|failure|warning|anomaly
    match: Matcher
    extract: Extractor
    confidence: float = 0.5  # base confidence when matched
    order: int = 100  # tie-break / phase ordering


_REGISTRY: list[Rule] = []


def register(rule: Rule) -> Rule:
    """Add a rule to the module-level registry (returns it, for decorator use)."""
    _REGISTRY.append(rule)
    return rule


def registered_rules() -> tuple[Rule, ...]:
    """All registered rules, ordered deterministically by `(order, name)`."""
    return tuple(sorted(_REGISTRY, key=lambda rule: (rule.order, rule.name)))


def clear_rules() -> None:
    """Empty the registry (test isolation)."""
    _REGISTRY.clear()
