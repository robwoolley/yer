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
