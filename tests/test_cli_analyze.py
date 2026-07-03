"""M2-09: `yer analyze` text output, input resolution, exit codes (SPEC-003).

Acceptance tests copied from SPEC-003 §5:
    T1  `yer analyze <corpus>` exits 1 (has errors), prints ranked findings.
    T2  `--fail-on none` on the same input exits 0.
    T4  No inputs / bad path -> exit 2, message on stderr.
"""

from pathlib import Path

import pytest

from yocto_error_reports.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_t1_analyze_exits_1_and_prints_findings(capsys):
    code = main(["analyze", str(FIXTURES)])
    out = capsys.readouterr().out
    assert code == 1  # fixtures contain errors
    assert "configure" in out and "compile" in out  # ranked findings rendered
    assert "exit 1" in out  # footer


def test_t2_fail_on_none_exits_0(capsys):
    code = main(["analyze", str(FIXTURES), "--fail-on", "none"])
    assert code == 0
    assert "exit 0" in capsys.readouterr().out


def test_t4_bad_path_exits_2_with_stderr(capsys):
    code = main(["analyze", str(FIXTURES / "does-not-exist.txt")])
    assert code == 2
    assert capsys.readouterr().err  # a message on stderr


def test_t4_no_inputs_exits_2():
    # argparse enforces nargs="+", exiting 2 on missing inputs
    with pytest.raises(SystemExit) as exc:
        main(["analyze"])
    assert exc.value.code == 2


def test_output_to_file(tmp_path, capsys):
    out_file = tmp_path / "report.txt"
    code = main(["analyze", str(FIXTURES), "-o", str(out_file)])
    assert code == 1
    assert "exit 1" in out_file.read_text(encoding="utf-8")
