# Working with the sample corpus

`yer` is developed against a corpus of **real** Yocto `error-report.txt` files in
[`error-reports/`](../error-reports/). This is the ground truth: rules, evidence
extraction, and the token/parse budgets are all validated against it. This page
explains how to add to it, verify, and turn a report into a committed fixture.

> **The corpus is local-only and gitignored** (`.gitignore` → `error-reports/`).
> Real reports can carry host identity and `local.conf` secrets, so they are
> **never committed**. Only the anonymized `tests/fixtures/*.json` derived from
> them are tracked.

## Where the files come from

`error_report_<UTCtimestamp>.txt` files are emitted by OpenEmbedded's
`report-error.bbclass` / `send-error-report`. Despite the `.txt` extension each
is a single JSON object (see [data-format.md](data-format.md)). You obtain them
from your own builds:

- Enable the reporter in your build: `INHERIT += "report-error"`. On a failing
  task, BitBake writes a report under
  `${LOG_DIR}/error-report/error_report_*.txt` (commonly `build/tmp/log/error-report/`).
- Or export them from an error-report server if your org runs one.

## Adding reports

There is no registry or index — the tools auto-discover reports via directory
scan and globs. Just drop files in:

```bash
cp build/tmp/log/error-report/error_report_*.txt error-reports/
# then, for example:
yer analyze error-reports/                 # scan the whole corpus
yer analyze error-reports/error_report_20260701180755.txt
```

Anything that reads inputs (`analyze`, `report`, `summarize`, `trend`) accepts a
file, a glob, a directory, or `-` for stdin.

## Verify after adding

The corpus harness is marked `slow` and **skips when the corpus is absent** (so
CI, which has no corpus, is unaffected). Run it locally:

```bash
pytest -m slow
```

This exercises:

- `tests/test_corpus_smoke.py` — every file ingests without raising (SPEC-001 T1)
  and the whole corpus (incl. the ~2 MB log) parses within the time budget.
- `tests/test_ci_artifacts.py::test_pipeline_over_corpus_does_not_crash` — the
  `report` + `analyze --format sarif` pipeline runs over the corpus and produces
  `index.html` + `report.json` + `results.sarif`.

A quick manual smoke, to confirm classification and privacy on new inputs:

```bash
yer analyze error-reports/ --format json | less        # every failure -> a finding
yer report error-reports/*.txt --html /tmp/yer-out     # open /tmp/yer-out/index.html
```

If a new report exposes a **new failure pattern** or a schema variant, follow the
spec-first loop ([spec-driven-workflow.md](spec-driven-workflow.md)): update the
SPEC (and `data-format.md` if the input understanding changed) **before** the
code, then add a fixture.

## Promoting a report to a committed fixture

Fixtures ([`tests/fixtures/`](../tests/fixtures/)) are a curated, anonymized
subset that lets contributors without the corpus run the golden tests. They are
selected explicitly, not automatically — adding a corpus file does **not** create
a fixture.

To add one (required whenever you handle a new failure category or pattern):

1. Pick the representative report from `error-reports/`.
2. Add a row to `MANIFEST` in
   [`tests/fixtures/derive_fixtures.py`](../tests/fixtures/derive_fixtures.py):
   `(source_report, output_fixture.json, category, "why this sample")`.
3. Regenerate and commit:

   ```bash
   python tests/fixtures/derive_fixtures.py
   ```

The script applies two scrub passes — wholesale replacement of
`local_conf`/`auto_conf`, then **structural** host-identity redaction
(`SSH_AUTH_SOCK` values and `/<host>/<user>/<date>/…` build roots) — and **fails
if any host-identity structure survives**. Site-specific extra pairs can go in a
gitignored `tests/fixtures/redactions.local`. Details and the fixture manifest
live in [tests/fixtures/README.md](../tests/fixtures/README.md).

Then add a golden/acceptance test that binds behavior to the new fixture, and run
`pytest` (plus `pytest -m slow` for the corpus).

## Privacy checklist

- [ ] The new report lives only under `error-reports/` (gitignored) — not staged
      for commit.
- [ ] Any derived fixture was produced by `derive_fixtures.py` (never hand-edited
      from a raw report) and the script reported no residual leak.
- [ ] Secrets that need a test (e.g. a `*_password` line for SPEC-005 redaction)
      use a **synthetic** fixture — do not un-scrub a real report.
