# Releasing `yer`

The maintainer runbook for publishing `yer` to PyPI. The design lives in
[SPEC-007](specs/SPEC-007-release.md); this page is the how-to.

## How releases work (in one paragraph)

Publishing is triggered **only by pushing a version tag** (`vX.Y.Z`). Ordinary
pushes and PRs run `ci.yml` (lint/type/test); a tag runs
[`release.yml`](../.github/workflows/release.yml), which guards on version
consistency, builds the sdist + wheel once, and uploads them to PyPI using
**Trusted Publishing (OIDC)** — so **no PyPI API token is ever stored** in the
repo or in GitHub secrets. A `vX.Y.Zrc*` tag publishes to **TestPyPI** (dry run);
a final `vX.Y.Z` tag publishes to **PyPI** and creates a GitHub Release whose body
is that version's CHANGELOG section.

## One-time setup (per index)

Done once by a maintainer; there are **no credentials to store in GitHub**.

1. **Register a Trusted Publisher** on the index (logged into your maintainer
   account):
   - PyPI: <https://pypi.org/manage/account/publishing/>
   - TestPyPI: <https://test.pypi.org/manage/account/publishing/>

   Because `yer` may not exist on the index yet, use the **pending publisher**
   flow (register before the first upload — the first successful run creates the
   project). Point the publisher at:
   - **PyPI Project Name:** `yer`
   - **Owner / Repository:** `robwoolley` / `yer`
   - **Workflow filename:** `release.yml`
   - **Environment:** `pypi` (PyPI) / `testpypi` (TestPyPI)

2. **Create the GitHub environments** (repo → Settings → Environments): `pypi`
   and, if you use the dry run, `testpypi`. Optionally add **required reviewers**
   so a release must be approved before it publishes.

That's it — at release time GitHub mints a short-lived OIDC token that PyPI
verifies against this publisher. Nothing long-lived exists to leak.

## Cutting a release

1. **Start from green `main`.** Ensure CI is passing on the commit you'll tag.

2. **Bump the version and roll the CHANGELOG** (they must move together — the
   release is guarded on it):
   - set `__version__` in [`yer/__init__.py`](../yer/__init__.py) to `X.Y.Z`;
   - in [`CHANGELOG.md`](../CHANGELOG.md), move the `[Unreleased]` entries into a
     new `## [X.Y.Z] — <release date>` section (keep an empty `[Unreleased]`),
     and update the compare/tag links at the bottom.

3. **Verify locally** (the same checks the workflow runs):

   ```bash
   python scripts/release_consistency.py "vX.Y.Z"   # tag == __version__ == CHANGELOG
   python -m build && twine check dist/*            # or: pytest -m slow (runs T1-T3, T5, T6)
   ```

4. **Commit and push** the bump (DCO signoff:
   `Signed-off-by: Rob Woolley <rob.woolley@windriver.com>`), then wait for CI to
   go green.

5. **(Optional) Test against TestPyPI.** Two ways, both requiring the one-time
   TestPyPI setup (a Trusted Publisher on test.pypi.org + a `testpypi` GitHub
   environment):

   - **Bump-free smoke (easiest).** In GitHub → **Actions → Release → Run
     workflow**, trigger it manually (`workflow_dispatch`). It builds the current
     tree and uploads to TestPyPI (`skip-existing`) — **no tag, no version bump**,
     and it never touches PyPI. Use this to verify the publish pipeline + OIDC +
     your TestPyPI setup.

   - **Real pre-release.** For a genuine `rc` on TestPyPI, first bump
     `__version__` **and** the CHANGELOG to the rc version (e.g. `0.1.0rc1`) so
     the consistency guard passes, then tag it:

     ```bash
     git tag -a vX.Y.Zrc1 -m "yer X.Y.Z rc1" && git push origin vX.Y.Zrc1
     ```

   Then confirm the upload at `https://test.pypi.org/project/yer/` and try an
   install:

   ```bash
   pipx run --index-url https://test.pypi.org/simple/ \
     --pip-args '--extra-index-url https://pypi.org/simple/' yer --version
   ```

6. **Publish.** Tag the final version and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "yer X.Y.Z" && git push origin vX.Y.Z
   ```

   The **Release** workflow builds, publishes to PyPI via OIDC, and creates the
   GitHub Release. Verify at `https://pypi.org/project/yer/` and that
   `pipx install yer` works.

> Pushing `vX.Y.Z` **is** the release — it publishes to the real index. Do it
> only when you mean it.

## Troubleshooting

- **Guard fails (`release-consistency: ...`).** The tag, `__version__`, and the
  newest dated CHANGELOG version disagree. Fix the mismatch, delete the bad tag
  (`git push --delete origin vX.Y.Z`), and re-tag.
- **"File already exists" on PyPI.** That version was already published; PyPI
  releases are immutable. Bump to a new version — the workflow deliberately does
  **not** use `skip-existing` on the real index.
- **OIDC / environment errors.** Confirm the Trusted Publisher's owner, repo,
  workflow filename (`release.yml`), and environment name match exactly, and that
  the GitHub environment exists (and its reviewers approved the run).
