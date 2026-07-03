"""Configure rule (SPEC-002 §2): CMake / configure-time failures.

Matches `CMake Error at`, `Configuring incomplete`, and `package "X" … NOT FOUND`
regardless of task — a `do_compile` that is really a configure failure classifies
here (content over task). Title is the NOT-FOUND package or first CMake Error;
`file`/`line` from `CMakeLists.txt:<n>`.
"""

from __future__ import annotations

import re

from ...models import Failure, Finding, LogLine
from ..evidence import build_evidence
from ..signatures import Rule, register
from ._signals import has_configure_signal

_PKG_NOTFOUND_RE = re.compile(r'package "([^"]+)" is considered to be NOT')
_CMAKELISTS_RE = re.compile(r"(CMakeLists\.txt):(\d+)")


def _match(failure: Failure, lines: list[LogLine]) -> bool:
    return has_configure_signal(lines)


def _extract(failure: Failure, lines: list[LogLine]) -> Finding | None:
    package = None
    for line in lines:
        found = _PKG_NOTFOUND_RE.search(line.text)
        if found is not None:
            package = found.group(1)
            break

    file_name = None
    line_no = None
    for line in lines:
        loc = _CMAKELISTS_RE.search(line.text)
        if loc is not None:
            file_name, line_no = loc.group(1), int(loc.group(2))
            break

    if package is not None:
        title = f'package "{package}" considered NOT FOUND'
    else:
        title = next((x.text for x in lines if "CMake Error" in x.text), "Configure error")

    focus = next(
        (x.n for x in lines if "considered to be NOT" in x.text or "CMake Error" in x.text),
        None,
    )
    return Finding(
        category="configure",
        severity="error",
        title=title,
        recipe=failure.recipe or failure.package,
        task=failure.task if failure.kind == "task" else None,
        file=file_name,
        line=line_no,
        evidence=build_evidence(lines, focus),
        confidence=0.85,
    )


CONFIGURE_RULE = Rule(
    name="configure",
    category="configure",
    severity="error",
    match=_match,
    extract=_extract,
    confidence=0.85,
    order=5,
)

register(CONFIGURE_RULE)
