# Quick Start

> ⚠️ Implementation is not built yet — this describes the **target** developer
> and CI experience defined by the specs. Track progress in
> [roadmap.md](roadmap.md).

## Install

```bash
# From a checkout (development)
pipx install .            # or: pip install -e .

# Once published
pipx install yocto-error-reports
```

Requires **Python 3.11+**. The core has no third-party runtime dependencies;
HTML rendering pulls in Jinja2, terminal color uses `rich`.

## Developer workflow

Point `yer` at one report, a glob, a directory, or stdin.

```bash
# Analyze a single report — ranked findings in the terminal
yer analyze error-reports/error_report_20260701180755.txt

# Analyze many at once
yer analyze error-reports/*.txt
yer analyze ./error-reports/            # a directory is scanned for reports
cat report.txt | yer analyze -          # stdin

# Machine-readable output
yer analyze error-reports/*.txt --format json -o report.json
yer analyze error-reports/*.txt --format sarif -o results.sarif   # (fast-follow)
```

### Get a fix suggestion from Claude

`yer` emits a compact, privacy-scrubbed, token-bounded summary. Pipe it to Claude:

```bash
yer summarize error-reports/error_report_20260701180755.txt --for-llm \
  | claude -p "You are a Yocto expert. Diagnose and propose a fix for this build failure."
```

`--for-llm` prints Markdown by default; add `--format json` for a structured
payload. `local.conf`/`auto.conf` are **excluded** unless you pass
`--include-config` (redaction still applies).

### Generate a static report/dashboard

```bash
yer report error-reports/*.txt --html out/
open out/index.html         # self-contained; no server required
```

## CI usage

`yer` is CI-first: it exits non-zero when findings meet a threshold and writes
publishable artifacts.

```yaml
# GitHub Actions example
- name: Analyze Yocto error reports
  run: |
    yer report build/tmp/log/error-report/*.txt \
      --html public/error-report \
      --format json -o public/error-report/report.json \
      --fail-on error

- name: Publish report artifact
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: yocto-error-report
    path: public/error-report
```

**Exit codes:** `0` = clean · `1` = findings at/above `--fail-on` · `2` = tool
or parse error. Use `--fail-on warning` to gate more strictly, or run without
`--fail-on` to always exit `0` and just publish the report.

## Commands at a glance

| Command | Purpose |
| --- | --- |
| `yer analyze <inputs>` | Parse + classify; print findings (`--format text/json/sarif`). |
| `yer report <inputs> --html <dir>` | Write self-contained HTML + `report.json`. |
| `yer summarize <inputs> --for-llm` | Emit token-bounded summary for Claude. |

See [SPEC-003](specs/SPEC-003-cli.md) for the full CLI contract.
