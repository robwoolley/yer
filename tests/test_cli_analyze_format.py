"""M2-10: analyze --format json, filters, --no-color (SPEC-003 §1, §3, §5).

Acceptance tests copied from SPEC-003 §5:
    T3  --format json validates and is byte-stable across runs.
    T5  --no-color / NO_COLOR produces plain ASCII.
    T6  --recipe gz-gui9 filters to that recipe only.
"""

import json
from pathlib import Path

from yer.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_t3_json_is_byte_stable_and_structured(capsys):
    assert main(["analyze", str(FIXTURES), "--format", "json"]) == 1
    first = capsys.readouterr().out
    assert main(["analyze", str(FIXTURES), "--format", "json"]) == 1
    second = capsys.readouterr().out
    assert first == second  # byte-stable

    data = json.loads(first)
    assert data["schema_version"] == "1.0"
    assert data["findings"]
    finding = data["findings"][0]
    for key in ("category", "severity", "title", "signature", "occurrences", "affected_recipes"):
        assert key in finding
    assert data["summary"]["errors"] >= 1


def test_t5_no_color_is_plain_ascii(capsys):
    main(["analyze", str(FIXTURES), "--no-color"])
    out = capsys.readouterr().out
    assert out.isascii()
    assert "\033[" not in out  # no ANSI escapes


def test_t6_recipe_filter(capsys):
    code = main(["analyze", str(FIXTURES), "--recipe", "gz-gui9", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["findings"]
    assert {f["recipe"] for f in data["findings"]} == {"gz-gui9"}
    assert code == 1


def test_category_filter(capsys):
    main(["analyze", str(FIXTURES), "--category", "fetch", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["findings"]
    assert all(f["category"] == "fetch" for f in data["findings"])


def test_max_evidence_truncates(capsys):
    main(["analyze", str(FIXTURES), "--max-evidence", "1", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert all(len(f["evidence"]) <= 1 for f in data["findings"])
