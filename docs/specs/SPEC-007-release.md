# SPEC-007 — Release & Distribution (PyPI)

- **Status:** Approved (2026-07-05)
- **Depends on:** [SPEC-000](SPEC-000-overview.md) (NFR1 packaging / `yer` console
  script), [SPEC-003](SPEC-003-cli.md) (the CLI surface being shipped)
- **Artifacts:** `pyproject.toml` (metadata), `.github/workflows/release.yml`,
  `docs/releasing.md`, `CHANGELOG.md` (process), `tests/test_release_meta.py`

## Scope

`yer` is feature-complete (M0–M6) but unreleased: it is not on PyPI, there is no
`v0.1.0` tag (the CHANGELOG already links one that does not exist), and there is
no repeatable release process. This milestone makes `yer` **installable by its
users** — `pipx install yer` — with a tagged, reproducible, supply-chain-clean
release flow.

Non-goals (v1): conda/distro packaging, signed OS packages, a hosted service.
A reusable composite GitHub Action for consumers is a **fast-follow** (§6), not a
blocker for the first release.

## 1. Versioning & single source of truth

- **SemVer**, as the CHANGELOG already declares. `0.y.z` while pre-1.0: minor may
  break.
- The version lives in **one place** — `yer/__init__.__version__`
  (hatch `dynamic = ["version"]` already reads it). Nothing else hard-codes it.
- A release bumps that string, moves the CHANGELOG `[Unreleased]` block to a new
  `[X.Y.Z] — <date>` section, and tags `vX.Y.Z`. The tag is the trigger; the
  working tree is never mutated by CI.

## 2. Package metadata (PyPI-ready)

- **Distribution name is `yer`** — matching the import package (`yer/`) and the
  console script, so `pip install yer` and `import yer` agree. (`pyproject.toml`
  `name = "yer"`.)
- `readme = "README.md"` renders as the PyPI long description; it MUST render
  cleanly (no broken relative image/links that assume the repo tree).
- `project.urls` carries **Homepage**, **Repository**, **Changelog**, and
  **Issues** so the PyPI sidebar is complete.
- `classifiers` reflect reality: bump **Development Status** from
  `2 - Pre-Alpha` to the release-appropriate trove (e.g. `3 - Alpha` at 0.1.0),
  keep the Python-version and topic classifiers accurate.
- License is the modern SPDX expression already in use (`license = "MIT"` +
  `license-files`).
- The distribution ships everything the tool needs at runtime and **nothing it
  must not**: the Jinja2 template (`render/templates/*.j2`) is included; the
  gitignored `error-reports/` corpus and any `.yer/` trend store are **excluded**
  from both sdist and wheel.

## 3. Build & integrity

- Build with the PyPA toolchain: `python -m build` → an **sdist** and a
  **wheel**. `twine check` (metadata + long-description) MUST pass.
- The wheel is the installable artifact; the sdist is the buildable source of
  record. Both are built **once** in a dedicated CI job and reused for publish
  (never rebuilt per target).
- Optional but recommended: attach build provenance (GitHub artifact
  attestations / PEP 740) so consumers can verify origin.

## 4. Publishing (Trusted Publishing, no stored secrets)

