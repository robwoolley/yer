# Milestone 6 — Trends (cross-run history)

**Goal:** add the time axis. Persist each run's findings to a local, privacy-safe
store keyed by `signature`, then compare a new run against history to answer
"what changed since last time?" — **new / recurring / regressed / fixed** — via a
`yer trend` subcommand, an additive HTML/JSON trend layer, and a `--fail-on-new`
regression gate. Exit criteria: recording two runs and diffing classifies each
signature correctly; the store leaks no host identity/config/evidence; the diff
document is deterministic for a fixed (inputs, store snapshot).

Roadmap: [../docs/roadmap.md](../docs/roadmap.md) · Spec:
[SPEC-006](../docs/specs/SPEC-006-trends.md) · CLI:
[SPEC-003](../docs/specs/SPEC-003-cli.md) §1 · Render:
[SPEC-004](../docs/specs/SPEC-004-report-render.md) · DoD conventions:
[../CLAUDE.md](../CLAUDE.md)

Task id format `M6-nn`. Each task cites its spec section and a DoD tied to a
concrete SPEC-006 acceptance test. New core `trends/` modules stay **stdlib-only**
(json); keep render/CLI concerns out of them.

---

- [ ] **M6-01 — Run record + append-only JSONL store (`trends/store.py`)**
  - Spec: SPEC-006 §1.
  - `record_run(report, *, store_path, tool_version) -> RunRecord` appends one
    JSON-Lines row (`run_id`, `recorded_at`, `tool_version`, `source_count`,
    minimal `findings` with **redacted** titles + signatures, `summary`);
    `load_runs(store_path) -> list[RunRecord]` tolerates an absent/empty store
    and skips malformed lines. Store defaults to `./.yer/trends.jsonl` and is
    gitignored. Never persist evidence, `local_conf`/`auto_conf`, or input paths.
  - DoD: **SPEC-006 T2** (append-only; absent store ⇒ readable as empty history;
    malformed line skipped, not fatal) and **T3** (a run record contains no
    host-identity structure, no config, no evidence, no input paths).

- [ ] **M6-02 — Cross-run diff + signature history (`trends/diff.py`)**
  - Spec: SPEC-006 §2 (history fold) and §3 (classification).
  - Fold the store into per-signature history (first/last seen, `runs_present`,
    `total_occurrences`, `current_streak`), then
    `diff(report, runs, *, baseline=None) -> TrendDiff`: current findings tagged
    `status ∈ {new, recurring, regressed}` (signature-keyed mapping so `Finding`
    stays render-agnostic) plus a `fixed` list. Deterministic ordering.
  - DoD: **SPEC-006 T1** (only-in-current ⇒ `new`; in-both ⇒ `recurring`;
    only-in-baseline ⇒ `fixed`), **T5** (present→absent→present vs baseline =
    prior run ⇒ `regressed`, not `new`), and **T6** (byte-identical trend JSON
    for a fixed inputs+store snapshot).

- [ ] **M6-03 — `yer trend` CLI subcommand**
  - Spec: SPEC-006 §4; SPEC-003 §1.
  - `yer trend <inputs> [--store PATH] [--baseline ID] [--record] [--fail-on-new]`:
    analyze → diff vs baseline → render the trend view; append to the store only
    with `--record`. `--fail-on-new` exits `1` on any `new`/`regressed` finding;
    otherwise SPEC-003 §4 exit codes (`2` on tool/usage error).
  - DoD: **SPEC-006 T4** — `--record` writes a record; a later run with a
    brand-new failure + `--fail-on-new` exits `1`; a run with only recurring
    findings + `--fail-on-new` exits `0`.

- [ ] **M6-04 — Trend render layer (HTML + JSON)**
  - Spec: SPEC-006 §4 (render); SPEC-004 §1–2.
  - Additive only: per-finding badge (`new`/`recurring`/`regressed`) and a "fixed
    since baseline" list, in a clearly separated `trend` block. The canonical
    `report.json` finding fields and byte-stability for a fixed (inputs, store
    snapshot) are preserved; HTML stays self-contained.
  - DoD: a badge renders per finding and the fixed list appears; **SPEC-004 T3**
    still holds (canonical `report.json` body byte-identical across runs for the
    same inputs+store) and **T2** (no external asset references) still holds.

- [ ] **M6-05 — Docs: trend CI gating + gitignore the store**
  - Spec: SPEC-006 §1, §4; SPEC-003 §4.
  - Extend `docs/ci.md` with a `yer trend --record --fail-on-new` regression-gate
    example (store persisted/restored across runs via cache/artifact); add
    `.yer/` to `.gitignore`.
  - DoD: `docs/ci.md` shows the trend gating step and references the store; a
    test asserts the documented trend workflow parses and references
    `yer trend` + the store path; `.yer/` is gitignored.

---

### Next milestone
M6 is the final milestone on the current roadmap. When it exits (diff classifies
correctly; store is privacy-safe; trend JSON deterministic), any further scope
(e.g. a hosted dashboard or cross-repo aggregation — explicit non-goals in
SPEC-006) needs a new **SPEC-007** authored first, then a `tasks/milestone-7.md`.
