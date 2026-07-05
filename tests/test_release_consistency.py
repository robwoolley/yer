"""M7-03: release-consistency check (SPEC-007 §5).

Acceptance test copied from SPEC-007 §8:
    T5  Release-consistency: the v* tag, __version__, and the newest dated
        CHANGELOG version are identical (the check fails the release otherwise).
"""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release_consistency.py"


def _load():
    spec = importlib.util.spec_from_file_location("release_consistency", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rc = _load()


def test_repo_version_matches_changelog():
    # the working tree's __version__ equals the newest dated CHANGELOG version
    assert rc.package_version() == rc.changelog_version()


def test_check_passes_for_consistent_trio():
    version = rc.package_version()
    assert rc.check(f"v{version}") == []  # v-prefixed tag
    assert rc.check(version) == []  # bare version also accepted


def test_check_fails_on_divergent_tag():
    assert rc.check("v9.9.9")  # non-empty -> mismatch reported


def test_check_fails_on_version_changelog_drift(monkeypatch):
    monkeypatch.setattr(rc, "package_version", lambda: "9.9.9")
    assert rc.check(None)  # __version__ != CHANGELOG -> mismatch reported


def test_main_exit_codes():
    version = rc.package_version()
    assert rc.main([f"v{version}"]) == 0
    assert rc.main(["v9.9.9"]) == 1


def test_changelog_version_parses_newest_dated_skipping_unreleased():
    text = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n_Nothing yet._\n\n"
        "## [0.2.0] — 2026-08-01\n\n### Added\n\n"
        "## [0.1.0] — 2026-07-04\n"
    )
    assert rc.changelog_version(text) == "0.2.0"
