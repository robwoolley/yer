"""M1-03: malformed input → parse-finding `Build`, never raise (SPEC-001 §1 / FR2).

Acceptance test copied from SPEC-001 §4:
    T2  A truncated/garbage file yields a parse-finding Build, not an exception.

Fixtures under tests/fixtures/malformed/ are **synthetic** (hand-written garbage,
never real reports).
"""

from pathlib import Path

import pytest

from yocto_error_reports import ingest
from yocto_error_reports.models import Build

MALFORMED = Path(__file__).resolve().parent / "fixtures" / "malformed"


@pytest.mark.parametrize(
    "name",
    ["truncated.txt", "not-json.txt", "json-array.txt"],
)
def test_t2_malformed_yields_parse_finding_build(name):
    build = ingest.load_report(MALFORMED / name)  # must not raise
    assert isinstance(build, Build)
    assert build.failures == []
    assert len(build.findings) == 1
    finding = build.findings[0]
    assert finding.category == "unknown"
    assert finding.severity == "error"
    assert finding.title  # a description of the parse problem
    assert build.source_path == str(MALFORMED / name)


def test_unreadable_path_does_not_raise():
    build = ingest.load_report(MALFORMED / "does-not-exist.txt")
    assert build.findings and build.findings[0].category == "unknown"


def test_directory_scan_skips_malformed_files():
    # Scanning the whole fixtures tree still yields only the 7 real reports;
    # the malformed/ files do not parse as reports and are silently skipped.
    builds = ingest.load_reports([MALFORMED.parent])
    assert len(builds) == 7
    assert all(b.findings == [] for b in builds)
