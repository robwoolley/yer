# Using `yer` in CI

`yer` is built to gate a Yocto/OpenEmbedded pipeline and publish shareable
artifacts. This page documents the **exit-code contract** (SPEC-003 §4) and a
copy-pasteable **GitHub Actions** recipe that publishes the HTML + JSON report
and uploads SARIF for code-scanning annotations.

## Exit-code contract (SPEC-003 §4)

`yer analyze` / `yer report` return:

| Code | Meaning |
| ---- | ------- |
| `0`  | No finding at or above `--fail-on` (or `--fail-on none`). |
| `1`  | At least one finding at/above `--fail-on` (default threshold: `error`). |
| `2`  | Tool/usage error (bad arguments, no matching inputs, unwritable output). |

Severity order for thresholding is `error` > `failure` > `warning` > `anomaly`.
A malformed report contributes a parse finding at `error` severity, so a corrupt
input under the default `--fail-on error` yields exit `1`, not `2`.

## GitHub Actions recipe

Run this after your Yocto build has produced `error-report.txt` files (the
`send-error-report` payloads). It writes a self-contained HTML report plus
`report.json`, uploads them as a build artifact, and pushes SARIF to GitHub code
scanning — while still failing the job when there are error-level findings.

```yaml
name: Yocto error report
on: [push]

jobs:
  yocto-error-report:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write   # required for upload-sarif
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install yer
        run: pip install yocto-error-reports

      - name: Analyze error reports
        id: yer
        continue-on-error: true   # let the uploads run even when findings exist
        run: |
          yer report error-reports/*.txt --html out/
          yer analyze error-reports/*.txt --format sarif -o results.sarif --fail-on error

      - name: Upload HTML + JSON report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: yocto-error-report
          path: out/

      - name: Upload SARIF to code scanning
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif

      - name: Fail on error-level findings
        if: steps.yer.outcome == 'failure'
        run: exit 1
```

Notes:

- `continue-on-error: true` on the analyze step lets the artifact and SARIF
  uploads run even when `yer` exits `1`; the final step re-propagates the
  failure so the job status reflects the findings.
- `out/` contains `index.html` (open it offline — no external requests) and the
  canonical, deterministic `report.json`.
- `results.sarif` drives code-scanning annotations; `security-events: write` is
  required for `upload-sarif`.

## Regression gating with trends

To fail a build only when a **new or regressed** failure appears (not on
pre-existing, already-known failures), record each run to a persistent store and
gate with `yer trend --fail-on-new`. The store (`.yer/trends.jsonl`) is carried
between runs with `actions/cache`, keyed so each run restores the latest history
and saves the updated store back.

```yaml
name: Yocto error trend
on: [push]

jobs:
  yocto-error-trend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install yer
        run: pip install yocto-error-reports

      # restore the run history from the previous build and save the updated
      # store back (the key rolls forward each run so history accumulates).
      - name: Restore trend store
        uses: actions/cache@v4
        with:
          path: .yer
          key: yer-trends-${{ github.run_id }}
          restore-keys: yer-trends-

      - name: Trend gate (fail only on new/regressed findings)
        run: |
          yer trend error-reports/*.txt --store .yer/trends.jsonl --record --fail-on-new
```

Notes:

- `--record` appends the current run to `.yer/trends.jsonl`; the next build's
  `restore-keys: yer-trends-` picks up the most recent cached store.
- `--fail-on-new` exits `1` only when a `new` or `regressed` signature is
  present, so a backlog of known failures does not keep the pipeline red.
- The store holds only redacted titles + signatures + counts — never evidence,
  config, or input paths — and is gitignored (`.yer/`); do not commit it.
- **First run:** with no history every finding is `new`, so `--fail-on-new`
  exits `1`. Seed the store once on a known baseline (run `yer trend … --record`
  without `--fail-on-new`) before enforcing the gate.
