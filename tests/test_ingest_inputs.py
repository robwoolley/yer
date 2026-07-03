"""M1-02: input resolution — paths, globs, directories, stdin (SPEC-001 §1).

DoD: a directory yields one Build per report (non-reports skipped); duplicate
paths are collapsed; ordering is deterministic; `-` reads one report from stdin.
"""

import io
from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.models import Build

FIXTURES = Path(__file__).resolve().parent / "fixtures"
N_REPORTS = 7  # *.json fixtures; README.md + derive_fixtures.py must be skipped


def test_directory_yields_one_build_per_report():
    builds = ingest.load_reports([FIXTURES])
    assert all(isinstance(b, Build) for b in builds)
    # exactly the 7 JSON reports; the .md and .py files do not parse as reports
    assert len(builds) == N_REPORTS
    assert [Path(b.source_path).name for b in builds] == sorted(
        p.name for p in FIXTURES.glob("*.json")
    )


def test_glob_pattern_matches_reports():
    builds = ingest.load_reports([str(FIXTURES / "*.json")])
    assert len(builds) == N_REPORTS


def test_duplicate_paths_deduped():
    one = FIXTURES / "configure_gz-gui9.json"
    assert len(ingest.load_reports([one, one])) == 1
    # a file already covered by a directory scan is not loaded twice
    assert len(ingest.load_reports([FIXTURES, one])) == N_REPORTS


def test_ordering_is_deterministic():
    a = [b.source_path for b in ingest.load_reports([FIXTURES])]
    b = [b.source_path for b in ingest.load_reports([FIXTURES])]
    assert a == b == sorted(a)


def test_stdin_reads_one_report(monkeypatch):
    text = (FIXTURES / "dependency_moveit.json").read_text(encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    builds = ingest.load_reports(["-"])
    assert len(builds) == 1
    assert builds[0].source_path == "-"
    assert builds[0].failures[0].kind == "message"
