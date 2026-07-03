"""Dependency rule (SPEC-002 §2): unresolved provides / missing RDEPENDS.

Matches message-kind failures and `Nothing provides` / `No provider` /
`Nothing RPROVIDES` signals. Title is the missing provide; recipe from `package`.
"""

from __future__ import annotations

import re

from ...models import Failure, Finding, LogLine
from ..evidence import build_evidence
from ..signatures import Rule, register

_SIGNALS = ("Nothing provides", "No provider", "Nothing RPROVIDES", "No eligible RPROVIDERs")
_PROVIDE_RE = re.compile(
    r"(?:Nothing provides|No provider(?:s)? for|Nothing RPROVIDES|"
    r"No eligible RPROVIDERs exist for)\s+'?([^'\n)]+?)'?(?:\s|$|\))"
)


def _match(failure: Failure, lines: list[LogLine]) -> bool:
    if failure.kind == "message":
        return True
    if (failure.task or "").startswith(("Nothing provides", "No provider")):
        return True
    return any(sig in line.text for line in lines for sig in _SIGNALS)


def _missing_provide(failure: Failure, lines: list[LogLine]) -> str | None:
    match = _PROVIDE_RE.search(failure.task or "")
    if match is None:
        for line in lines:
            match = _PROVIDE_RE.search(line.text)
            if match is not None:
                break
    return match.group(1).strip() if match else None


def _extract(failure: Failure, lines: list[LogLine]) -> Finding | None:
    provide = _missing_provide(failure, lines)
    default = failure.task or "Unresolved dependency"
    title = f"Nothing provides '{provide}'" if provide else default
    evidence = build_evidence(lines) or [title]
    return Finding(
        category="dependency",
        severity="error",
        title=title,
        recipe=failure.recipe or failure.package,
        task=failure.task if failure.kind == "task" else None,
        evidence=evidence,
        confidence=0.9,
    )


DEPENDENCY_RULE = Rule(
    name="dependency",
    category="dependency",
    severity="error",
    match=_match,
    extract=_extract,
    confidence=0.9,
    order=10,
)

register(DEPENDENCY_RULE)
