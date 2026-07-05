# Milestone 7 — Release & Distribution (PyPI)

**Goal:** make `yer` installable by its users — `pipx install yer` — via a
tagged, reproducible, supply-chain-clean release.
Exit criteria: `python -m build` yields a valid sdist + wheel that install and
run from a clean environment; a `v*` tag publishes to PyPI via Trusted
Publishing (no stored secrets); the tag, `__version__`, and CHANGELOG agree; and
no host data (corpus / `.yer` store) ships in the artifacts.

Roadmap: [../docs/roadmap.md](../docs/roadmap.md) · Spec:
[SPEC-007](../docs/specs/SPEC-007-release.md) · DoD conventions:
[../CLAUDE.md](../CLAUDE.md)

Task id format `M7-nn`. Each task cites its spec section and a DoD tied to a
concrete SPEC-007 acceptance test. This milestone is repo/release infrastructure,
not a runtime code module — core `parse`/`analyze`/`models` are untouched.

---

- [x] **M7-01 — PyPI-ready metadata + a correct distribution**
  - Spec: SPEC-007 §2, §3, §7.
  - Complete `project.urls` (Homepage, Repository, Changelog, Issues), bump the
    `Development Status` classifier (`2 - Pre-Alpha` → release-appropriate), and
    confirm the built distribution ships the Jinja2 template while **excluding**
    `error-reports/`, any `.yer/` store, and `redactions.local`.
  - DoD: **SPEC-007 T1** (`python -m build` produces an sdist + wheel; the wheel
    contains `render/templates/report.html.j2` and declares the `yer` entry
    point) and **T6** (no `error_report_*.txt`, `.yer/`, or `redactions.local` in
    either artifact).

- [x] **M7-02 — Validate the distribution (`twine check` + clean install)**
  - Spec: SPEC-007 §3, §2.
  - Run `twine check dist/*` (metadata + README long-description) and smoke-test a
    clean-venv install of the wheel.
  - DoD: **SPEC-007 T3** (`twine check` passes; README renders) and **T2**
    (installing the wheel into a fresh virtualenv gives `yer --version ==
    __version__` and `yer analyze <fixture>` runs end-to-end).

- [x] **M7-03 — Release-consistency check**
  - Spec: SPEC-007 §1, §5.
  - A test asserting the release tag (when building from one), `__version__`, and
    the newest dated `CHANGELOG.md` version are identical — no release without a
    matching, dated changelog entry.
  - DoD: **SPEC-007 T5** — the check passes for a consistent version trio and
    fails when they diverge.

- [x] **M7-04 — Tag-triggered publish workflow (Trusted Publishing)**
  - Spec: SPEC-007 §4, §5.
  - `.github/workflows/release.yml`: on a `v*` tag, build once, publish via PyPI
    **Trusted Publishing (OIDC)** (`pypa/gh-action-pypi-publish`, no stored
    token), in a protected `environment: pypi` with `id-token: write`; refuse to
    overwrite an existing version; create a GitHub Release whose body is that
    version's CHANGELOG section and attach the dists.
  - DoD: **SPEC-007 T4** — a test parses `release.yml` and asserts the `v*`
    trigger, OIDC Trusted Publishing with no `password:`/token secret,
    `id-token: write`, the `pypi` environment, and build-once/publish structure.

- [x] **M7-05 — Cut v0.1.0 + document the release process**
  - Spec: SPEC-007 §1, §4, §5.
  - `docs/releasing.md`: the one-time PyPI/TestPyPI name reservation + Trusted
    Publisher registration, and the per-release steps (bump `__version__`, roll
    CHANGELOG `[Unreleased]` → `[X.Y.Z] — <date>`, tag `vX.Y.Z`, push). Ready the
    `0.1.0` changelog block for release.
  - DoD: `docs/releasing.md` present and complete; the release-consistency check
    (M7-03), `twine check`, and the clean-install smoke (M7-02) are all green —
    the repo is one `git tag v0.1.0` away from publishing.

- [ ] **M7-06 — (Fast-follow) reusable composite GitHub Action**
  - Spec: SPEC-007 §6.
  - `action.yml` wrapping the `docs/ci.md` recipe (`yer report` + `yer analyze
    --format sarif` + artifact/SARIF upload) so consumers write one `uses:` line;
    versioned to the release tag.
  - DoD: a test parses `action.yml` and asserts it references `yer report` +
    `yer analyze --format sarif` and the upload steps; documented in `docs/ci.md`.

---

### Next milestone
M7 is the current end of the roadmap. Further scope (SPEC-006/007 non-goals — a
hosted dashboard, cross-repo aggregation, distro packaging, a signed release
supply chain) needs a new **SPEC-008** authored first, then
`tasks/milestone-8.md`.
