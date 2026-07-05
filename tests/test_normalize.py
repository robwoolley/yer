"""M1-06: the shared `normalize()` helper (SPEC-001 §2).

Maps volatile tokens (run-script PIDs, line/column numbers, hex addresses) to
stable placeholders so the same failure yields the same SPEC-002 `signature`
across builds. Conservative in v1 (SPEC-002 §4 / OQ1): discriminating path text
is preserved so distinct recipes do not falsely merge.
"""

from pathlib import Path

from yer import ingest, parse

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_run_script_pid_normalized():
    out = parse.normalize("run.do_compile.2609824, line 153")
    assert "run.do_compile.<PID>" in out
    assert "2609824" not in out


def test_topdir_path_and_line_normalized():
    line = "TOPDIR/tmp/work/cortexa76/foo/1.0/src/bar.cpp:601:12: error: bad"
    out = parse.normalize(line)
    assert "bar.cpp:<N>" in out       # line (and column) collapsed
    assert "601" not in out and ":12" not in out
    assert "bar.cpp" in out           # discriminating filename kept


def test_backtrace_line_word_normalized():
    assert parse.normalize("do_configure, ..., line 132") == "do_configure, ..., line <N>"


def test_hex_address_normalized():
    assert parse.normalize("segfault at 0x7ffde3a1b2c0 in foo") == (
        "segfault at 0x<HEX> in foo"
    )


def test_idempotent():
    s = "run.do_configure.642082 at TOPDIR/a/b.c:99:3 addr 0xDEAD, line 12"
    once = parse.normalize(s)
    assert parse.normalize(once) == once


def test_same_failure_different_pid_merges_distinct_recipe_stays_split():
    a = parse.normalize("run.do_configure.642082, line 153")
    b = parse.normalize("run.do_configure.999999, line 153")
    assert a == b  # only the PID differed -> identical normalized form
    # distinct recipes keep distinct paths -> distinct normalized forms
    gz = parse.normalize("TOPDIR/work/gz-gui9/1.0/src/x.cpp:10: error")
    og = parse.normalize("TOPDIR/work/ogre-next/3.0/src/x.cpp:10: error")
    assert gz != og


def test_normalizes_a_real_backtrace_line():
    build = ingest.load_report(FIXTURES / "configure_gz-gui9.json")
    frames = parse.extract_backtrace(parse.parse_log(build.failures[0].log))
    raw = f"#{frames[0].index}: {frames[0].func}, {frames[0].path}, line {frames[0].line}"
    out = parse.normalize(raw)
    assert "run.do_configure.<PID>" in out
    assert "line <N>" in out
    assert str(frames[0].line) not in out
