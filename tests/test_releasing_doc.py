"""M7-05: the release runbook exists and covers the essentials (SPEC-007 §1/§4/§5).

Binds docs/releasing.md to the operational steps a maintainer needs: the tag
trigger, the OIDC no-token model, the pypi environment, the version/CHANGELOG
bump, the consistency guard, and the TestPyPI dry run.
"""

from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "releasing.md"


def test_runbook_exists():
    assert DOC.is_file(), "expected docs/releasing.md"


def test_runbook_covers_the_essentials():
    text = DOC.read_text(encoding="utf-8")
    lowered = text.lower()
    # what triggers a publish
    assert "git tag" in lowered
    assert "v*" in text or "vX.Y.Z" in text
    # the no-secrets OIDC model + protected environment
    assert "trusted publish" in lowered
    assert "environment" in lowered and "pypi" in lowered
    # per-release mechanics
    assert "__version__" in text
    assert "changelog" in lowered
    assert "release_consistency" in text
    # the dry-run gate
    assert "testpypi" in lowered or "test.pypi.org" in lowered


def test_runbook_does_not_instruct_storing_a_token():
    # the whole point of Trusted Publishing: no long-lived PyPI secret
    lowered = DOC.read_text(encoding="utf-8").lower()
    assert "pypi_api_token" not in lowered
    assert "secrets.pypi" not in lowered
