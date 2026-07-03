# Milestone 2 — Analyzer + terminal

**Goal:** classify each failure into ranked, deduplicated `Finding`s across all
six categories + fallback, and expose them through `yer analyze` with rich
terminal output, `--format text/json`, and the CI exit-code contract. Exit
criteria: every corpus file yields ≥1 correctly-categorized finding; golden-file
tests pass; first-error-as-root-cause is verified on samples.

Roadmap: [../docs/roadmap.md](../docs/roadmap.md) · Specs:
[SPEC-002](../docs/specs/SPEC-002-analyzer.md) (analyzer),
[SPEC-003](../docs/specs/SPEC-003-cli.md) (CLI) · DoD conventions:
[../CLAUDE.md](../CLAUDE.md)

Task id format `M2-nn`. Each task cites its spec section and a DoD tied to a
concrete acceptance test. Core `analyze`/`parse`/`models` stay **stdlib-only**
(`rich` is allowed only in `cli.py`); CLI concerns never leak into `analyze`.

---

- [x] **M2-01 — Rule registry + analyze orchestration skeleton**
  - Spec: SPEC-002 §1 (rule registry), §6 (Output).
  - `analyze/signatures.py`: `Rule` record + a module-level registry with a
    `register`/lookup API. `analyze/__init__.py`: `analyze(builds) -> Report`
    that runs each failure's parsed `LogLine[]` through the rules, collects hits,
    and carries ingest-time `Build.findings` (parse findings) into
    `Report.findings`. Adding a category = a new `rules/` module, no orchestrator
    edit.
  - DoD: a trivial registered rule matches a crafted failure; `analyze([])`
    returns an empty deterministic `Report`; parse-finding Builds surface in
    `Report.findings`.

- [x] **M2-02 — Fallback rule + evidence extraction**
  - Spec: SPEC-002 §2 (`fallback.py`), §3 (evidence).
  - `rules/fallback.py`: any remaining `level=="ERROR"` (else last `WARNING`) →
    an `unknown` finding, guaranteeing every failure yields ≥1. Evidence helper:
    ≤ N lines (default 15), tail-biased, `NOTE:`/`DEBUG:` stripped unless sole
    content; never the whole log.
  - DoD: **SPEC-002 T6** — every corpus file yields ≥1 finding; evidence never
    exceeds N lines and excludes NOTE/DEBUG noise.

- [x] **M2-03 — `dependency` + `fetch` rules**
  - Spec: SPEC-002 §2 (dependency, fetch).
  - `rules/dependency.py`: `kind=="message"` / `Nothing provides` / `No provider`
    → `dependency`, title = missing provide, recipe from `package`.
    `rules/fetch.py`: `do_fetch` + `Unable to fetch`/`Network`/checksum mismatch →
    `fetch`, title = URI + reason.
  - DoD: `dependency_moveit` → one `dependency` finding; `fetch_dartsim` →
    a `fetch` finding (part of **SPEC-002 T1**).

- [x] **M2-04 — `patch` rule**
  - Spec: SPEC-002 §2 (patch).
  - `rules/patch.py`: `Hunk #\d+ FAILED`, `does not apply`, `rejects in file` →
    `patch`; title = patch/first failing file+hunk; `file`/`line` from
    `Hunk #N FAILED at <line>`.
  - DoD: **SPEC-002 T4** — `patch_ogre-next` → `patch`, `file` =
    `OgreMathlibNEON.h`, hunk line 601 (golden-file check).

- [x] **M2-05 — `qa` rule + within-finding dedup**
  - Spec: SPEC-002 §2 (qa), §4 (within-finding collapse).
  - `rules/qa.py`: `ERROR: QA Issue:` / `Fatal QA errors were found` → `qa`;
    collapse the many near-identical per-symlink lines into one finding with a
    count.
  - DoD: **SPEC-002 T2** — `qa_gz-physics-vendor` → **one** qa finding carrying a
    symlink count, not 14 (golden-file check).

- [x] **M2-06 — `configure` + `compile` rules (content over task name)**
  - Spec: SPEC-002 §2 (configure, compile + grounded notes).
  - `rules/configure.py`: `CMake Error at`, `Configuring incomplete`,
    `package "X" … NOT FOUND`; `file`/`line` from `CMakeLists.txt:<n>`.
    `rules/compile.py`: `ninja: build stopped`, gcc/clang `error:`,
    `undefined reference to`. Rules match on **content**, so configure-style
    signals win even under `do_compile`.
  - DoD: **SPEC-002 T3** — `compile_gz-sim-vendor` classifies as `configure`
    (Qt6 NOT FOUND), not `compile`; `compile_nanoflann` → `compile`;
    `configure_gz-gui9` → `configure`. Completes **SPEC-002 T1** across the six
    category fixtures.

- [x] **M2-07 — Signatures + cross-report dedup groups**
  - Spec: SPEC-002 §4 (dedup), reuse `parse.normalize`.
  - `analyze/dedup.py`: `signature = sha1(normalize(category + "\n" + title +
    "\n" + top_evidence))`; group duplicate findings across reports in one run
    into `FindingGroup`s (occurrence count + affected recipes). Conservative v1.
  - DoD: identical failures across two reports share a `signature` and collapse
    into one group with `occurrences == 2`; `Report.groups` populated
    deterministically.

- [x] **M2-08 — Ranking + root-cause vs cascade**
  - Spec: SPEC-002 §5.
  - Sort findings by `(severity_rank, phase_order, -confidence, recipe)` with
    `phase_order` fetch < patch < configure < compile < qa. Within one failure,
    the earliest `error`-severity finding is the root cause; later same-category
    errors get `cascade_of = <root signature>` (not dropped).
  - DoD: **SPEC-002 T5** — a 22-failure report yields ≤22 findings, correctly
    deduped and ranked; first-error-as-root-cause verified on a sample; ordering
    is deterministic.

- [x] **M2-09 — `yer analyze`: text output, input resolution, exit codes**
  - Spec: SPEC-003 §1, §2, §3, §4; SPEC-000 FR8.
  - `cli.py` `analyze` subcommand: resolve inputs (SPEC-001), render `text`
    (rich if available; grouped by recipe, cascades nested; footer
    `N errors, M warnings — exit K`), and wire `--fail-on {error,failure,
    warning,none}` to the exit-code contract (0/1/2). Supersedes the provisional
    `inventory` command.
  - DoD: **SPEC-003 T1** (`analyze error-reports/*.txt` → exit 1, ranked
    findings), **T2** (`--fail-on none` → exit 0), **T4** (no inputs / bad path →
    exit 2, stderr message); SPEC-000 acceptance #3.

- [x] **M2-10 — `analyze --format json`, filters, `--no-color`**
  - Spec: SPEC-003 §1, §3, §5.
  - Deterministic `--format json` (byte-stable; canonical `report.json` schema
    conformance is finalized in M4/SPEC-004), `--category`/`--recipe` filters,
    `--max-evidence`, and `--no-color`/`NO_COLOR` plain-ASCII output.
  - DoD: **SPEC-003 T3** (json byte-stable across two runs), **T5** (`--no-color`
    → plain ASCII), **T6** (`--recipe gz-gui9` filters to that recipe).

---

### Next milestone
Create `tasks/milestone-3.md` from SPEC-005 (LLM summary) acceptance tests when
M2 exits (every corpus file ≥1 correctly-categorized finding; golden tests pass;
exit-code contract green).
