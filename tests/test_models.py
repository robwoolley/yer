"""Contract test for M0-02: the cross-stage data model.

DoD (tasks/milestone-0.md M0-02): the dataclasses are importable, typed, and
carry **no logic**. Field lists come from architecture.md §"The data model"
(Build/Failure/LogLine/Finding), SPEC-002 §6 (Report + dedup groups), and
SPEC-005 §3 (Summary + truncated block).

This test pins the field names so later stages code against a stable contract.
"""

import dataclasses

from yocto_error_reports import models


def _field_names(cls) -> set[str]:
    assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"
    return {f.name for f in dataclasses.fields(cls)}


def test_logline_fields():
    assert _field_names(models.LogLine) == {"n", "level", "text"}


def test_failure_fields():
    # architecture.md §"The data model"
    assert _field_names(models.Failure) == {"task", "package", "recipe", "log", "kind"}


def test_build_fields():
    assert _field_names(models.Build) == {
        "component", "machine", "distro", "build_sys", "target_sys",
        "bitbake_version", "branch_commit", "failures", "findings", "raw", "source_path",
    }


def test_finding_fields():
    assert _field_names(models.Finding) == {
        "category", "severity", "title", "recipe", "task",
        "file", "line", "evidence", "signature", "confidence", "cascade_of",
    }


def test_finding_group_fields():
    # SPEC-002 §4/§6: cross-report dedup group carries occurrence count + recipes.
    assert _field_names(models.FindingGroup) == {
        "signature", "occurrences", "affected_recipes",
    }


def test_summary_fields():
    # SPEC-005 §3: build subset + selected findings + honest truncation block.
    assert _field_names(models.Summary) == {
        "build", "findings", "findings_omitted", "log_lines_dropped",
    }


def test_report_fields():
    # SPEC-002 §6: Report holds Build[], flat Finding[], and dedup groups.
    assert _field_names(models.Report) == {"builds", "findings", "groups"}


def test_models_instantiate_and_nest():
    line = models.LogLine(n=1, level="ERROR", text="QA Issue: ...")
    failure = models.Failure(
        task="do_package_qa", package="foo", recipe="foo-1.0", log="log", kind="task"
    )
    build = models.Build(
        component="core-image-minimal", machine="qemux86-64", distro="poky",
        build_sys="x86_64-linux", target_sys="aarch64-oe-linux",
        bitbake_version="2.18.0", branch_commit="wrynose:06dd66e",
        failures=[failure], raw={"failures": []}, source_path="error_report_x.txt",
    )
    finding = models.Finding(
        category="qa", severity="error", title="QA Issue", recipe="foo-1.0",
        task="do_package_qa", file=None, line=None, evidence=["QA Issue: ..."],
        signature="sha1:abc", confidence=0.9, cascade_of=None,
    )
    group = models.FindingGroup(signature="sha1:abc", occurrences=2, affected_recipes=["foo-1.0"])
    summary = models.Summary(
        build=build, findings=[finding], findings_omitted=0, log_lines_dropped=0
    )
    report = models.Report(builds=[build], findings=[finding], groups=[group])

    assert line.level == "ERROR"
    assert report.builds[0].failures[0].kind == "task"
    assert summary.findings[0].category == "qa"
    # Round-trips cleanly (pure data, no custom logic).
    assert dataclasses.asdict(report)["findings"][0]["signature"] == "sha1:abc"


def test_no_logic_only_dataclass_machinery():
    # "No logic": no hand-written (non-dunder) methods on any model class.
    for name in ("Build", "Failure", "LogLine", "Finding", "FindingGroup", "Summary", "Report"):
        cls = getattr(models, name)
        own_funcs = {
            k for k, v in vars(cls).items()
            if callable(v) and not k.startswith("__")
        }
        assert own_funcs == set(), f"{name} should carry no methods, found {own_funcs}"
