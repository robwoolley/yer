"""M1-05: extract the BB backtrace block into structured frames (SPEC-001 §2).

Acceptance test copied from SPEC-001 §4:
    T6  Backtrace frames extracted from the gz-gui9 do_configure sample.
"""

from pathlib import Path

from yocto_error_reports import ingest, parse

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_no_backtrace_returns_empty():
    lines = parse.parse_log("ERROR: something failed\nNOTE: done")
    assert parse.extract_backtrace(lines) == []


def test_frames_parsed_from_real_format():
    log = (
        "WARNING: Backtrace (BB generated script): \n"
        "\t#1: cmake_do_configure, TOPDIR/.../temp/run.do_configure.642082, line 153\n"
        "\t#2: do_configure, TOPDIR/.../temp/run.do_configure.642082, line 132\n"
        "NOTE: after the block\n"
    )
    frames = parse.extract_backtrace(parse.parse_log(log))
    assert [(f.index, f.func, f.line) for f in frames] == [
        (1, "cmake_do_configure", 153),
        (2, "do_configure", 132),
    ]
    assert frames[0].path.endswith("run.do_configure.642082")


def test_t6_backtrace_frames_from_configure_sample():
    build = ingest.load_report(FIXTURES / "configure_gz-gui9.json")
    frames = parse.extract_backtrace(parse.parse_log(build.failures[0].log))
    assert [f.func for f in frames] == ["cmake_do_configure", "do_configure", "main"]
    assert frames[0].index == 1
    assert frames[0].func == "cmake_do_configure"
    assert frames[0].line == 153
    assert "run.do_configure.642082" in frames[0].path
    # the analyzer uses the do_configure frame to confirm the failing task
    assert any(f.func == "do_configure" for f in frames)
