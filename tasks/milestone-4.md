# Milestone 4 — Static report

**Goal:** project the `Report` into publishable artifacts — a canonical,
deterministic `report.json` and a single self-contained `index.html` — via
`yer report <inputs> --html <dir>`. Exit criteria: the HTML opens offline (no
external requests); the same input yields a byte-identical `report.json`.

Roadmap: [../docs/roadmap.md](../docs/roadmap.md) · Spec:
[SPEC-004](../docs/specs/SPEC-004-report-render.md) · CLI:
[SPEC-003](../docs/specs/SPEC-003-cli.md) §1 · DoD conventions:
[../CLAUDE.md](../CLAUDE.md)

Task id format `M4-nn`. Each task cites its spec section and a DoD tied to a
concrete SPEC-004 acceptance test. `render/` may use **Jinja2** (a new dep, cli/
render only); core `parse`/`analyze`/`models` stay stdlib-only; keep render/CLI
concerns out of the core.

---

- [x] **M4-01 — Canonical `report.json` (`render/json_out.py`)**
  - Spec: SPEC-004 §1; SPEC-002 §6 ordering.
  - `to_report_json(report, *, tool_version) -> str`: `schema_version`,
    `tool_version`, `builds[]` (component/machine/distro/source/failure_count),
    `findings[]` (category/severity/confidence/title/recipe/task/file/line/
    evidence/signature/cascade_of/occurrences/affected_recipes), and
    `summary` (errors/warnings/by_category). Stable key order, findings sorted
    per SPEC-002, **no wall-clock timestamps** in the document body.
  - DoD: **SPEC-004 T3** — `report.json` validates against the schema and is
    byte-identical across two runs.

- [x] **M4-02 — Privacy: redact host identity + exclude config from artifacts**
  - Spec: SPEC-004 §4 (**update first**: add host-identity redaction, as in
    SPEC-005 §4 — `report.json`/HTML are published artifacts).
  - Reuse `redact.redact_host_identity` on finding evidence/titles in the
    artifacts; never render `local_conf`/`auto_conf` without `--include-config`
    (redaction still applies when opted in).
  - DoD: a `report.json` of a synthetic host-identity report contains no
    host-identity structure; config excluded by default.

- [ ] **M4-03 — Self-contained static HTML (`render/static.py` + templates)**
  - Spec: SPEC-004 §2.
  - Jinja2 → one `index.html`: **inline** CSS/JS, no external requests
    (assets as data-URIs), light & dark via `prefers-color-scheme`, findings
    grouped by recipe then category (collapsible), each showing severity,
    confidence, `file:line`, and evidence in a `<pre>`; cascades nested.
  - DoD: **SPEC-004 T2** (no `http(s)://` asset references; opens offline) and
    **T4** (a finding with `file`/`line` renders a location; one without still
    renders).

- [ ] **M4-04 — Per-finding "Copy for Claude" button**
  - Spec: SPEC-004 §2.
  - Each finding carries a "Copy for Claude" button that copies that finding's
    SPEC-005 Markdown (inline JS clipboard; no network).
  - DoD: a button is present per finding and copies the finding's Markdown
    summary (verify the payload is embedded in the page).

- [ ] **M4-05 — Responsive layout: long lines never break the page**
  - Spec: SPEC-004 §2, T5.
  - Wide content (evidence `<pre>`, tables) scrolls within its own
    `overflow-x` container; the page body never scrolls horizontally.
  - DoD: **SPEC-004 T5** — long evidence lines do not cause horizontal page
    scroll (assert the scroll-container CSS/markup around evidence).

- [ ] **M4-06 — `yer report` CLI subcommand**
  - Spec: SPEC-003 §1 (`report`); SPEC-004.
  - `cli.py` `report` subcommand: input resolution (SPEC-001), `--html <dir>`
    (required), optional `--format json -o <path>` for the canonical JSON
    elsewhere, plus the `analyze` filters and `--fail-on`/exit-code contract.
    Writes `<dir>/index.html` + `<dir>/report.json`.
  - DoD: **SPEC-004 T1** — `yer report error-reports/*.txt --html out/` writes
    `out/index.html` and `out/report.json`; exit codes match `analyze`.

---

### Next milestone
Create `tasks/milestone-5.md` from SPEC-003/004 (SARIF + CI hardening) when M4
exits (HTML opens offline; `report.json` byte-identical across runs).
