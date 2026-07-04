"""M5-02: SARIF 2.1.0 emitter (SPEC-004 §3).

Acceptance tests copied from SPEC-004 §5:
    T7  SARIF output is a valid 2.1.0 document: version == "2.1.0", one runs[0]
        with tool.driver.name == "yer" and tool.driver.rules[] covering the
        distinct categories; each finding is a runs[0].results[] entry with
        ruleId == category, level per the §3 severity map, and message.text set.
        A finding with file/line carries locations[0].physicalLocation
        (artifactLocation.uri, region.startLine); one without omits locations.
    T8  SARIF output is byte-identical across two runs (no wall-clock timestamps)
        and its titles/evidence contain no host-identity structure.
"""

import json
import re
from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.models import Build, Failure, Finding, Report
from yocto_error_reports.render.sarif import to_sarif

FIXTURES = Path(__file__).resolve().parent / "fixtures"

_HOSTDIR = re.compile(r"/[\w.+-]+/[\w.+-]+/\d{4}-\d{2}-\d{2}")


def _doc(report):
    return json.loads(to_sarif(report, tool_version="1.0.0"))


def test_t7_structure_and_mapping():
    report = analyze([ingest.load_report(FIXTURES / "configure_gz-gui9.json")])
    doc = _doc(report)
    assert doc["version"] == "2.1.0"
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "yer"
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert rule_ids == {f.category for f in report.findings}  # rules cover categories
    results = run["results"]
    assert len(results) == len(report.findings)
    for res, finding in zip(results, report.findings, strict=True):
        assert res["ruleId"] == finding.category
        assert res["message"]["text"]  # message.text set
    # the configure finding carries file/line -> physicalLocation
    loc = results[0]["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == report.findings[0].file
    assert loc["region"]["startLine"] == report.findings[0].line


def test_t7_finding_without_location_omits_locations():
    report = analyze([ingest.load_report(FIXTURES / "dependency_moveit.json")])
    assert report.findings[0].file is None
    assert "locations" not in _doc(report)["runs"][0]["results"][0]


def test_t7_level_mapping():
    report = Report(
        findings=[
            Finding(category="compile", severity="error", title="e"),
            Finding(category="qa", severity="failure", title="f"),
            Finding(category="qa", severity="warning", title="w"),
            Finding(category="unknown", severity="anomaly", title="a"),
        ]
    )
    levels = [r["level"] for r in _doc(report)["runs"][0]["results"]]
    assert levels == ["error", "error", "warning", "note"]


def test_t8_byte_identical_across_runs():
    report = analyze([ingest.load_report(FIXTURES / "configure_gz-gui9.json")])
    assert to_sarif(report, tool_version="1.0.0") == to_sarif(report, tool_version="1.0.0")


def test_t8_host_identity_redacted_from_sarif():
    # an unscrubbed report whose finding title carries host-identity structure
    log = (
        "Nothing RPROVIDES 'foo' (but /ala-host99/rwoolley/2026-06-30/build/../"
        "layers/meta/foo_1.0.bb RDEPENDS on it)\n"
        "No eligible RPROVIDERs exist for 'foo'"
    )
    leaky = Failure(
        task="Nothing provides '/ala-host99/rwoolley/2026-06-30/foo'",
        package="foo",
        log=log,
        kind="message",
    )
    out = to_sarif(analyze([Build(failures=[leaky])]), tool_version="1.0.0")
    assert "rwoolley" not in out
    assert "/ala-host99" not in out
    assert _HOSTDIR.search(out) is None
    assert "HOSTDIR" in out  # redaction placeholder present in the title
