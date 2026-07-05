"""M7-04: tag-triggered publish workflow (SPEC-007 §4, §5).

Acceptance test copied from SPEC-007 §8:
    T4  The release workflow triggers only on a `v*` tag, builds once, and
        publishes via OIDC Trusted Publishing with no stored API token;
        publishing an already-existing version fails rather than overwriting.

Verified structurally by parsing `.github/workflows/release.yml` (the live
publish is validated by pushing a real tag).
"""

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml"


def _doc():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_exists():
    assert WORKFLOW.is_file(), "expected .github/workflows/release.yml"


def test_triggers_on_version_tag_and_manual_dispatch():
    doc = _doc()
    # YAML 1.1 parses the `on:` key as the boolean True; accept either form.
    triggers = doc.get(True, doc.get("on"))
    assert triggers["push"] == {"tags": ["v*"]}  # tag push, no branches
    assert "workflow_dispatch" in triggers  # manual TestPyPI smoke


def test_manual_dispatch_publishes_only_to_testpypi():
    jobs = _doc()["jobs"]
    testpypi_if = jobs["publish-testpypi"]["if"]
    pypi_if = jobs["publish-pypi"]["if"]
    # TestPyPI runs on a manual dispatch (or an rc tag)
    assert "workflow_dispatch" in testpypi_if
    # PyPI is restricted to tag pushes -> a manual run can never publish to PyPI
    assert "tag" in pypi_if
    assert "workflow_dispatch" not in pypi_if


def test_guard_runs_only_for_tag_releases():
    build_steps = _doc()["jobs"]["build"]["steps"]
    guard = next(s for s in build_steps if "release_consistency.py" in (s.get("run") or ""))
    assert "tag" in (guard.get("if") or "")  # skipped on a bump-free manual run


def test_builds_once_then_publishes_from_the_artifact():
    text = WORKFLOW.read_text(encoding="utf-8")
    jobs = _doc()["jobs"]
    assert "build" in jobs
    # build guards on version consistency, builds, and uploads the dist artifact
    assert "release_consistency.py" in text  # the M7-03 guard runs first
    assert "python -m build" in text
    assert "actions/upload-artifact" in text
    # the publish job consumes that artifact (build-once / publish)
    assert "actions/download-artifact" in text


def test_pypi_publish_uses_oidc_trusted_publishing():
    jobs = _doc()["jobs"]
    publish = jobs["publish-pypi"]
    assert publish["environment"] == "pypi"  # protected environment
    assert publish["permissions"]["id-token"] == "write"  # OIDC
    steps = publish["steps"]
    assert any("pypa/gh-action-pypi-publish" in (s.get("uses") or "") for s in steps)


def test_no_stored_pypi_token():
    text = WORKFLOW.read_text(encoding="utf-8").lower()
    assert "password:" not in text  # no username/password auth
    assert "secrets.pypi" not in text  # no stored PyPI secret
    assert "pypi_api_token" not in text
    assert "api-token" not in text and "api_token" not in text


def test_final_tag_publish_is_not_skip_existing():
    # republishing an existing version must fail, not silently skip
    publish = _doc()["jobs"]["publish-pypi"]
    publish_step = next(
        s for s in publish["steps"] if "pypa/gh-action-pypi-publish" in (s.get("uses") or "")
    )
    with_ = publish_step.get("with") or {}
    assert not with_.get("skip-existing", False)


def test_creates_github_release_from_changelog():
    text = WORKFLOW.read_text(encoding="utf-8")
    jobs = _doc()["jobs"]
    assert "github-release" in jobs
    assert "changelog_section.py" in text  # release body is the CHANGELOG section
    assert "gh release create" in text
    assert jobs["github-release"]["permissions"]["contents"] == "write"
