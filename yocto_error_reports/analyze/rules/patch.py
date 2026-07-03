"""Patch rule (SPEC-002 §2): `do_patch` hunk failures / non-applying patches.

Matches `Hunk #N FAILED`, `does not apply`, or `rejects in file`. Title names the
patch and the first failing file/hunk; `file`/`line` come from the first
`Hunk #N FAILED at <line>` and the `patching file` that precedes it.
"""

from __future__ import annotations

import re

from ...models import Failure, Finding, LogLine
from ..evidence import build_evidence
from ..signatures import Rule, register

_HUNK_RE = re.compile(r"Hunk #(\d+) FAILED at (\d+)")
_PATCHING_RE = re.compile(r"patching file (\S+)")
_REJECTS_RE = re.compile(r"rejects in file (\S+)")
_PATCH_NAME_RE = re.compile(r"([\w.+-]+\.patch)")


def _match(failure: Failure, lines: list[LogLine]) -> bool:
    if any(
        _HUNK_RE.search(line.text)
        or "does not apply" in line.text
        or "rejects in file" in line.text
        for line in lines
    ):
        return True
    # a do_patch task failure is a patch-phase failure even without hunk detail
    return (failure.task or "") == "do_patch" and any(line.level == "ERROR" for line in lines)


def _first_failing_hunk(lines: list[LogLine]) -> tuple[int | None, int | None, str | None]:
    """(hunk, line, file) for the first failing hunk; file from the prior `patching file`."""
    current_file: str | None = None
    for line in lines:
        patching = _PATCHING_RE.search(line.text)
        if patching is not None:
            current_file = patching.group(1)
        hunk = _HUNK_RE.search(line.text)
        if hunk is not None:
            return int(hunk.group(1)), int(hunk.group(2)), current_file
    return None, None, None


def _patch_name(lines: list[LogLine]) -> str | None:
    for line in lines:
        if "does not apply" in line.text or ("Applying patch" in line.text):
            name = _PATCH_NAME_RE.search(line.text)
            if name is not None:
                return name.group(1)
    return None


def _extract(failure: Failure, lines: list[LogLine]) -> Finding | None:
    hunk, line_no, path = _first_failing_hunk(lines)
    if path is None:
        for line in lines:
            rejects = _REJECTS_RE.search(line.text)
            if rejects is not None:
                path = rejects.group(1)
                break
    file_base = path.split("/")[-1] if path else None
    patch_name = _patch_name(lines)

    if patch_name and file_base and hunk is not None:
        title = f"{patch_name} failed: Hunk #{hunk} at {file_base}:{line_no}"
    elif file_base and hunk is not None:
        title = f"Patch hunk #{hunk} failed at {file_base}:{line_no}"
    elif patch_name:
        title = f"Patch {patch_name} does not apply"
    else:
        title = "Patch failed to apply"

    focus = next((line.n for line in lines if _HUNK_RE.search(line.text)), None)
    return Finding(
        category="patch",
        severity="error",
        title=title,
        recipe=failure.recipe or failure.package,
        task=failure.task if failure.kind == "task" else None,
        file=file_base,
        line=line_no,
        evidence=build_evidence(lines, focus),
        confidence=0.9,
    )


PATCH_RULE = Rule(
    name="patch",
    category="patch",
    severity="error",
    match=_match,
    extract=_extract,
    confidence=0.9,
    order=10,
)

register(PATCH_RULE)
