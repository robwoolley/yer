"""Evidence selection for findings (SPEC-002 §3).

Each finding carries a handful of the lines that matter — never the whole log:
<= N lines (default 15), tail-biased, with `NOTE:`/`DEBUG:` noise stripped unless
it is the only content. Stdlib-only.
"""

from __future__ import annotations

from ..models import LogLine

MAX_EVIDENCE = 15
_NOISE = frozenset({"NOTE", "DEBUG"})


def render_line(line: LogLine) -> str:
    """Reconstruct a readable line, re-attaching its bitbake level prefix."""
    return f"{line.level}: {line.text}" if line.level else line.text


def build_evidence(
    lines: list[LogLine], focus_n: int | None = None, *, max_lines: int = MAX_EVIDENCE
) -> list[str]:
    """Up to `max_lines` rendered lines, tail-biased toward `focus_n`.

    NOTE/DEBUG lines are dropped unless they are the only content. When `focus_n`
    is given the window ends at that line (context precedes the error); otherwise
    the last `max_lines` signal lines are taken.
    """
    signal = [line for line in lines if line.level not in _NOISE]
    if not signal:
        signal = list(lines)  # only noise -> keep it (§3: unless it is the only content)

    if focus_n is not None:
        upto = [i for i, line in enumerate(signal) if line.n <= focus_n]
        end = (upto[-1] + 1) if upto else len(signal)
    else:
        end = len(signal)

    start = max(0, end - max_lines)
    return [render_line(line) for line in signal[start:end]]
