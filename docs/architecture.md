# Architecture

> **Status:** Approved design for v1. Changes require updating this doc and the
> affected SPEC.

## Principle

One idea — `error-report.txt → findings → outputs` — expressed as five
**decoupled, individually testable** stages. Each stage is a pure function over
data structures defined in `models.py`. Almost all the product value is in the
**analyze** stage; everything else is a projection of the ranked findings list.

```
                ┌──────────┐   ┌────────┐   ┌───────────────────────┐   ┌───────────┐   ┌────────┐
  *.txt  ─────▶ │  ingest  │─▶ │ parse  │─▶ │        analyze        │─▶ │ summarize │─▶ │ render │ ─▶ terminal
  (JSON)        │          │   │        │   │ classify→dedup→rank   │   │ (LLM)     │   │        │    report.json
                └──────────┘   └────────┘   └───────────────────────┘   └───────────┘   └────────┘    report.html
                   Build[]       Failure[]         Finding[]              Summary        artifacts
```

## Stages

### 1. ingest (`ingest.py`)
Locate and load inputs: file paths, globs, directories, `-` for stdin. Parse
JSON **defensively** (extension is opaque; content detection). Emits `Build`
objects. Schema-tolerant: every field optional, unknown keys ignored, missing
`failures` → empty. **Never raises on a malformed report** — records a
parse-level finding instead.

### 2. parse (`parse.py`)
Turns each failure's raw `log` string into structured `LogLine` events: strip
the bitbake level prefix (`ERROR:`/`WARNING:`/`NOTE:`/`DEBUG:`), keep line
numbers, detect the `Backtrace (BB generated script)` block. Handles 2 MB logs
via streaming/line iteration, not whole-string regex. No classification here —
just structure.

### 3. analyze (`analyze/`) — the core
- `signatures.py` — a **registry** of rules: `(name, matcher, category,
  severity, extractor, confidence)`.
- `rules/` — one module per domain (`compile.py`, `configure.py`, `patch.py`,
  `qa.py`, `fetch.py`, `dependency.py`, `fallback.py`).
- `dedup.py` — collapse repeated lines and group duplicate findings by
  `signature`.
- `__init__.py` — orchestrates classify → dedup → rank, emits `Finding[]`.

Ranking heuristic: the **first real error** in a task log is usually the root
cause; later errors are often cascades. Rank by `(severity, task-phase order,
confidence)`; mark suspected cascades rather than dropping them. A `fallback`
rule captures any stray `ERROR:`/`WARNING:` so nothing is silently lost.

### 4. summarize (`summarize.py`)
Projects `Finding[]` into a **token-bounded** `Summary`: top-K findings, ≤N
evidence lines each (tail-biased), always keep recipe+task+first-error, and an
explicit `truncated` block. Emits JSON (for piping) and tight Markdown (for
paste). **No network calls.** See [SPEC-005](specs/SPEC-005-llm-summary.md).

### 5. render (`render/`)
- `json_out.py` — canonical `report.json` (full findings).
- `static.py` — Jinja2 → **one self-contained HTML file** (inline CSS/JS, no
  external assets) publishable as a CI artifact / to Pages.
- `sarif.py` — optional SARIF for GitHub/GitLab code-scanning UIs (fast-follow).
- Terminal rendering lives in `cli.py` (via `rich`).

## Package layout

```
yocto_error_reports/
  __init__.py
  models.py          # Build, Failure, LogLine, Finding, Summary, Report
  ingest.py
  parse.py
  analyze/
    __init__.py      # orchestration: classify → dedup → rank
    signatures.py    # rule registry
    rules/           # compile.py configure.py patch.py qa.py fetch.py dependency.py fallback.py
    dedup.py
  summarize.py
  render/
    static.py
    json_out.py
    sarif.py
    templates/
  cli.py             # entrypoint + terminal output + exit codes
tests/
  fixtures/          # anonymized *.json samples + expected/*.json golden files
  test_*.py
pyproject.toml       # console_scripts: yer = yocto_error_reports.cli:main
```

## The data model (contract between stages)

```python
@dataclass
class Build:
    component: str | None; machine: str | None; distro: str | None
    build_sys: str | None; target_sys: str | None; bitbake_version: str | None
    branch_commit: str | None; failures: list["Failure"]
    raw: dict            # original JSON, for escape hatches
    source_path: str

@dataclass
class Failure:
    task: str | None; package: str | None; recipe: str | None
    log: str
    kind: str            # "task" | "message"  (dependency failures put msg in task)

@dataclass
class LogLine:
    n: int; level: str | None; text: str

@dataclass
class Finding:
    category: str        # compile|configure|patch|qa|fetch|dependency|unknown
    severity: str        # error|failure|warning|anomaly
    title: str
    recipe: str | None; task: str | None
    file: str | None; line: int | None
    evidence: list[str]  # the few lines that matter — NOT the whole log
    signature: str       # normalized hash for dedup/trends
    confidence: float
    cascade_of: str | None   # signature of the finding this likely cascades from

@dataclass
class FindingGroup:        # cross-report dedup group (SPEC-002 §4/§6)
    signature: str; occurrences: int; affected_recipes: list[str]

@dataclass
class Summary:             # token-bounded LLM projection (SPEC-005 §3)
    build: Build | None; findings: list["Finding"]      # selected top-K
    findings_omitted: int; log_lines_dropped: int       # honest-loss block

@dataclass
class Report:              # analyzer output (SPEC-002 §6)
    builds: list["Build"]; findings: list["Finding"]; groups: list["FindingGroup"]
```

`signature` = hash of the normalized title/evidence with paths, line numbers,
hex, and timestamps stripped. **Conservative normalization in v1** (favor fewer
false merges); the trend layer can tune it later.

## Cross-cutting

- **Exit codes:** `0` clean · `1` findings ≥ `--fail-on` · `2` tool/parse error.
- **Determinism:** same input → byte-identical `report.json` (stable ordering,
  no timestamps in the canonical doc; wall-clock only in HTML chrome).
- **Extensibility:** new failure type = new rule module + fixture. No core edit.
- **Performance target:** analyze the full 77-file corpus in < a few seconds.

## Changelog

- **2026-07-03 (M0-02):** Drew `Summary`, `Report`, and `FindingGroup` into the
  §"The data model" code block. They were already referenced (models list;
  SPEC-002 §6 "dedup groups"; SPEC-005 §3) but not shown here; `FindingGroup` is
  the concrete type for SPEC-002's cross-report dedup groups. No behavior change
  — implemented in `models.py` as pure, defaultable dataclasses.
