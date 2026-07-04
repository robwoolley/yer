# Milestone 5 — CI hardening

**Goal:** make `yer` a first-class CI citizen — emit SARIF 2.1.0 for
code-scanning annotations, document the exit-code contract and a runnable
GitHub Actions recipe, and verify artifact publishing (HTML + `report.json` +
`results.sarif`) on a sample pipeline. Exit criteria: `yer analyze --format
sarif` produces valid, deterministic SARIF; a documented CI job uploads the
artifacts and code-scanning results; exit codes match the SPEC-003 contract.

Roadmap: [../docs/roadmap.md](../docs/roadmap.md) · Specs:
[SPEC-004](../docs/specs/SPEC-004-report-render.md) §3 (SARIF),
[SPEC-003](../docs/specs/SPEC-003-cli.md) §4 (exit codes) · DoD conventions:
[../CLAUDE.md](../CLAUDE.md)

Task id format `M5-nn`. Each task cites its spec section and a DoD tied to a
concrete acceptance test. `render/sarif.py` is render-only; core
`parse`/`analyze`/`models` stay stdlib-only; keep render/CLI concerns out of the
core.

---

- [x] **M5-01 — SARIF acceptance tests (spec-first: SPEC-004 §3 → §5)**
  - Spec: SPEC-004 §3 (**update first**): §3 defines the SARIF mapping but §5
    has no SARIF acceptance test. Add **T7/T8** to §5 (with a dated `## Changelog`
    note) making the mapping verifiable: a 2.1.0 document with one `run`, tool
    driver `yer`, `rules[]` derived from categories, and each finding a `result`
    (`ruleId = category`, `level` mapped from severity, `physicalLocation` from
    `file`/`line` when present); deterministic/byte-stable.
  - DoD: SPEC-004 §5 lists concrete SARIF acceptance tests (T7 structure/mapping,
    T8 determinism) and §3 carries the Changelog note. No code yet.

- [x] **M5-02 — `render/sarif.py` SARIF 2.1.0 emitter**
  - Spec: SPEC-004 §3; SPEC-002 §6 ordering.
  - `to_sarif(report, *, tool_version) -> str`: SARIF 2.1.0 (`$schema`, `version`
    `"2.1.0"`), one `run` with `tool.driver.name = "yer"` + `version`, `rules[]`
    from the distinct categories, and `results[]` in analyzer rank order — each
    with `ruleId = category`, `level` from severity (`error`→error,
    `warning`→warning, else note), `message.text` = redacted title, and
    `physicalLocation.artifactLocation.uri` + `region.startLine` when `file`/
    `line` are present. No wall-clock timestamps; host-identity redaction per
    SPEC-004 §4.
  - DoD: **SPEC-004 T7** — output is valid 2.1.0 with the specified mapping; a
    finding with `file`/`line` yields a `physicalLocation`, one without omits it.

- [x] **M5-03 — Wire SARIF into the CLI (`--format sarif`)**
  - Spec: SPEC-003 §1 (`analyze --format {text,json,sarif}`); SPEC-004 §3.
  - Add `sarif` to `analyze --format` (and accept `report --format sarif -o
    <path>` to emit `results.sarif` alongside the HTML/JSON artifacts). Exit-code
    contract unchanged (SPEC-003 §4).
  - DoD: **SPEC-004 T8** — `yer analyze <inputs> --format sarif` writes valid,
    byte-identical-across-runs SARIF; exit codes match `analyze`.

- [x] **M5-04 — Documented exit-code contract + GitHub Actions recipe**
  - Spec: SPEC-003 §4/§5; SPEC-004.
  - Add a docs section (CI recipe) with a runnable GitHub Actions workflow:
    `yer report … --html out/`, `yer analyze … --format sarif -o results.sarif`,
    gating on the exit code, `upload-artifact` for `out/`, and
    `upload-sarif` (code-scanning). Document the 0/1/2 exit-code table.
  - DoD: docs contain a copy-pasteable workflow and the exit-code table; a test
    asserts the documented workflow YAML parses and references the artifacts.

- [x] **M5-05 — Verify artifact publishing on a sample pipeline**
  - Spec: roadmap M5; SPEC-004 T1/T3, SPEC-004 §3.
  - A CI-smoke test that runs the `report` + `analyze --format sarif` path over
    fixtures and asserts `index.html`, `report.json`, and `results.sarif` are all
    produced, self-contained, and re-runnable to byte-identical output; confirm
    the SARIF is shaped for code-scanning upload (`runs[].results[]`).
  - DoD: the smoke test produces and validates all three artifacts; corpus run
    does not crash.

---

### Next milestone
Create `tasks/milestone-6.md` (Trends — stretch) from a new **SPEC-006** when M5
exits (SARIF valid + deterministic; CI recipe documented; artifacts verified).
Author SPEC-006 first — M6 has no spec yet.
