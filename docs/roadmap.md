# Roadmap & Development Plan

> **Status:** Living plan. Milestones are ordered to deliver a useful tool as
> early as possible. Each milestone ends in a shippable, demoable state and is
> broken into tasks under [../tasks/](../tasks/).

## Sequencing rationale

The **analyze** stage is the product. So we build the shortest path to *ranked
findings from real reports* (M0–M2), then unlock the Claude workflow **before**
investing in HTML (M3 before M4), because a token-bounded summary is the highest
leverage output. HTML, SARIF, and trends follow.

## Milestone overview

| # | Name | Goal (demoable outcome) | Specs |
|---|------|--------------------------|-------|
| **M0** | Foundation | Repo scaffolding, `pyproject.toml`, `yer --version`, CI lint/test, fixtures extracted from `error-reports/`. | — |
| **M1** | Ingest + Parse | `yer analyze` loads all 77 corpus files without crashing; prints raw failure inventory (recipe/task counts). | [001](specs/SPEC-001-parser.md) |
| **M2** | Analyzer (seed rules) | Ranked, deduped findings for compile/configure/patch/qa/fetch/dependency + fallback; rich terminal output; exit codes. | [002](specs/SPEC-002-analyzer.md), [003](specs/SPEC-003-cli.md) |
| **M3** | LLM summary | `yer summarize --for-llm` emits token-bounded JSON + Markdown; privacy redaction; pipes to `claude`. | [005](specs/SPEC-005-llm-summary.md) |
| **M4** | Static report | `yer report --html` writes self-contained HTML + canonical `report.json`; deterministic. | [004](specs/SPEC-004-report-render.md) |
| **M5** | CI hardening | SARIF output, documented exit-code contract, GitHub Actions example, artifact publishing verified. | 003, 004 |
| **M6** | Trends (stretch) | Append runs to a store; diff signatures across builds; regression/new-failure view in HTML. | [006](specs/SPEC-006-trends.md) |

## Milestone detail

### M0 — Foundation
- Python package skeleton, `pyproject.toml` with `yer` console script.
- `models.py` dataclasses (the cross-stage contract).
- Test harness (`pytest`), lint/format (`ruff`), typecheck (`mypy`), CI workflow.
- Fixture pipeline: anonymized subset of `error-reports/` → `tests/fixtures/`.
- **Exit criteria:** `yer --version` runs; CI green; ≥6 fixtures (one per category).

### M1 — Ingest + Parse
- `ingest.py`: paths/globs/dirs/stdin, defensive JSON, schema-tolerant `Build`.
- `parse.py`: `log` → `LogLine[]`, prefix stripping, backtrace-block detection.
- **Exit criteria:** analyzing the whole corpus never raises; malformed input
  yields a parse finding, not a crash; handles the 2.1 MB log within budget.

### M2 — Analyzer + terminal
- `signatures.py` registry + `rules/` for all six observed categories + fallback.
- `dedup.py` and ranking (cascade detection).
- `cli.py` `analyze` subcommand with `rich` output and `--format text/json`.
- Exit-code contract wired to `--fail-on`.
- **Exit criteria:** every corpus file produces ≥1 finding with correct category;
  golden-file tests pass; first-error-as-root-cause verified on samples.

### M3 — LLM summary
- `summarize.py`: top-K + tail-biased evidence + `truncated` accounting.
- Privacy redaction; `--include-config` opt-in.
- **Exit criteria:** summary for the 2 MB report stays under the token budget;
  round-trip `yer summarize | claude` produces a plausible fix on ≥3 samples.

### M4 — Static report
- `json_out.py` canonical deterministic `report.json`.
- `static.py` self-contained HTML (inline assets, light/dark, findings grouped
  by recipe/category, per-finding "copy for Claude").
- **Exit criteria:** HTML opens offline; same input → identical `report.json`.

### M5 — CI hardening
- `sarif.py`; documented CI recipes; verify artifact upload + code-scanning
  annotations on a sample pipeline.

### M6 — Trends (stretch)
- Signature store, cross-build diff, regression/new/fixed views. See
  [SPEC-006](specs/SPEC-006-trends.md) (Approved).

## Tracking

- Task lists: [../tasks/milestone-0.md](../tasks/milestone-0.md) … one file per
  milestone as work begins.
- Definition of done per component: see [../CLAUDE.md](../CLAUDE.md).
