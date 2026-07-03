"""Parse: turn a failure's raw `log` string into structured `LogLine[]`.

SPEC-001 §2. Line-oriented and **streaming**: we iterate lines and match an
anchored per-line regex — never a single regex over the whole (up to 2 MB) log
(§3, O(n)). No classification here; that is the analyzer's job.

Stdlib-only per SPEC-000 NFR1.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .models import LogLine

# bitbake prefixes many lines with a level token at column 0. `\s?` consumes at
# most one space after the colon (data-format §"Log line grammar").
_LEVEL_RE = re.compile(r"^(ERROR|WARNING|NOTE|DEBUG):\s?")

# The BB backtrace block: a header line, then tab-indented frames (data-format
# §"The BB backtrace block"). Matched against `LogLine.text` (level already split).
_BACKTRACE_HEADER = "Backtrace (BB generated script)"
_FRAME_RE = re.compile(r"^\s*#(\d+):\s*([^,]+?),\s*(.+?),\s*line\s+(\d+)\s*$")


def _split_level(line: str) -> tuple[str | None, str]:
    match = _LEVEL_RE.match(line)
    if match is None:
        return None, line
    return match.group(1), line[match.end() :]


def iter_log_lines(log: str) -> Iterator[LogLine]:
    """Yield `LogLine`s with 1-based numbers, streaming over `\\n`-delimited lines.

    Leading indentation from sub-tools (cmake/ninja) is preserved in `.text`; a
    trailing `\\r` (CRLF) is stripped. A final newline does not emit a spurious
    empty last line.
    """
    if not log:
        return
    lines = log.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # drop the empty element a trailing newline produces
    for n, raw in enumerate(lines, start=1):
        text = raw[:-1] if raw.endswith("\r") else raw
        level, text = _split_level(text)
        yield LogLine(n=n, level=level, text=text)


def parse_log(log: str) -> list[LogLine]:
    """Eager form of :func:`iter_log_lines`."""
    return list(iter_log_lines(log))


@dataclass(frozen=True)
class BacktraceFrame:
    """One frame of the BB backtrace: ``#<index>: <func>, <path>, line <line>``."""

    index: int
    func: str
    path: str
    line: int


def extract_backtrace(lines: Iterable[LogLine]) -> list[BacktraceFrame]:
    """Return the frames of the BB backtrace block, or ``[]`` if absent.

    A parsed side-channel (SPEC-001 §2): the analyzer uses these frames to
    confirm the failing shell function and task. Scans for the
    ``Backtrace (BB generated script)`` header, then the contiguous
    ``#N: func, path, line n`` frames that follow.
    """
    rows = list(lines)
    for i, line in enumerate(rows):
        if line.text.startswith(_BACKTRACE_HEADER):
            frames: list[BacktraceFrame] = []
            for follow in rows[i + 1 :]:
                match = _FRAME_RE.match(follow.text)
                if match is None:
                    break
                frames.append(
                    BacktraceFrame(
                        index=int(match.group(1)),
                        func=match.group(2).strip(),
                        path=match.group(3).strip(),
                        line=int(match.group(4)),
                    )
                )
            return frames
    return []
