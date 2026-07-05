"""M3-04: JSON summary output + truncated block (SPEC-005 §3).

Acceptance test copied from SPEC-005 §5:
    T2  --format json validates and includes a `truncated` block when trimming
        occurred; byte-stable across runs.
"""

import json
from pathlib import Path

from yer import ingest
from yer.analyze import analyze
from yer.models import Report
from yer.summarize import summarize, to_json

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _report(fixture):
    return analyze([ingest.load_report(FIXTURES / fixture)])


def test_t2_json_validates_has_truncated_and_is_byte_stable():
    report = _report("fetch_dartsim.json")  # 3 findings
    first = to_json(summarize(report, top_k=1))  # force findings omitted
    second = to_json(summarize(report, top_k=1))
    assert first == second  # byte-stable

    data = json.loads(first)  # validates as JSON
    assert "truncated" in data
    assert data["truncated"]["findings_omitted"] >= 1  # trimming occurred
    assert data["truncated"]["log_lines_dropped"] > 0


def test_json_finding_and_build_fields():
    data = json.loads(to_json(summarize(_report("configure_gz-gui9.json"))))
    assert data["build"]["machine"] == "raspberrypi5"
    assert data["build"]["distro"] == "ros2"
    finding = data["findings"][0]
    for key in ("category", "confidence", "recipe", "task", "title", "file", "line",
                "likely_cause", "evidence"):
        assert key in finding
    assert finding["category"] == "configure"
    assert finding["file"] == "CMakeLists.txt"
    assert finding["likely_cause"]  # a non-empty hint


def test_json_empty_report_is_valid():
    data = json.loads(to_json(summarize(Report())))
    assert data["findings"] == []
    assert data["truncated"] == {"findings_omitted": 0, "log_lines_dropped": 0}
