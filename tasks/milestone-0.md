# Milestone 0 — Foundation

**Goal:** repo scaffolding, package skeleton, data model, test/CI harness, and a
fixture corpus extracted from `error-reports/`. Exit criteria: `yer --version`
runs, CI is green, ≥6 category fixtures exist.

Roadmap: [../docs/roadmap.md](../docs/roadmap.md) · DoD conventions:
[../CLAUDE.md](../CLAUDE.md)

Task id format `M0-nn`. Each task cites its spec and a definition of done (DoD).

---

- [x] **M0-01 — Package skeleton & `pyproject.toml`**
  - Spec: SPEC-000 §6 (NFR1), architecture §"Package layout".
  - Create `yocto_error_reports/` package, `pyproject.toml` with
    `console_scripts: yer = yocto_error_reports.cli:main`, Python `>=3.11`.
  - DoD: `pipx install .` then `yer --version` prints a version.

- [x] **M0-02 — Data model (`models.py`)**
  - Spec: architecture §"The data model"; SPEC-001/002 field lists.
  - Dataclasses: `Build`, `Failure`, `LogLine`, `Finding`, `Summary`, `Report`.
  - DoD: importable, typed, `mypy` clean; no logic.

- [x] **M0-03 — Test + lint + type harness**
  - Spec: CLAUDE.md conventions.
  - Add `pytest`, `ruff`, `mypy` config; a trivial smoke test.
  - DoD: `pytest`, `ruff check`, `mypy` all pass locally.

- [x] **M0-04 — CI workflow**
  - Spec: roadmap M0 exit criteria.
  - GitHub Actions: matrix on 3.11/3.12, run lint + type + tests.
  - DoD: CI green on a trivial PR.

- [x] **M0-05 — License & project metadata**
  - Spec: SPEC-000 §9 OQ3; README "License TBD".
  - Decide a license (recommend MIT or Apache-2.0), add `LICENSE`, fill
    `pyproject` metadata.
  - DoD: `LICENSE` present; README license section updated.

- [x] **M0-06 — Fixture pipeline**
  - Spec: SPEC-001/002 acceptance tests; CLAUDE.md "ground truth".
  - Select ≥6 reports from `error-reports/` (one per category: compile,
    configure, patch, qa, fetch, dependency) → `tests/fixtures/`, **anonymized**
    (scrub `local_conf`/`auto_conf`, any host paths not already `TOPDIR`).
  - Add a small script/README documenting how fixtures were derived.
  - DoD: fixtures load as JSON; a test enumerates them; no secrets present.

- [ ] **M0-07 — Corpus smoke harness**
  - Spec: SPEC-001 T1 (never crash on the corpus).
  - A test (marked slow/optional) that loads every file in `error-reports/` and
    asserts no exception once ingest exists (stub-tolerant until M1).
  - DoD: harness present; wired to run in M1.

---

### Next milestone
Create `tasks/milestone-1.md` from SPEC-001 acceptance tests when M0 exits.
