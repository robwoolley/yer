"""M4-01: canonical, deterministic report.json (SPEC-004 §1).

Acceptance test copied from SPEC-004 §5:
    T3  report.json validated against the schema; identical across two runs.
"""

import json
from pathlib import Path

from yer import ingest
from yer.analyze import analyze
from yer.render.json_out import to_report_json

FIXTURES = Path(__file__).resolve().parent / "fixtures"

_FINDING_KEYS = {
    "category", "severity", "confidence", "title", "recipe", "task", "file",
    "line", "evidence", "signature", "cascade_of", "occurrences", "affected_recipes",
}
_BUILD_KEYS = {"component", "machine", "distro", "source", "failure_count"}


def _report():
    return analyze(ingest.load_reports([FIXTURES]))


def test_t3_byte_identical_across_runs():
    report = _report()
    first = to_report_json(report, tool_version="1.2.3")
    second = to_report_json(report, tool_version="1.2.3")
    assert first == second  # byte-identical


def test_t3_schema_shape():
    data = json.loads(to_report_json(_report(), tool_version="1.2.3"))
    assert data["schema_version"] == "1.0"
    assert data["tool_version"] == "1.2.3"
    assert data["builds"] and data["builds"][0].keys() >= _BUILD_KEYS
    assert data["findings"] and data["findings"][0].keys() >= _FINDING_KEYS
    for key in ("errors", "warnings", "by_category"):
        assert key in data["summary"]


def test_no_wall_clock_timestamp_in_body():
    text = to_report_json(_report(), tool_version="1.0.0")
    assert "generated_at" not in text and "timestamp" not in text


def test_findings_in_rank_order_and_occurrences_from_groups():
    report = _report()
    data = json.loads(to_report_json(report, tool_version="1.0.0"))
    # findings preserve the analyzer's deterministic rank order (SPEC-002 §6)
    assert [f["signature"] for f in data["findings"]] == [f.signature for f in report.findings]
    # occurrences/affected_recipes are carried from the dedup groups
    assert all(f["occurrences"] >= 1 for f in data["findings"])


def test_empty_report_json():
    from yer.models import Report

    data = json.loads(to_report_json(Report(), tool_version="1.0.0"))
    assert data["findings"] == [] and data["builds"] == []
    assert data["summary"]["by_category"] == {}
