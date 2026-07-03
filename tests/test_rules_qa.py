"""M2-05: qa rule + within-finding dedup (SPEC-002 §2 qa, §4).

Acceptance test copied from SPEC-002 §7:
    T2  gz-physics-vendor QA sample -> one qa finding with a symlink-count,
        not 14 (the many near-identical per-symlink lines collapse).
"""

from pathlib import Path

from yocto_error_reports import ingest, parse
from yocto_error_reports.analyze import analyze
from yocto_error_reports.analyze.rules import qa

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _failure(fixture):
    build = ingest.load_report(FIXTURES / fixture)
    return build, build.failures[0], parse.parse_log(build.failures[0].log)


def test_t2_qa_collapses_to_one_finding_with_symlink_count():
    build, *_ = _failure("qa_gz-physics-vendor.json")
    findings = analyze([build]).findings
    assert len(findings) == 1  # not one-per-QA-line
    finding = findings[0]
    assert finding.category == "qa"
    assert finding.recipe == "gz-physics-vendor"
    # the 10 near-identical [dev-so] symlink lines are collapsed with a count
    assert "dev-so" in finding.title and "10" in finding.title
    # evidence is collapsed to one representative line per class, not 11 lines
    assert len(finding.evidence) <= 3
    assert any("(x10)" in line for line in finding.evidence)


def test_qa_rule_reports_distinct_classes():
    _, failure, lines = _failure("qa_gz-physics-vendor.json")
    finding = qa.QA_RULE.extract(failure, lines)
    assert "dev-so" in finding.title  # 10 symlink issues
    assert "buildpaths" in finding.title  # 1 buildpaths issue


def test_qa_rule_does_not_match_compile():
    _, failure, lines = _failure("compile_nanoflann.json")
    assert not qa.QA_RULE.match(failure, lines)
