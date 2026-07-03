"""The cross-stage data contract: `ingest → parse → analyze → summarize → render`.

Pure dataclasses, **no logic** (M0-02). Field lists are authoritative from:
  - architecture.md §"The data model" — Build, Failure, LogLine, Finding
  - SPEC-002 §6 / §4 — Report and the cross-report dedup FindingGroup
  - SPEC-005 §3 — Summary (token-bounded projection + truncated accounting)

Core modules are stdlib-only per SPEC-000 NFR1. Every field is defaultable so
construction is defensive (data-format §"Robustness rules": each field optional).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LogLine:
    """One parsed log line: 1-based number, split bitbake level, remaining text."""

    n: int = 0
    level: str | None = None  # ERROR | WARNING | NOTE | DEBUG | None
    text: str = ""


@dataclass
class Failure:
    """One failure object from a report (pre-parse; `log` is the raw string)."""

    task: str | None = None      # do_* task name, or an error message when kind=="message"
    package: str | None = None
    recipe: str | None = None    # absent in 2 legacy samples — optional
    log: str = ""
    kind: str = "task"           # "task" | "message"


@dataclass
class Build:
    """One ingested report (schema-tolerant; `raw` keeps the original JSON)."""

    component: str | None = None
    machine: str | None = None
    distro: str | None = None
    build_sys: str | None = None
    target_sys: str | None = None
    bitbake_version: str | None = None
    branch_commit: str | None = None
    failures: list[Failure] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    source_path: str = ""


@dataclass
class Finding:
    """A classified, ranked build failure — the product's core unit."""

    category: str = "unknown"    # compile|configure|patch|qa|fetch|dependency|unknown
    severity: str = "error"      # error|failure|warning|anomaly
    title: str = ""
    recipe: str | None = None
    task: str | None = None
    file: str | None = None
    line: int | None = None
    evidence: list[str] = field(default_factory=list)  # the few lines that matter
    signature: str = ""          # normalized hash for dedup/trends
    confidence: float = 0.0
    cascade_of: str | None = None  # signature of the finding this likely cascades from


@dataclass
class FindingGroup:
    """Cross-report dedup group: findings sharing a `signature` (SPEC-002 §4)."""

    signature: str = ""
    occurrences: int = 0
    affected_recipes: list[str] = field(default_factory=list)


@dataclass
class Summary:
    """Token-bounded projection for the LLM (SPEC-005): selection + honest loss."""

    build: Build | None = None
    findings: list[Finding] = field(default_factory=list)  # selected, top-K, ranked
    findings_omitted: int = 0
    log_lines_dropped: int = 0


@dataclass
class Report:
    """Analyzer output: builds, the flat ranked findings, and dedup groups."""

    builds: list[Build] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    groups: list[FindingGroup] = field(default_factory=list)
