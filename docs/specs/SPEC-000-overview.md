# SPEC-000 — Product Overview & Requirements

- **Status:** Approved
- **Owners:** rob@robertwoolley.com
- **Supersedes / depends on:** none (root spec)

## 1. Problem

A failed Yocto/OpenEmbedded build emits an `error-report.txt` (JSON) whose
substance is one or more raw task logs, up to ~2 MB each, dominated by
`NOTE:`/`DEBUG:` noise. Developers waste time locating the real cause; CI has no
structured signal; and the logs are too large to hand to an LLM verbatim.

## 2. Goals

- **G1** Parse `error-report.txt` files robustly (see [data-format](../data-format.md)).
- **G2** Extract and **classify** failures into ranked, deduplicated findings.
- **G3** Serve three consumers from one findings model: developers (terminal),
  CI (artifacts + exit codes), and Claude (token-bounded summary).
- **G4** Be trivial to run locally and in CI; core has no third-party deps.

## 3. Non-goals (v1)

- Parsing raw bitbake console output or individual `log.do_*` files (future).
- Querying `errors.yoctoproject.org` / error-report-web (future).
- A persistent dashboard service or database (v1 is static artifacts).
- Making Claude API calls from the tool (summary is emitted; user pipes it).
- Auto-applying fixes.

## 4. Users & primary use cases

| User | Use case |
| --- | --- |
| Developer | Run `yer analyze report.txt`, see the root cause in seconds. |
| Developer | `yer summarize … --for-llm | claude` to get a fix suggestion. |
| CI | Fail the job on real errors; publish an HTML/JSON artifact. |
| Team lead | Skim a static report across many failed recipes. |

## 5. Functional requirements

- **FR1** Accept file paths, globs, directories, and stdin.
- **FR2** Tolerate schema drift and malformed reports without crashing (FR2 is
  a hard requirement — verified against the full corpus).
- **FR3** Classify each failure into one of: `compile`, `configure`, `patch`,
  `qa`, `fetch`, `dependency`, `unknown` (fallback). No failure is dropped.
- **FR4** Deduplicate identical findings within a report and across reports in
  one run, keyed by a stable `signature`.
- **FR5** Rank findings; identify likely root cause vs cascade.
- **FR6** Output formats: `text` (terminal), `json`, `sarif` (fast-follow),
  self-contained `html`.
- **FR7** LLM summary is token-bounded and privacy-scrubbed.
- **FR8** Exit codes: `0` clean, `1` findings ≥ `--fail-on`, `2` tool error.

## 6. Non-functional requirements

- **NFR1** Python 3.11+; core modules stdlib-only.
- **NFR2** Analyze the full 77-file corpus in a few seconds; handle a 2 MB log.
- **NFR3** Deterministic canonical output (`report.json` byte-stable per input).
- **NFR4** Privacy: never leak `local_conf`/`auto_conf` without opt-in.
- **NFR5** Extensible: new failure category = one rule module + fixture.

## 7. Acceptance (v1 done)

Running `yer` against `error-reports/*.txt`:
1. Loads all files without raising.
2. Produces ≥1 correctly-categorized finding per file.
3. `--fail-on error` returns exit 1 on files with errors.
4. `yer summarize` output for the largest report is under the token budget.
5. `yer report --html` opens offline and is deterministic.

## 8. Component specs

| Spec | Component |
| --- | --- |
| [SPEC-001](SPEC-001-parser.md) | Ingest + parse |
| [SPEC-002](SPEC-002-analyzer.md) | Analyzer (rules, dedup, ranking) |
| [SPEC-003](SPEC-003-cli.md) | CLI + exit codes |
| [SPEC-004](SPEC-004-report-render.md) | Static report rendering |
| [SPEC-005](SPEC-005-llm-summary.md) | LLM summary |

## 9. Open questions

- **OQ1** `signature` normalization: conservative (v1 default) vs aggressive?
- **OQ2** Ship SARIF in v1 (M2/M4) or defer to M5?
- **OQ3** License choice (task M0-05). **Resolved 2026-07-03: MIT.**
