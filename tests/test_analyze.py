"""M2-01: rule registry + analyze orchestration skeleton (SPEC-002 §1, §6).

`analyze(builds)` runs each failure's parsed `LogLine[]` through the registered
rules and returns a `Report`. Adding a category is a new rule module; the
orchestrator does not change. Findings selection/ranking (root-cause vs cascade)
and dedup groups arrive in later M2 tasks.
"""

from yocto_error_reports.analyze import analyze, signatures
from yocto_error_reports.analyze.signatures import Rule
from yocto_error_reports.models import Build, Failure, Finding, Report


def _match_boom(failure, lines):
    return any("boom" in line.text for line in lines)


def _extract_boom(failure, lines):
    return Finding(category="compile", severity="error", title="boom", recipe=failure.recipe)


_BOOM_RULE = Rule(
    name="boom",
    category="compile",
    severity="error",
    match=_match_boom,
    extract=_extract_boom,
    confidence=0.9,
    order=10,
)


def test_empty_builds_gives_empty_deterministic_report():
    report = analyze([])
    assert isinstance(report, Report)
    assert report.builds == []
    assert report.findings == []
    assert report.groups == []


def test_trivial_rule_matches_and_extracts():
    failure = Failure(task="do_compile", recipe="foo", log="NOTE: hi\nERROR: boom", kind="task")
    report = analyze([Build(failures=[failure])], rules=[_BOOM_RULE])
    assert len(report.findings) == 1
    assert report.findings[0].category == "compile"
    assert report.findings[0].title == "boom"
    assert report.findings[0].recipe == "foo"


def test_non_matching_rule_yields_no_findings():
    build = Build(failures=[Failure(task="do_compile", log="ERROR: unrelated", kind="task")])
    assert analyze([build], rules=[_BOOM_RULE]).findings == []


def test_ingest_parse_findings_surface_in_report():
    # a Build carrying an ingest-time parse Finding (malformed input, M1-03)
    build = Build(findings=[Finding(category="unknown", severity="error", title="bad json")])
    report = analyze([build], rules=[])
    assert [f.title for f in report.findings] == ["bad json"]


def test_multiple_matching_rules_produce_deterministic_findings():
    def extract_named(name):
        return lambda failure, lines: Finding(category="compile", severity="error", title=name)

    always = lambda failure, lines: True  # noqa: E731
    r_late = Rule("late", "compile", "error", always, extract_named("late"), 0.5, order=20)
    r_early = Rule("early", "compile", "error", always, extract_named("early"), 0.5, order=5)
    build = Build(failures=[Failure(task="do_compile", log="ERROR: x", kind="task")])
    # both rules fire; final order is the deterministic rank order (SPEC-002 §5)
    first = [f.title for f in analyze([build], rules=[r_late, r_early]).findings]
    second = [f.title for f in analyze([build], rules=[r_early, r_late]).findings]
    assert set(first) == {"early", "late"}
    assert first == second  # deterministic regardless of input rule order


def test_default_uses_module_registry():
    saved = signatures.registered_rules()
    try:
        signatures.clear_rules()
        signatures.register(_BOOM_RULE)
        build = Build(failures=[Failure(task="do_compile", log="ERROR: boom", kind="task")])
        assert len(analyze([build]).findings) == 1  # no rules= -> registry
    finally:
        signatures.clear_rules()
        for rule in saved:
            signatures.register(rule)
