"""Shared signal predicates for the compile/configure boundary (SPEC-002 §2).

Configure-style signals win the category even under `do_compile`, so the compile
rule defers when any configure signal is present.
"""

from __future__ import annotations

from ...models import LogLine

CONFIGURE_SIGNALS = (
    "CMake Error",
    "Configuring incomplete",
    "considered to be NOT",
    "NOT FOUND",
)


def has_configure_signal(lines: list[LogLine]) -> bool:
    return any(signal in line.text for line in lines for signal in CONFIGURE_SIGNALS)
