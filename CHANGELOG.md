# Changelog

All notable changes to `yocto-error-reports` (`yer`) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

## [0.1.0] — 2026-07-04

First implemented release. The full `ingest → parse → analyze → summarize →
render` pipeline plus cross-run trends, built spec-first (milestones M0–M6),
tested against the real report corpus, and green in CI.

### Added

- **Ingest & parse** (SPEC-001): defensive JSON loading of `error-report.txt`
  files from paths, globs, directories, and stdin; schema-tolerant `Build`
  model; streaming, tail-biased parsing of task logs up to ~2 MB; bitbake level
  and backtrace-block detection. Malformed input yields a parse finding, never a
  crash.
- **Analyzer** (SPEC-002): rule registry with seed rules for `compile`,
  `configure`, `patch`, `qa`, `fetch`, and `dependency`, plus a fallback that
  guarantees every failure yields ≥1 finding. Content-over-task classification,
  ≤15-line tail-biased evidence, stable `signature` dedup, cross-report finding
  groups, deterministic ranking, and root-cause vs cascade detection.
- **CLI** (SPEC-003): `yer analyze` with `--format text|json|sarif`,
  `--category`/`--recipe` filters, `--max-evidence`, `--no-color`/`NO_COLOR`, and
  the `0`/`1`/`2` exit-code contract wired to `--fail-on`.
- **LLM summary** (SPEC-005): `yer summarize` emits a token-bounded Markdown or
  JSON summary (default ~4000 tokens, even for the 2 MB log) with top-K findings,
  tail-biased evidence, and an honest `truncated` accounting; pipes to `claude`.
- **Static report** (SPEC-004): `yer report --html <dir>` writes a self-contained
  `index.html` (inline CSS/JS, light/dark, findings grouped by recipe, per-finding
  "Copy for Claude" button, responsive) and a canonical, byte-deterministic
  `report.json`.
- **SARIF** (SPEC-004 §3): `--format sarif` emits SARIF 2.1.0 for GitHub/GitLab
  code-scanning annotations.
- **Trends** (SPEC-006): append-only local run store keyed by `signature`;
  `yer trend` diffs a run against history into new / recurring / regressed /
  fixed, with a `--fail-on-new` regression gate, a `--record` opt-in, and an
  additive HTML trend layer (badges + "fixed since baseline" list).
- **CI recipes** ([docs/ci.md](docs/ci.md)): documented exit-code contract,
  GitHub Actions workflows for artifact + SARIF publishing, and a trend
  regression-gate example.

### Security & privacy

- Host identity (`SSH_AUTH_SOCK` sockets, `/<host>/<user>/<date>/…` build roots)
  is redacted by structure from every shareable output — summaries, `report.json`,
  HTML, SARIF, and the trend store.
- `local.conf`/`auto.conf` are excluded unless `--include-config`, and secret
  lines are redacted even then.
- The trend store holds only redacted titles, signatures, and counts — never
  evidence, config, or input paths — and is gitignored.

[Unreleased]: https://github.com/robwoolley/yer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/robwoolley/yer/releases/tag/v0.1.0
