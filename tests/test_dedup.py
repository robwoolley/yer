"""M2-07: signatures + cross-report dedup groups (SPEC-002 §4).

signature = sha1(normalize(category + title + top_evidence)); duplicate findings
across reports in one run collapse into a FindingGroup with an occurrence count
and the affected recipes. Conservative v1 normalization (OQ1).
"""

from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.analyze.dedup import collapse_evidence, compute_signature
from yocto_error_reports.models import Finding

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_identical_failures_share_signature_and_group():
    reports = [
        ingest.load_report(FIXTURES / "dependency_moveit.json"),
        ingest.load_report(FIXTURES / "dependency_moveit.json"),
    ]
    report = analyze(reports)
    assert len(report.findings) == 2
    assert report.findings[0].signature.startswith("sha1:")
    assert report.findings[0].signature == report.findings[1].signature

    assert len(report.groups) == 1
    group = report.groups[0]
    assert group.occurrences == 2
    assert group.signature == report.findings[0].signature
    assert group.affected_recipes == ["moveit-ros-planning-interface-dev"]


def test_signature_ignores_volatile_pid_and_line():
    a = Finding(
        category="configure",
        title='package "Qt6" considered NOT FOUND',
        evidence=["CMake Error at run.do_configure.111, line 5"],
    )
    b = Finding(
        category="configure",
        title='package "Qt6" considered NOT FOUND',
        evidence=["CMake Error at run.do_configure.999, line 9"],
    )
    assert compute_signature(a) == compute_signature(b)


def test_different_categories_differ():
    a = Finding(category="configure", title="x", evidence=["e"])
    b = Finding(category="compile", title="x", evidence=["e"])
    assert compute_signature(a) != compute_signature(b)


def test_within_finding_evidence_collapse():
    collapsed = collapse_evidence(["boom", "boom", "boom", "next"])
    assert collapsed == ["boom (×3)", "next"]


def test_corpus_findings_all_signed_and_grouped():
    report = analyze(ingest.load_reports([FIXTURES]))
    assert all(f.signature.startswith("sha1:") for f in report.findings)
    assert report.groups  # non-empty
    # groups are deterministic across runs
    again = analyze(ingest.load_reports([FIXTURES]))
    assert [g.signature for g in report.groups] == [g.signature for g in again.groups]
