"""QA rule (SPEC-002 §2 qa, §4 within-finding dedup).

A `do_package_qa` failure emits many near-identical `ERROR: QA Issue:` lines
(one per offending symlink). This collapses them into **one** finding, grouping
by QA class (the trailing `[tag]`) with a per-class count, so the dozen symlink
lines become a single `[dev-so] (×N)` entry instead of a dozen findings.
"""

from __future__ import annotations

import re
from collections import Counter

from ...models import Failure, Finding, LogLine
from ..evidence import build_evidence
from ..signatures import Rule, register

_QA_TAG_RE = re.compile(r"\[([\w-]+)\]\s*$")


def _match(failure: Failure, lines: list[LogLine]) -> bool:
    if (failure.task or "") == "do_package_qa":
        return True
    return any(
        "QA Issue:" in line.text or "Fatal QA errors were found" in line.text
        for line in lines
    )


def _qa_class(text: str) -> str:
    tag = _QA_TAG_RE.search(text)
    if tag is not None:
        return tag.group(1)
    after = text.split("QA Issue:", 1)[-1].strip()
    return after.split(maxsplit=1)[0] if after else "qa"


def _extract(failure: Failure, lines: list[LogLine]) -> Finding | None:
    issues = [line for line in lines if "QA Issue:" in line.text]
    counts: Counter[str] = Counter(_qa_class(line.text) for line in issues)
    representative: dict[str, str] = {}
    for line in issues:
        representative.setdefault(_qa_class(line.text), line.text)

    # Within-finding collapse: one representative line per class, with a count.
    evidence = [
        f"{representative[cls]} (x{n})" if n > 1 else representative[cls]
        for cls, n in counts.most_common()
    ]

    if counts:
        summary = ", ".join(f"{cls} x{n}" for cls, n in counts.most_common())
        title = f"QA Issue: {summary}"
    else:
        title = "Fatal QA errors were found"

    return Finding(
        category="qa",
        severity="error",
        title=title,
        recipe=failure.recipe or failure.package,
        task=failure.task if failure.kind == "task" else None,
        evidence=evidence or build_evidence(lines),
        confidence=0.9,
    )


QA_RULE = Rule(
    name="qa",
    category="qa",
    severity="error",
    match=_match,
    extract=_extract,
    confidence=0.9,
    order=10,
)

register(QA_RULE)
