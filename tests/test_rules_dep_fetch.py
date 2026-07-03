"""M2-03: dependency + fetch rules (SPEC-002 §2).

DoD: dependency_moveit -> one dependency finding; fetch_dartsim -> a fetch
finding (part of SPEC-002 T1). Fixtures are the anonymized corpus samples.
"""

from pathlib import Path

from yocto_error_reports import ingest, parse
from yocto_error_reports.analyze import analyze
from yocto_error_reports.analyze.rules import dependency, fetch

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _failure(fixture, task=None):
    build = ingest.load_report(FIXTURES / fixture)
    if task is None:
        failure = build.failures[0]
    else:
        failure = next(f for f in build.failures if f.task == task)
    return build, failure, parse.parse_log(failure.log)


def test_dependency_rule_matches_and_extracts():
    _, failure, lines = _failure("dependency_moveit.json")
    assert dependency.DEPENDENCY_RULE.match(failure, lines)
    finding = dependency.DEPENDENCY_RULE.extract(failure, lines)
    assert finding.category == "dependency"
    assert finding.severity == "error"
    assert "moveit-ros-planning-interface-dev" in finding.title
    assert finding.recipe == "moveit-ros-planning-interface-dev"  # from package


def test_dependency_integration_single_finding():
    build, *_ = _failure("dependency_moveit.json")
    findings = analyze([build]).findings
    assert len(findings) == 1
    assert findings[0].category == "dependency"


def test_fetch_rule_matches_and_extracts_uri_and_reason():
    _, failure, lines = _failure("fetch_dartsim.json", task="do_fetch")
    assert fetch.FETCH_RULE.match(failure, lines)
    finding = fetch.FETCH_RULE.extract(failure, lines)
    assert finding.category == "fetch"
    assert finding.task == "do_fetch"
    assert "dart.git" in finding.title  # the URI
    assert "Unable to fetch" in finding.title  # the reason


def test_fetch_integration_yields_one_fetch_finding():
    build, *_ = _failure("fetch_dartsim.json")  # multi-failure report
    fetch_findings = [f for f in analyze([build]).findings if f.category == "fetch"]
    assert len(fetch_findings) == 1
    assert fetch_findings[0].task == "do_fetch"


def test_rules_do_not_misfire_on_compile():
    _, failure, lines = _failure("compile_nanoflann.json")
    assert not fetch.FETCH_RULE.match(failure, lines)
    assert not dependency.DEPENDENCY_RULE.match(failure, lines)
