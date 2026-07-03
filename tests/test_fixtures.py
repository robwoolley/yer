"""M0-06: the fixture corpus loads as JSON, covers every category, is scrubbed.

DoD: fixtures load as JSON; a test enumerates them; no secrets present.
Provenance and derivation: tests/fixtures/README.md + derive_fixtures.py.
"""

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURES = sorted(FIXTURE_DIR.glob("*.json"))

# The six failure categories from data-format.md, encoded in fixture filenames.
REQUIRED_CATEGORIES = ("compile", "configure", "patch", "qa", "fetch", "dependency")

# Real config that must never appear in a shareable fixture (data-format §Privacy).
SECRET_MARKERS = ("empty-root-password", "allow-empty-password", "allow-root-login")
SCRUB_PLACEHOLDER = "<scrubbed for fixture — see tests/fixtures/README.md>"


def test_at_least_six_fixtures():
    assert len(FIXTURES) >= 6, f"expected >=6 fixtures, found {len(FIXTURES)}"


def test_every_category_has_a_fixture():
    names = " ".join(p.name for p in FIXTURES)
    for category in REQUIRED_CATEGORIES:
        assert category in names, f"no fixture for category {category!r}"


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_fixture_loads_as_report_json(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert isinstance(data.get("failures"), list), "report must carry a failures list"


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_fixture_is_scrubbed(path):
    text = path.read_text(encoding="utf-8")
    for marker in SECRET_MARKERS:
        assert marker not in text, f"{path.name} still contains secret marker {marker!r}"
    data = json.loads(text)
    for key in ("local_conf", "auto_conf"):
        if key in data:
            assert data[key] == SCRUB_PLACEHOLDER, f"{path.name} {key} not scrubbed"
