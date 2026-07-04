# yocto-error-reports (`yer`)

A command-line tool that reads Yocto/OpenEmbedded `error-report.txt` files,
**highlights the errors, failures, and anomalies** in the embedded build logs,
and turns them into:

- **Rich terminal output** for developers debugging a failed build.
- **Self-contained static HTML + JSON + SARIF artifacts** for CI to publish.
- **Compact, token-bounded summaries** designed to be fed to Claude for
  automated root-cause analysis and fix suggestions.
- **Cross-run trends** — new / recurring / regressed / fixed failures, with a
  `--fail-on-new` regression gate.

> `error-report.txt` files are the JSON payloads produced by OpenEmbedded's
> `report-error` bbclass / `send-error-report`. See
> [docs/data-format.md](docs/data-format.md).

## Status

✅ **Implemented (v0.1.0).** The full pipeline (`ingest → parse → analyze →
summarize → render`) plus cross-run trends is built, tested against the real
report corpus, and green in CI. Milestones M0–M6 are complete — see
[docs/roadmap.md](docs/roadmap.md) and [CHANGELOG.md](CHANGELOG.md).

## Why

A failed Yocto build drops a large JSON report whose real content is one or more
raw task logs — up to ~2 MB each. Finding the actual root cause means scrolling
past thousands of lines of `NOTE:`/`DEBUG:` noise. `yer` extracts the handful of
lines that matter, classifies the failure (compile / configure / patch / QA /
fetch / dependency), deduplicates repeats, and presents a ranked list of
**findings** — the same findings drive the terminal view, the HTML report, and
the LLM summary.

## Quick example

```console
$ yer analyze error-reports/error_report_20260701180755.txt
[ERROR] gz-gui9 [do_configure] - configure (0.85)
    package "Qt5" considered NOT FOUND
    at CMakeLists.txt:86
      | -- Could NOT find Qt5QuickControls2 (missing: Qt5QuickControls2_DIR)
      | but it set Qt5_FOUND to FALSE so package "Qt5" is considered to be NOT

1 error(s), 0 warning(s) - exit 1

$ yer report error-reports/*.txt --html out/                 # static dashboard + report.json
$ yer analyze error-reports/*.txt --format sarif -o out.sarif # code-scanning annotations
$ yer summarize error-reports/err.txt | claude -p "Fix this build failure"
$ yer trend error-reports/*.txt --store .yer/trends.jsonl --record --fail-on-new  # regression gate
```

## Documentation map

| Doc | Purpose |
| --- | --- |
| [docs/quickstart.md](docs/quickstart.md) | Install and first run (dev + CI). |
| [docs/ci.md](docs/ci.md) | CI recipes: exit codes, SARIF upload, trend gating. |
| [docs/architecture.md](docs/architecture.md) | The five-stage pipeline and module layout. |
| [docs/roadmap.md](docs/roadmap.md) | Milestones and the development plan. |
| [docs/data-format.md](docs/data-format.md) | Reference for the `error-report.txt` format. |
| [docs/corpus.md](docs/corpus.md) | How to add to the sample corpus and derive fixtures. |
| [docs/spec-driven-workflow.md](docs/spec-driven-workflow.md) | How specs, plans, and tasks are organized for Claude Code. |
| [docs/specs/](docs/specs/) | Component specifications (SPEC-000…006). |
| [tasks/](tasks/) | Actionable, per-milestone task lists. |
| [CHANGELOG.md](CHANGELOG.md) | Release history. |
| [CLAUDE.md](CLAUDE.md) | Operating guide for Claude Code in this repo. |

## Design commitments (v1)

- **Language:** Python 3.11+. Core `parse`/`analyze`/`models` are **stdlib-only**;
  rendering adds Jinja2.
- **Inputs:** `error-report.txt` JSON files (globs, dirs, stdin).
- **Outputs:** terminal, canonical `report.json`, self-contained HTML, SARIF
  2.1.0, and a local cross-run trend store.
- **LLM:** emits a structured summary only — **no API calls in the core tool.**
- **CI-first:** meaningful exit codes, machine-readable output, deterministic
  artifacts, and privacy redaction of host identity in everything shareable.

## License

[MIT](LICENSE) © 2026 Rob Woolley.
