"""M1-04: parse a raw `log` into `LogLine[]` (SPEC-001 §2, §3).

Acceptance test copied from SPEC-001 §4:
    T5  Level prefixes correctly split on the do_package_qa sample
        (`ERROR: QA Issue:` -> level `ERROR`, text `QA Issue:…`).
"""

import time
from pathlib import Path

from yocto_error_reports import ingest, parse
from yocto_error_reports.models import LogLine

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_empty_log_is_no_lines():
    assert parse.parse_log("") == []


def test_level_tokens_split_and_numbered():
    log = "ERROR: boom\nWARNING: careful\nNOTE: fyi\nDEBUG: trace\nplain line"
    lines = parse.parse_log(log)
    assert [(x.n, x.level, x.text) for x in lines] == [
        (1, "ERROR", "boom"),
        (2, "WARNING", "careful"),
        (3, "NOTE", "fyi"),
        (4, "DEBUG", "trace"),
        (5, None, "plain line"),
    ]
    assert all(isinstance(x, LogLine) for x in lines)


def test_indentation_preserved_and_not_a_level():
    # sub-tool indentation is meaningful — keep it; an indented "error:" is not
    # a bitbake level token (those are anchored at column 0).
    lines = parse.parse_log("    error: undefined reference\n\tmore")
    assert lines[0].level is None
    assert lines[0].text == "    error: undefined reference"
    assert lines[1].text == "\tmore"


def test_crlf_trailing_carriage_return_stripped():
    lines = parse.parse_log("ERROR: boom\r\nplain\r\n")
    assert [(x.level, x.text) for x in lines] == [("ERROR", "boom"), (None, "plain")]


def test_only_one_space_after_colon_consumed():
    lines = parse.parse_log("ERROR:   three spaces")
    assert lines[0].level == "ERROR"
    assert lines[0].text == "  three spaces"  # one space eaten, two kept


def test_t5_level_prefix_split_on_qa_sample():
    build = ingest.load_report(FIXTURES / "qa_gz-physics-vendor.json")
    lines = parse.parse_log(build.failures[0].log)
    qa = [x for x in lines if x.level == "ERROR" and x.text.startswith("QA Issue:")]
    assert qa, "expected 'ERROR: QA Issue:' split into level=ERROR, text='QA Issue:…'"
    assert qa[0].level == "ERROR"
    assert qa[0].text.startswith("QA Issue:")


def test_large_log_streams_within_budget():
    # the 560 KB / 2240-line ogre-next compile log (committed fixture)
    build = ingest.load_report(FIXTURES / "fetch_dartsim.json")
    big = max((f.log for f in build.failures), key=len)
    start = time.perf_counter()
    lines = parse.parse_log(big)
    elapsed = time.perf_counter() - start
    # a final newline does not create a spurious trailing empty line
    expected = big.count("\n") + (0 if big.endswith("\n") else 1)
    assert len(lines) == expected
    assert [x.n for x in lines] == list(range(1, expected + 1))  # 1-based, contiguous
    assert elapsed < 1.0, f"parsing {len(big)} bytes took {elapsed:.3f}s"
