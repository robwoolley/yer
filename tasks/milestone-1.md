# Milestone 1 — Ingest + Parse

**Goal:** turn input sources into schema-tolerant `Build` objects and each
failure's raw `log` into structured `LogLine[]` — **no classification yet**.
Exit criteria: analyzing the whole corpus never raises; malformed input yields a
parse-finding `Build`, not a crash; the 2.1 MB log parses within budget.

Roadmap: [../docs/roadmap.md](../docs/roadmap.md) · Spec:
[../docs/specs/SPEC-001-parser.md](../docs/specs/SPEC-001-parser.md) · DoD
conventions: [../CLAUDE.md](../CLAUDE.md)

Task id format `M1-nn`. Each task cites its spec section and a definition of done
(DoD) tied to a concrete SPEC-001 acceptance test. Core `ingest`/`parse`/`models`
stay **stdlib-only**; no CLI/render concerns.

---

- [x] **M1-01 — Ingest one report → `Build`**
  - Spec: SPEC-001 §1 (parsing rules), data-format §"Failure object schema".
  - Load a single file; extension is opaque (detect via `json.loads`); map
    top-level + failure fields to `Build`/`Failure`; every field optional;
    unknown keys preserved in `Build.raw`; `failures` absent/empty → `[]`;
    infer `Failure.kind` (`do_*` task → `"task"`, else `"message"`).
  - DoD: the 7 fixtures load to `Build`; **SPEC-001 T3** (`"Nothing provides …"`
    → `kind="message"`) and **T4** (missing `recipe` → `None`) pass on
    `dependency_moveit.json`.

- [x] **M1-02 — Input resolution: paths, globs, dirs, stdin**
  - Spec: SPEC-001 §1 (Inputs, Output).
  - Accept file paths, globs, directories (recursively yield files that parse as
    reports), and `-` (stdin). De-duplicate repeated paths; return `list[Build]`
    in stable input order.
  - DoD: pointing ingest at a directory yields one `Build` per report;
    duplicate paths are collapsed; ordering is deterministic across runs.

- [ ] **M1-03 — Malformed input → parse-finding `Build` (never raise)**
  - Spec: SPEC-001 §1 (Error handling, FR2).
  - A non-JSON or wrong-shape file MUST NOT raise; instead emit a `Build`
    carrying a synthetic parse `Finding` (`category="unknown"`,
    `severity="error"`, title = the parse problem). Add a small **synthetic**
    malformed fixture under `tests/fixtures/` (truncated/garbage — no real data).
  - DoD: **SPEC-001 T2** passes — the garbage fixture yields a parse-finding
    `Build`, not an exception.

- [ ] **M1-04 — Parse `log` → `LogLine[]`**
  - Spec: SPEC-001 §2 (`log` → `LogLine[]`), §3 (performance).
  - Iterate lines (no whole-string regex over 2 MB); split a leading
    `^(ERROR|WARNING|NOTE|DEBUG):\s?` token into `LogLine.level`, remainder →
    `.text`; keep sub-tool indentation; preserve 1-based `.n`.
  - DoD: **SPEC-001 T5** passes on `qa_gz-physics-vendor.json`
    (`ERROR: QA Issue:` → level `ERROR`, text `QA Issue:…`); the 560 KB / 2.1 MB
    logs parse via streaming within the few-second budget.

- [ ] **M1-05 — Backtrace block → structured frames**
  - Spec: SPEC-001 §2 (Backtrace block), data-format §"The BB backtrace block".
  - Detect `WARNING: Backtrace (BB generated script):` and the following
    `#N: <func>, <path>, line <n>` frames; expose parsed frames for the analyzer
    to confirm the failing function/task.
  - DoD: **SPEC-001 T6** passes — frames extracted from
    `configure_gz-gui9.json` (`cmake_do_configure` / `do_configure`, path, line).

- [ ] **M1-06 — Shared `normalize()` helper**
  - Spec: SPEC-001 §2 (Path normalization helper).
  - Provide `normalize(text)` mapping `TOPDIR/…` paths, absolute temp paths, line
    numbers, hex addresses, and PIDs (e.g. `run.do_compile.2609824`) to stable
    placeholders. Defined in `parse` so `parse`/`analyze` share one normalizer
    (feeds SPEC-002 `signature`).
  - DoD: unit tests show stable output on fixture-derived lines
    (e.g. `run.do_compile.<N>` → placeholder; `TOPDIR/...:123` → path+line
    normalized); idempotent (`normalize(normalize(x)) == normalize(x)`).

- [ ] **M1-07 — Wire corpus smoke to `ingest` + 2 MB perf budget**
  - Spec: SPEC-001 T1, §3.
  - Upgrade the M0-07 harness (`tests/test_corpus_smoke.py`) to call
    `ingest.load_report` and assert a `Build` per file; add a timing assertion
    that the largest (2.1 MB) report parses within budget.
  - DoD: **SPEC-001 T1** green via `ingest` over all 77 files; the large-log
    parse completes within the few-second corpus budget.

- [ ] **M1-08 — Failure inventory demo (recipe/task counts)**
  - Spec: SPEC-001 §1 (Output `Build[]`); roadmap M1 demoable outcome.
  - Add a pure `inventory(builds)` helper returning per-task/per-recipe counts,
    plus a **minimal** printout of the corpus inventory. Thin and provisional —
    superseded by the M2 `analyze` CLI (SPEC-003); keep presentation out of
    `ingest`/`parse` internals.
  - DoD: running over `error-reports/` reports counts matching data-format's
    distribution (compile 60 · configure 31 · patch 27 · qa 12 · fetch 1 ·
    dependency 2); helper is unit-tested on the fixtures.

---

### Next milestone
Create `tasks/milestone-2.md` from SPEC-002 (analyzer) + SPEC-003 (CLI)
acceptance tests when M1 exits (corpus never raises; T1–T6 green).
