# Milestone 3 — LLM summary

**Goal:** project the ranked `Finding[]` into a compact, **token-bounded**,
privacy-scrubbed `Summary` and expose it as `yer summarize`, emitting Markdown
(default) or JSON suitable to pipe into Claude. Exit criteria: the summary for the
2.1 MB report stays under the token budget; a round-trip `yer summarize | claude`
produces a plausible fix on ≥3 category samples.

Roadmap: [../docs/roadmap.md](../docs/roadmap.md) · Spec:
[SPEC-005](../docs/specs/SPEC-005-llm-summary.md) · CLI:
[SPEC-003](../docs/specs/SPEC-003-cli.md) §1 · DoD conventions:
[../CLAUDE.md](../CLAUDE.md)

Task id format `M3-nn`. Each task cites its spec section and a DoD tied to a
concrete SPEC-005 acceptance test. Core `summarize` is **stdlib-only** and makes
**no network calls** (the tool emits text; the user pipes it). CLI/render lives in
`cli.py`.

---

- [x] **M3-01 — Selection → `Summary` (top-K, tail-biased, truncation accounting)**
  - Spec: SPEC-005 §1; architecture §"The data model" (`Summary`).
  - `summarize.py`: `summarize(report, *, budget, top_k=5, max_evidence=8) ->
    Summary`. Select top-K findings by rank; ≤ M evidence lines each,
    tail-biased; **always keep** recipe/task/category/`file:line`/first-error;
    record `findings_omitted` and `log_lines_dropped`.
  - DoD: **SPEC-005 T5** — for a multi-finding report the rank-1 root cause is
    always present, even at a small `--budget`; truncation counts are correct.

- [x] **M3-02 — Token-budget bounding**
  - Spec: SPEC-005 §1 (token budget).
  - Enforce the emitted summary fits under budget (default ~4000 tokens;
    approximate via a chars/4 heuristic). Trim evidence, then findings, recording
    drops in the `truncated` block.
  - DoD: **SPEC-005 T1** — the summary for the largest (2.1 MB) corpus report is
    under the default token budget.

- [x] **M3-03 — Markdown output (`--format md`)**
  - Spec: SPEC-005 §2.
  - Render a `Summary` to human/model-pasteable Markdown: build header
    (component/machine/distro/target/bitbake/branch), per-finding section with the
    root-cause line and a fenced evidence block, and a "(N findings omitted; K log
    lines dropped)" note.
  - DoD: output matches the SPEC-005 §2 shape on the `configure_gz-gui9` fixture
    (golden-ish); root cause + `file:line` present.

- [x] **M3-04 — JSON output (`--format json`) + `truncated` block**
  - Spec: SPEC-005 §3.
  - Render a `Summary` to deterministic JSON: `build` subset, `findings`
    (category/confidence/recipe/task/title/`file`/`line`/`likely_cause`/evidence),
    and a `truncated` block.
  - DoD: **SPEC-005 T2** — JSON validates and includes a `truncated` block when
    trimming occurred; byte-stable across runs.

- [x] **M3-05 — Privacy: exclude config + redact host identity from evidence**
  - Spec: SPEC-005 §4 (**update first**: the reporter does NOT anonymize
    everything — `do_fetch` env dumps and dependency build roots leak host
    identity, per data-format.md; §4's "already scrubbed by the reporter"
    assumption is wrong).
  - Exclude `local_conf`/`auto_conf` by default; redact host-identity **structure**
    from evidence (the `SSH_AUTH_SOCK` value; `/<seg>/<seg>/<YYYY-MM-DD>/…` build
    roots) reusing the fixture scrubber's approach.
  - DoD: **SPEC-005 T3** — no `local_conf`/`auto_conf` content without
    `--include-config`; and no host-identity structure appears in a summary of the
    `dependency_moveit`/`fetch_dartsim` samples.

- [x] **M3-06 — `--include-config` opt-in + secret redaction**
  - Spec: SPEC-005 §4.
  - `--include-config` includes config but still redacts secrets
    (`password`/`token`/`key`/`secret`, `*_password`/`allow-empty-password`).
    Add a small **synthetic** fixture carrying a fake `*_password` line (per the
    M0-06 README note) — never un-scrub a real report.
  - DoD: **SPEC-005 T4** — with `--include-config`, a `password`-bearing line is
    redacted in the output.

- [ ] **M3-07 — `yer summarize` CLI subcommand**
  - Spec: SPEC-003 §1 (`summarize`); SPEC-005.
  - `cli.py` `summarize` subcommand: input resolution (SPEC-001),
    `--format {md,json}` (default `md`), `--budget <tokens>`, `--include-config`,
    `-o/--output`. No network calls.
  - DoD: `yer summarize <fixture> --format json` validates; `--format md` emits
    Markdown; exit-code contract consistent with `analyze`.

- [ ] **M3-08 — Budget verification + documented round-trip smoke**
  - Spec: SPEC-005 T1, T6; roadmap M3 exit criteria.
  - A `slow`/corpus test asserting the 2.1 MB report summary is under budget; a
    **documented** manual round-trip (`yer summarize <sample> | claude -p
    "diagnose"`) — not run in CI (no network in core/tests).
  - DoD: **SPEC-005 T1** verified on the 2.1 MB report; **T6** round-trip recipe
    documented (README/quickstart) with ≥3 category samples to try.

---

### Next milestone
Create `tasks/milestone-4.md` from SPEC-004 (static report) acceptance tests when
M3 exits (summary under budget for the 2 MB report; privacy redaction verified).