Publishing is handled by `.github/workflows/release.yml`. It uses **PyPI Trusted
Publishing (OIDC)** via `pypa/gh-action-pypi-publish` — **no API token is stored
in the repo or org secrets** (matches the project's no-secrets posture).

### When it publishes

- **PyPI: only on a version tag.** A final `vX.Y.Z` tag push is the *only* thing
  that publishes to the real index. Ordinary pushes and pull requests never
  publish — they run `ci.yml` (lint/type/test) instead. A maintainer starts a
  release by pushing an **annotated, DCO-signed tag** `vX.Y.Z` (see
  `docs/releasing.md`); CI never mutates the working tree or creates tags itself.
- **TestPyPI via a pre-release tag.** A `vX.Y.Zrc*` tag publishes to **TestPyPI**
  (a real PEP 440 pre-release: `__version__`/CHANGELOG must equal the rc version,
  so the consistency guard passes).
- **TestPyPI via manual dispatch (bump-free smoke).** The workflow also accepts
  `workflow_dispatch`: a maintainer can run it by hand to build the current tree
  and publish to **TestPyPI** (`skip-existing`) with no tag and no version bump —
  a pipeline/OIDC smoke test. A manual run **skips the consistency guard** (there
  is no release tag) and **never** runs the PyPI publish or GitHub Release jobs;
  those are restricted to tag pushes.

### How it publishes (step by step)

1. **Guard** — for **tag** triggers, the release-consistency check (§5) confirms
   the tag equals `__version__` and the newest dated CHANGELOG version; a mismatch
   fails the run before anything is published. A manual `workflow_dispatch` smoke
   skips this step (it has no release tag).
2. **Build once** — one job runs `python -m build` (sdist + wheel) and
   `twine check`, then uploads the `dist/` as a workflow artifact. This job has no
   elevated permissions.
3. **Publish** — a separate job downloads that artifact and calls
   `pypa/gh-action-pypi-publish`. It declares `permissions: id-token: write` and
   runs in a protected `environment: pypi`, so PyPI authenticates the workflow via
   short-lived OIDC — there is no long-lived token to leak. It is **idempotent**:
   republishing an existing version fails rather than overwriting (`skip-existing`
   is used only for the TestPyPI dry run, never for the real index).
4. **Release notes** — the workflow creates a **GitHub Release** for the tag whose
   body is that version's CHANGELOG section, and attaches the built sdist + wheel.

### Prerequisite (one-time, in `docs/releasing.md`)

The `yer` name is reserved on PyPI and TestPyPI, and each index has a **Trusted
Publisher** registered for this repository + the `release.yml` workflow +
environment. No secret is stored in GitHub for this to work.

## 5. Release consistency & provenance of notes

- A **release-consistency check** (a test) asserts the tag version,
  `__version__`, and the top non-`Unreleased` CHANGELOG version all agree — no
  tag ships without a matching, dated CHANGELOG entry.
- CI creates a **GitHub Release** from the tag whose body is that version's
  CHANGELOG section, and attaches the built sdist + wheel.
- Commits/tags follow the repo's DCO convention (Signed-off-by).

## 6. Fast-follow: reusable GitHub Action (adoption)

A composite action (`action.yml`) wrapping the `docs/ci.md` recipe
(`yer report` + `yer analyze --format sarif` + upload) so consumers write one
`uses:` line instead of hand-copying YAML. Documented, versioned to the release
tag. Deferred out of the first release but tracked here for continuity.

## 7. Determinism & privacy (cross-cutting)

- The published artifacts are byte-reproducible from a given tag (no wall-clock or
  environment leakage into the wheel beyond standard build metadata).
- **No host data ships:** an explicit check confirms neither sdist nor wheel
  contains `error-reports/`, a `.yer/` store, or `tests/fixtures/redactions.local`.

## 8. Acceptance tests

- **T1** `python -m build` produces an sdist and a wheel; the wheel contains
  `yer/render/templates/report.html.j2` and declares the `yer`
  console-script entry point.
- **T2** Installing the built **wheel** into a clean virtualenv exposes
  `yer --version` equal to `__version__`, and `yer analyze <fixture>` runs
  end-to-end (proves the template and entry point ship correctly).
- **T3** `twine check dist/*` passes (valid metadata; README renders as the long
  description).
- **T4** The release workflow triggers on a `v*` tag (and manual
  `workflow_dispatch`), builds once, and publishes via OIDC Trusted Publishing
  with no stored API token; publishing an already-existing version fails rather
  than overwriting. A manual `workflow_dispatch` run publishes **only** to
  TestPyPI — the PyPI publish and GitHub Release jobs are restricted to tag
  pushes.
- **T5** Release-consistency: the `v*` tag, `__version__`, and the newest dated
  CHANGELOG version are identical (the check fails the release otherwise).
- **T6** Neither the sdist nor the wheel contains any corpus report
  (`error_report_*.txt`), a `.yer/` trend store, or `redactions.local`.

## Changelog

- **2026-07-05 (TestPyPI smoke):** §4 — added a bump-free `workflow_dispatch`
  path that builds the current tree and publishes to TestPyPI (skip-existing),
  skipping the consistency guard and never running the PyPI/GitHub-Release jobs
  (those stay tag-only). Extended T4 to assert manual runs are TestPyPI-only.
  Rationale: let maintainers smoke-test the publish pipeline + OIDC + TestPyPI
  setup without minting a version.
- **2026-07-05 (ratified):** Status Draft → Approved. Scope accepted as written
  (distribution `yer`; tag-triggered PyPI publish via Trusted Publishing; the
  version/CHANGELOG consistency gate; no-host-data-ships check); M7 tasks may now
  be implemented.
- **2026-07-05 (rename + publish docs):** The distribution is named **`yer`**
  (not `yocto-error-reports`), matching the renamed import package `yer/` and the
  console script; §2 states this and all examples use `pipx install yer`.
  Expanded §4 with explicit **"when it publishes"** (only on a `v*` tag; `rc*` →
  TestPyPI, final → PyPI) and **"how it publishes"** (guard → build-once →
  OIDC publish → GitHub Release) documentation.
- **2026-07-04 (M7 authoring):** Initial draft. Centers the milestone on a
  tag-triggered PyPI release via Trusted Publishing (OIDC, no stored secrets),
  with build-once/publish, `twine check`, a tag/`__version__`/CHANGELOG
  consistency gate, a GitHub Release from the CHANGELOG section, and a
  no-host-data-ships check. Metadata polish (URLs, Development Status) and a
  reusable composite Action (fast-follow) round out adoption. Status stays
  **Draft** until ratified.
