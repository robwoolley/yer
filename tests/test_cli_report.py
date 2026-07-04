"""M4-06: `yer report` CLI subcommand (SPEC-003 §1; SPEC-004).

Acceptance test copied from SPEC-004 §5:
    T1  `yer report <inputs> --html out/` writes `out/index.html` and
        `out/report.json`; exit codes match `analyze`.

Plus the SPEC-003 §4 exit-code contract and SPEC-004 §4 determinism as they
apply to this subcommand.
"""

from pathlib import Path

import pytest

from yocto_error_reports.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_t1_report_writes_html_and_json(tmp_path):
    out = tmp_path / "out"
    code = main(["report", str(FIXTURES), "--html", str(out)])
    assert code == 1  # fixtures contain errors -> same exit as `analyze`
    assert (out / "index.html").is_file()
    assert (out / "report.json").is_file()
    html = (out / "index.html").read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert '"schema_version": "1.0"' in (out / "report.json").read_text(encoding="utf-8")


def test_report_exit_codes_match_analyze(tmp_path):
    # `--fail-on none` -> exit 0, same as analyze
    code = main(["report", str(FIXTURES), "--html", str(tmp_path / "o"), "--fail-on", "none"])
    assert code == 0


def test_report_json_byte_identical_across_runs(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    main(["report", str(FIXTURES), "--html", str(a)])
    main(["report", str(FIXTURES), "--html", str(b)])
    assert (a / "report.json").read_bytes() == (b / "report.json").read_bytes()
    assert (a / "index.html").read_bytes() == (b / "index.html").read_bytes()


def test_report_requires_html_dir():
    # --html is required for this subcommand; argparse exits 2 without it
    with pytest.raises(SystemExit) as exc:
        main(["report", str(FIXTURES)])
    assert exc.value.code == 2


def test_report_no_matching_inputs_exits_2(tmp_path, capsys):
    code = main(["report", str(FIXTURES / "nope.txt"), "--html", str(tmp_path / "o")])
    assert code == 2
    assert capsys.readouterr().err  # message on stderr


def test_report_format_json_output_emits_canonical_json(tmp_path):
    out = tmp_path / "out"
    extra = tmp_path / "canonical.json"
    code = main(
        ["report", str(FIXTURES), "--html", str(out), "--format", "json", "-o", str(extra)]
    )
    assert code == 1
    assert extra.is_file()
    # the extra JSON matches the artifact JSON byte-for-byte
    assert extra.read_text(encoding="utf-8") == (out / "report.json").read_text(encoding="utf-8")


def test_report_recipe_filter_scopes_artifacts(tmp_path):
    out = tmp_path / "out"
    main(["report", str(FIXTURES), "--html", str(out), "--recipe", "gz-gui9", "--fail-on", "none"])
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "gz-gui9" in html
    assert "moveit-ros-planning-interface-dev" not in html  # other recipes filtered out
