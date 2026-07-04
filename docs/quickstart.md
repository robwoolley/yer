# Quick Start

> **Status:** all four subcommands — `analyze`, `report`, `summarize`, and
> `trend` — are implemented and tested (v0.1.0). See [CHANGELOG.md](../CHANGELOG.md)
> and, for CI, [ci.md](ci.md).

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
yer analyze error-reports/*.txt --format sarif -o results.sarif   # code-scanning
```

### Get a fix suggestion from Claude

`yer` emits a compact, privacy-scrubbed, token-bounded summary (≤ ~4000 tokens by
default, even for a 2 MB log). Pipe it to Claude:

```bash
yer summarize error-reports/error_report_20260701180755.txt \
  | claude -p "You are a Yocto expert. Diagnose and propose a fix for this build failure."
```

Markdown is the default; add `--format json` for a structured payload, `--budget
<tokens>` to resize. `local.conf`/`auto.conf` are **excluded** unless you pass
`--include-config` (secret + host-identity redaction still applies). Host-identity
paths (`SSH_AUTH_SOCK`, `/<host>/<user>/<date>/…` build roots) are always redacted
from evidence — the summary is safe to share.

#### Round-trip smoke (SPEC-005 T6)

Requires the [`claude`](https://claude.com/claude-code) CLI. Try one report per
category and check the fix is plausible:

```bash
# pick reports of different failure categories from your build
for r in \
    error-reports/<a-configure-failure>.txt \
    error-reports/<a-compile-failure>.txt \
    error-reports/<a-patch-failure>.txt ; do
  echo "=== $r ===";
  yer summarize "$r" | claude -p "Diagnose this Yocto build failure and propose a fix.";
done
```

`yer analyze <report>` first if you're unsure of a report's category (the finding
category is printed per failure).

### Generate a static report/dashboard

```bash
yer report error-reports/*.txt --html out/
open out/index.html         # self-contained; no server required

# annotate the HTML with new/recurring/regressed badges from history
yer report error-reports/*.txt --html out/ --store .yer/trends.jsonl
```

### Track trends across builds

`yer trend` records each run to a local append-only store (keyed by the stable
finding `signature`) and diffs a new run against history — **new / recurring /
regressed / fixed** — so CI can fail only on *new* regressions.

```bash
# seed the baseline once (no gate)
yer trend error-reports/*.txt --store .yer/trends.jsonl --record

# later builds: record and fail only if something new/regressed appears
yer trend error-reports/*.txt --store .yer/trends.jsonl --record --fail-on-new

# inspect the diff as JSON
yer trend error-reports/*.txt --store .yer/trends.jsonl --format json
```

The store holds only redacted titles + signatures + counts — never evidence,
config, or paths — and should stay gitignored (`.yer/`).

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

For SARIF code-scanning upload and a trend-based regression gate
(`yer trend --fail-on-new`), see the full recipes in [ci.md](ci.md).

## Commands at a glance

| Command | Purpose |
| --- | --- |
| `yer analyze <inputs>` | Parse + classify; print findings (`--format text/json/sarif`). |
| `yer report <inputs> --html <dir>` | Write self-contained HTML + `report.json` (+ SARIF via `--format sarif -o`). |
| `yer summarize <inputs>` | Emit token-bounded summary for Claude (`--format md/json`). |
| `yer trend <inputs> --store <path>` | Diff a run against history; gate with `--fail-on-new`. |

See [SPEC-003](specs/SPEC-003-cli.md) for the full CLI contract.
