"""Guard for M0-05: MIT license present and declared consistently.

DoD: LICENSE file present; README license section updated; pyproject metadata
filled. This pins those so the license can't silently drift.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_license_file_is_mit():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Rob Woolley" in text


def test_pyproject_declares_mit():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["license"] == "MIT"


def test_readme_license_section_updated():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "MIT" in text
    assert "TBD" not in text  # the placeholder is gone
