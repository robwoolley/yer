# yocto-error-reports (`yer`)

A command-line tool that reads Yocto/OpenEmbedded `error-report.txt` files,
**highlights the errors, failures, and anomalies** in the embedded build logs,
and turns them into:

- **Rich terminal output** for developers debugging a failed build.
- **Self-contained static HTML + JSON report artifacts** for CI to publish.
- **Compact, token-bounded summaries** designed to be fed to Claude for
  automated root-cause analysis and fix suggestinons.

> `error-report.txt` files are the JSON payloads produced by OpenEmbedded's
> `report-error` bbclass / `send-error-report`. See
> [docs/data-format.md](docs/data-format.md).

## Status

📐 **Planning / spec phase.** This repository currently contains the
specifications, architecture, and roadmap. No application code is written yet.
Implementation is tracked in [docs/roadmap.md](docs/roadmap.md) and
[tasks/](tasks/).

## Why

A failed Yocto build drops a large JSON report whose real content is one or more
raw task logs — up to ~2 MB each. Finding the actual root cause means scrolling
past thousands of lines of `NOTE:`/`DEBUG:` noise. `yer` extracts the handful of
lines that matter, classifies the failure (compile / configure / patch / QA /
fetch / dependency), deduplicates repeats, and presents a ranked list of
**findings** — the same findings drive the terminal view, the HTML report, and
the LLM summary.

## Quick example (target UX)

```console
$ yer analyze error-reports/error_report_20260701180755.txt
gz-gui9  do_configure  ✖ configure-error (confidence 0.86)
  CMake Error: package "Qt6" considered NOT FOUND
  CMakeLists.txt:110 (gz_configure_build)
1 error, 0 warnings — exit 1

$ yer report error-reports/*.txt --html out/         # static dashboard
$ yer summarize error-reports/err.txt --for-llm | claude -p "Fix this build failure"
```

## Documentation map

| Doc | Purpose |
| --- | --- |
| [docs/quickstart.md](docs/quickstart.md) | Install and first run (dev + CI). |
| [docs/architecture.md](docs/architecture.md) | The five-stage pipeline and module layout. |
| [docs/roadmap.md](docs/roadmap.md) | Milestones and the development plan. |
| [docs/data-format.md](docs/data-format.md) | Reference for the `error-report.txt` format. |
| [docs/spec-driven-workflow.md](docs/spec-driven-workflow.md) | How specs, plans, and tasks are organized for Claude Code. |
| [docs/specs/](docs/specs/) | Component specifications (SPEC-000…005). |
| [tasks/](tasks/) | Actionable, per-milestone task lists. |
| [CLAUDE.md](CLAUDE.md) | Operating guide for Claude Code in this repo. |

## Design commitments (v1)

- **Language:** Python 3.11+. Core parser/analyzer has **no runtime deps**;
  rendering adds Jinja2, terminal adds `rich`.
- **Inputs (v1):** `error-report.txt` JSON files (globs, dirs, stdin).
- **Outputs (v1):** terminal, `report.json`, self-contained HTML. SARIF + trend
  store are fast-follows.
- **LLM:** emits a structured summary only — **no API calls in the core tool.**
- **CI-first:** meaningful exit codes and machine-readable output.

## License

[MIT](LICENSE) © 2026 Rob Woolley.
