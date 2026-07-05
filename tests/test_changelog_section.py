"""M7-04: CHANGELOG section extraction for release notes (SPEC-007 §5)."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "changelog_section.py"


def _load():
    spec = importlib.util.spec_from_file_location("changelog_section", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cs = _load()

_SAMPLE = (
    "# Changelog\n\n"
    "## [Unreleased]\n\n_Nothing yet._\n\n"
    "## [0.2.0] — 2026-08-01\n\n### Added\n\n- a new thing\n\n"
    "## [0.1.0] — 2026-07-04\n\n- first\n\n"
    "[Unreleased]: https://example/compare\n"
    "[0.2.0]: https://example/tag/v0.2.0\n"
)


def test_extracts_named_section_only():
    section = cs.changelog_section("0.2.0", _SAMPLE)
    assert section.startswith("## [0.2.0] — 2026-08-01")
    assert "a new thing" in section
    assert "0.1.0" not in section  # stops at the next version heading
    assert "https://example" not in section  # excludes link-reference defs


def test_strips_leading_v():
    assert cs.changelog_section("v0.2.0", _SAMPLE).startswith("## [0.2.0]")


def test_real_changelog_has_current_version(capsys):
    # the repo's actual current version resolves to a real section
    import importlib.util as _u

    rc_path = SCRIPT.parent / "release_consistency.py"
    spec = _u.spec_from_file_location("release_consistency", rc_path)
    rc = _u.module_from_spec(spec)
    spec.loader.exec_module(rc)

    version = rc.package_version()
    section = cs.changelog_section(version)
    assert section.startswith(f"## [{version}]")


def test_unknown_version_raises():
    import pytest

    with pytest.raises(ValueError):
        cs.changelog_section("9.9.9", _SAMPLE)
