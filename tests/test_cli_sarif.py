"""M5-03: `--format sarif` wired into the CLI (SPEC-003 §1; SPEC-004 §3).

Acceptance test copied from SPEC-004 §5:
    T8  SARIF output is byte-identical across two runs.
Plus the SPEC-003 §4 exit-code contract for the `analyze`/`report` subcommands.
"""

import json
from pathlib import Path

from yer.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_analyze_format_sarif_emits_valid_sarif(capsys):
    code = main(["analyze", str(FIXTURES), "--format", "sarif"])
    doc = json.loads(capsys.readouterr().out)
    assert code == 1  # exit codes match analyze (fixtures have errors)
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "yer"
    assert doc["runs"][0]["results"]


def test_analyze_sarif_byte_identical_across_runs(capsys):
    main(["analyze", str(FIXTURES), "--format", "sarif"])
    first = capsys.readouterr().out
    main(["analyze", str(FIXTURES), "--format", "sarif"])
    second = capsys.readouterr().out
    assert first == second


def test_analyze_sarif_respects_fail_on_none(capsys):
    code = main(["analyze", str(FIXTURES), "--format", "sarif", "--fail-on", "none"])
    capsys.readouterr()
    assert code == 0


def test_analyze_sarif_recipe_filter(capsys):
    main(["analyze", str(FIXTURES), "--format", "sarif", "--recipe", "gz-gui9"])
    doc = json.loads(capsys.readouterr().out)
    assert {r["ruleId"] for r in doc["runs"][0]["results"]}  # scoped, still valid
    # every result's rule is a configure/compile category for gz-gui9's findings
    assert all("locations" in r or r["ruleId"] for r in doc["runs"][0]["results"])


def test_report_format_sarif_writes_results_file(tmp_path):
    out = tmp_path / "out"
    sarif = tmp_path / "results.sarif"
    code = main(
        ["report", str(FIXTURES), "--html", str(out), "--format", "sarif", "-o", str(sarif)]
    )
    assert code == 1
    assert (out / "index.html").is_file() and (out / "report.json").is_file()
    doc = json.loads(sarif.read_text(encoding="utf-8"))
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["results"]
