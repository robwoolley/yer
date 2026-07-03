"""M3-07: `yer summarize` CLI subcommand (SPEC-003 §1; SPEC-005).

DoD: `yer summarize <fixture> --format json` validates; `--format md` emits
Markdown; exit-code contract consistent with analyze (2 on tool/usage error).
"""

import json
from pathlib import Path

import pytest

from yocto_error_reports.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONFIGURE = FIXTURES / "configure_gz-gui9.json"


def test_summarize_markdown_default(capsys):
    assert main(["summarize", str(CONFIGURE)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Yocto build failure — gz-gui9 (do_configure)")


def test_summarize_json_validates(capsys):
    assert main(["summarize", str(CONFIGURE), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["findings"]
    assert data["findings"][0]["category"] == "configure"
    assert "truncated" in data


def test_summarize_budget_bounds_output(capsys):
    main(["summarize", str(FIXTURES), "--format", "json", "--budget", "60"])
    data = json.loads(capsys.readouterr().out)
    assert data["findings"]  # at least the root cause survives a tiny budget


def test_summarize_no_inputs_exits_2():
    with pytest.raises(SystemExit) as exc:
        main(["summarize"])
    assert exc.value.code == 2


def test_summarize_bad_path_exits_2(capsys):
    assert main(["summarize", str(FIXTURES / "does-not-exist.txt")]) == 2
    assert capsys.readouterr().err


def test_summarize_output_to_file(tmp_path):
    out_file = tmp_path / "summary.md"
    assert main(["summarize", str(CONFIGURE), "-o", str(out_file)]) == 0
    assert out_file.read_text(encoding="utf-8").startswith("# Yocto build failure")
