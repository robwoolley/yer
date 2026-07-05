"""Fetch rule (SPEC-002 §2): `do_fetch` network / checksum failures.

Matches `do_fetch` failures whose log shows an unfetchable URL, network error, or
checksum mismatch. Title is the reason + URI.
"""

from __future__ import annotations

import re

from ...models import Failure, Finding, LogLine
from ..evidence import build_evidence
from ..signatures import Rule, register

_SIGNALS = (
    "Unable to fetch",
    "Fetcher failure",
    "FetchError",
    "Network is unreachable",
    "checksum",
    "Unable to find revision",
)
_FETCHERR_RE = re.compile(r"FetchError\('([^']+)',\s*'([^']+)'\)")
_URI_RE = re.compile(r"'((?:git|https?|ftp|ssh|svn|npm|file|s3|crate)://[^']+)'")


def _match(failure: Failure, lines: list[LogLine]) -> bool:
    if (failure.task or "") != "do_fetch":
        return False
    return any(sig in line.text for line in lines for sig in _SIGNALS)


def _title(lines: list[LogLine]) -> str:
    errors = "\n".join(line.text for line in lines if line.level == "ERROR")
    scope = errors or "\n".join(line.text for line in lines)
    fetcherr = _FETCHERR_RE.search(scope)
    if fetcherr is not None:
        reason, uri = fetcherr.group(1), fetcherr.group(2)
        return f"{reason} ({uri})"
    uri_match = _URI_RE.search(scope)
    reason = next(
        (line.text for line in lines if line.level == "ERROR" and "fetch" in line.text.lower()),
        None,
    )
    if uri_match and reason:
        return f"{reason} ({uri_match.group(1)})"
    if uri_match:
        return f"Unable to fetch {uri_match.group(1)}"
    return reason or "do_fetch failed"


def _extract(failure: Failure, lines: list[LogLine]) -> Finding | None:
    focus = next(
        (line.n for line in lines if line.level == "ERROR" and "fetch" in line.text.lower()),
        None,
    )
    return Finding(
        category="fetch",
        severity="error",
        title=_title(lines),
        recipe=failure.recipe or failure.package,
        task="do_fetch",
        evidence=build_evidence(lines, focus),
        confidence=0.85,
    )


FETCH_RULE = Rule(
    name="fetch",
    category="fetch",
    severity="error",
    match=_match,
    extract=_extract,
    confidence=0.85,
    order=10,
)

register(FETCH_RULE)
