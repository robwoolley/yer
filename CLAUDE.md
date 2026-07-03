# CLAUDE.md — Operating guide for this repository

This project is developed **spec-first**. Read this before writing code.

## What this project is

`yer` — a Python CLI that parses Yocto `error-report.txt` (JSON) files, extracts
and classifies build failures into ranked **findings**, and renders them as
terminal output, static HTML/JSON artifacts, and token-bounded LLM summaries.

## The golden rule: specs lead code

1. Behaviour is defined in [docs/specs/](docs/specs/) **before** it is
   implemented. If code and spec disagree, the spec wins — or the spec is
   updated in the same change with a clear rationale.
2. Every implementation task in [tasks/](tasks/) names the spec section it
   satisfies. Do not implement beyond the referenced spec without updating it.
3. When you discover the spec is wrong or underspecified (e.g. a new log
   pattern in a sample), **update the spec first**, then the code, then add a
   fixture.

See [docs/spec-driven-workflow.md](docs/spec-driven-workflow.md) for the full
workflow and file conventions.

## Architecture in one line

`ingest → parse → analyze → summarize → render`, five decoupled stages sharing
the dataclasses in `models.py`. Details: [docs/architecture.md](docs/architecture.md).

## Ground truth: the sample corpus

- Real reports live in [`error-reports/`](error-reports/) (77 files). **Use
  them.** Never invent format details — verify against these.
- The format is documented in [docs/data-format.md](docs/data-format.md).
- Any new failure pattern you handle MUST get a fixture under `tests/fixtures/`
  (anonymized) plus a golden-output test.

## Conventions

- **Python 3.11+.** Core `parse`/`analyze`/`models` modules: **stdlib only.**
  Rendering may use Jinja2; terminal may use `rich`. Keep deps out of the core.
- Parsing is **defensive**: every report field is optional; never index a
  missing key; tolerate unknown keys and empty `failures`.
- Logs can be **2 MB+**. Never load-and-hold more than needed; extraction is
  **tail-biased** and token-bounded.
- **Privacy:** never emit `local_conf`/`auto_conf` into shareable output or LLM
  summaries without explicit opt-in + redaction.
- Findings carry a stable `signature` hash (path/number/hex-normalized) so the
  same failure dedups within a run and across runs (future trend layer).
- CI contract: exit `0` clean, `1` findings at/above `--fail-on`, `2` tool error.

## Definition of done for a component

- Matches its SPEC section, referenced by task id.
- Has fixture-backed tests (golden files where applicable).
- Runs cleanly against the real `error-reports/` corpus without crashing.
- Docs/specs updated if behaviour changed.

## Do not

- Do not add network calls to the core tool (LLM integration is summary-only).
- Do not commit real, un-anonymized customer data as fixtures.
- Do not let `render`/CLI concerns leak into `parse`/`analyze`.
