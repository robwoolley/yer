"""Compile rule (SPEC-002 §2): gcc/clang compile failures.

Matches a compiler `error:`, `undefined reference to`, or `ninja: build stopped`
— but **defers** when configure-style signals are present, so a `do_compile` that
is really a configure failure is classified as configure (content over task).
Title is the first compiler `error:`; `file:line` from the diagnostic when present.
"""

from __future__ import annotations

import re

from ...models import Failure, Finding, LogLine
from ..evidence import build_evidence
from ..signatures import Rule, register
from ._signals import has_configure_signal

_DIAG_RE = re.compile(r"(\S+\.[A-Za-z][\w+]*):(\d+):(?:\d+:)?\s*error:")


def _has_compile_signal(lines: list[LogLine]) -> bool:
    return any(
        "error:" in line.text
        or "undefined reference to" in line.text
        or "ninja: build stopped" in line.text
        for line in lines
    )


def _match(failure: Failure, lines: list[LogLine]) -> bool:
    return _has_compile_signal(lines) and not has_configure_signal(lines)


def _extract(failure: Failure, lines: list[LogLine]) -> Finding | None:
    error = next((line for line in lines if "error:" in line.text), None)
    if error is None:
        error = next((line for line in lines if "undefined reference to" in line.text), None)
    title = error.text if error is not None else "Compilation failed"

    file_name = None
    line_no = None
    for line in lines:
        diag = _DIAG_RE.search(line.text)
        if diag is not None:
            file_name, line_no = diag.group(1).split("/")[-1], int(diag.group(2))
            break

    focus = error.n if error is not None else next(
        (x.n for x in lines if "ninja: build stopped" in x.text), None
    )
    return Finding(
        category="compile",
        severity="error",
        title=title,
        recipe=failure.recipe or failure.package,
        task=failure.task if failure.kind == "task" else None,
        file=file_name,
        line=line_no,
        evidence=build_evidence(lines, focus),
        confidence=0.8,
    )


COMPILE_RULE = Rule(
    name="compile",
    category="compile",
    severity="error",
    match=_match,
    extract=_extract,
    confidence=0.8,
    order=10,
)

register(COMPILE_RULE)
