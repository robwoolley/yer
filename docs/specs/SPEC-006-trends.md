# SPEC-006 — Trends (cross-run history)

- **Status:** Draft (M6 is a stretch goal; ratify before implementing)
- **Depends on:** [SPEC-002](SPEC-002-analyzer.md) (the `signature` primitive),
  [SPEC-003](SPEC-003-cli.md) (CLI/exit codes), [SPEC-004](SPEC-004-report-render.md) (render)
- **Modules:** `trends/store.py`, `trends/diff.py`, `trends/__init__.py`; render +
  CLI hooks

## Scope

Everything so far describes a **single run**. Trends add the time axis: persist
each run's findings to a local store keyed by the stable `signature` (SPEC-002
§4), then compare a new run against history to answer the question a CI owner
actually has — *"what changed since last time?"* — as **new / recurring / fixed**
findings, plus a per-signature history. This is the M6 stretch layer; the core
pipeline does not depend on it.

Non-goals (v1): a hosted dashboard, cross-repo aggregation, and statistical
flakiness scoring. The store is a local file; there are no network calls.

## 1. The run record & store (`store.py`)

- A **run record** is the minimal, privacy-safe projection of a `Report`:

```jsonc
{
  "run_id": "sha1:…",          // stable hash of (sorted signatures + tool_version)
  "recorded_at": "2026-07-04T18:00:00Z",  // wall-clock; store is history, not an artifact
  "tool_version": "x.y.z",
  "source_count": 12,           // number of input reports; never the paths
  "findings": [                 // one row per finding in the run
    { "signature": "sha1:…", "category": "configure", "severity": "error",
      "recipe": "gz-gui9", "title": "package \"Qt5\" considered NOT FOUND" }
  ],
  "summary": { "errors": 1, "warnings": 0, "by_category": { "configure": 1 } }
}
```

- **Storage:** append-only **JSON Lines** — one run record per line — at
  `--store <path>` (default `./.yer/trends.jsonl`). Appending a run never
  rewrites earlier lines. A missing/empty store means "no history" (first run:
  everything is new). A malformed line is skipped defensively, never fatal.
- **What is NOT stored:** raw evidence, `local_conf`/`auto_conf`, or input paths.
  Titles are stored **after** SPEC-004 §4 host-identity redaction. The store is a
  local artifact and MUST be gitignored (like `error-reports/`).

## 2. Signature history

Folding the store yields, per `signature`: `first_seen` / `last_seen`
(`run_id` + timestamp), `runs_present` (count), `total_occurrences`, and
`current_streak` (consecutive most-recent runs containing it). History is the
input to both the diff (§3) and any future regression view.

## 3. Diff & status classification (`diff.py`)

Compare the current run **C** against a **baseline B** (default: the immediately
previous run in the store; overridable with `--baseline <run_id>`):

- **new** — signature in C, not in B, and not in any run older than B either.
- **recurring** — signature in both C and B.
- **regressed** — signature in C, absent in B, but present in some run *older*
  than B (fixed then came back).
- **fixed** — signature in B, not in C. Listed separately (fixed findings are, by
  definition, absent from the current `Report`).

`diff(report, store, *, baseline=None) -> TrendDiff` returns the current
findings tagged with a `status ∈ {new, recurring, regressed}` (a mapping keyed by
signature, so `Finding` stays render-agnostic) plus the list of `fixed`
signatures with their last-seen metadata. Ordering is deterministic given the
store contents.

## 4. CLI & render integration

- **`yer trend <inputs> [--store PATH] [--baseline ID] [--record] [--fail-on-new]`**
  (SPEC-003 §1): analyze inputs → `Report`, compute the diff vs baseline, render
  the trend view, and — only with `--record` — append the run to the store.
  - `--fail-on-new`: exit `1` when any **new** or **regressed** finding is
    present (regression gating), independent of the base `--fail-on` severity
    threshold. Exit codes otherwise follow SPEC-003 §4 (`2` on tool/usage error).
  - `--record` is explicit so a dry run never mutates history.
- **Render:** the HTML/JSON reports gain an optional trend layer — a per-finding
  badge (`new` / `recurring` / `regressed`) and a "fixed since baseline" list.
  This is additive to SPEC-004; the deterministic `report.json` body stays
  byte-identical for a given (inputs, store snapshot), and the badge lives in a
  clearly separated `trend` block, not the canonical finding fields.

## 5. Determinism & privacy (cross-cutting)

- The **store** carries timestamps (it is a history log, not a published
  artifact). Everything derived from it — the diff document, the trend badges —
  is deterministic for a fixed (inputs, store snapshot): no wall-clock leakage
  into the diff body.
- Redaction is enforced at write time (titles) and re-checked at render time.
  The store never contains evidence, config, or input paths, so publishing a
  trend report cannot leak host identity that the store did not already exclude.

## 6. Acceptance tests

- **T1** Record run A then run B; diff B vs A: a signature only in B → `new`;
  in both → `recurring`; only in A → `fixed`.
- **T2** The store is append-only JSONL: recording twice appends two lines and
  leaves the first untouched; an absent store makes the first run all-`new`; a
  malformed line is skipped, not fatal.
- **T3** A run record contains no host-identity structure, no `local_conf`/
  `auto_conf`, no evidence, and no input paths.
- **T4** `yer trend <inputs> --record` writes a record; a later run with a
  brand-new failure and `--fail-on-new` exits `1`; a run with only recurring
  findings and `--fail-on-new` exits `0`.
- **T5** A signature present in run 1, absent in run 2, present in run 3 →
  status `regressed` (not `new`) when the baseline is run 2.
- **T6** The diff document is deterministic: the same (inputs, store snapshot)
  yields byte-identical trend JSON across runs.

## Changelog

- **2026-07-04 (M6 authoring):** Initial draft. Grounded on the existing
  `signature` primitive (SPEC-002 §4) and `FindingGroup` within-run dedup;
  chooses an append-only local JSONL store, a new/recurring/regressed/fixed diff
  against a configurable baseline, a `yer trend` subcommand with `--record` /
  `--fail-on-new`, and an additive render layer that preserves SPEC-004
  determinism. Status stays **Draft** until ratified.
