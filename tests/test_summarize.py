"""M3-01: selection into a token-bounded Summary (SPEC-005 §1).

Acceptance test copied from SPEC-005 §5:
    T5  For a multi-finding report, root cause (rank 1) is always present even
        at a small --budget.
"""

from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.models import Report
from yocto_error_reports.summarize import summarize

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _report(fixture):
    return analyze([ingest.load_report(FIXTURES / fixture)])


def test_t5_root_cause_present_at_small_budget():
    report = _report("fetch_dartsim.json")  # 3 findings (fetch + 2 compile)
    root = report.findings[0]
    summary = summarize(report, budget=5, top_k=5, max_evidence=8)
    assert summary.findings  # never empty when the report has findings
    assert summary.findings[0].signature == root.signature  # rank-1 kept
    assert summary.findings_omitted == len(report.findings) - len(summary.findings)


def test_top_k_caps_selection():
    report = _report("fetch_dartsim.json")
    summary = summarize(report, budget=1_000_000, top_k=1)
    assert len(summary.findings) == 1
    assert summary.findings_omitted == len(report.findings) - 1


def test_evidence_trimmed_tail_biased():
    report = _report("configure_gz-gui9.json")
    original = report.findings[0].evidence
    summary = summarize(report, budget=1_000_000, top_k=5, max_evidence=2)
    assert all(len(f.evidence) <= 2 for f in summary.findings)
    # tail-biased: keep the suffix (the real error sits near the end)
    expected = original[-2:] if len(original) > 2 else original
    assert summary.findings[0].evidence == expected
    # summarize must not mutate the source report
    assert report.findings[0].evidence == original


def test_truncation_accounts_for_dropped_log_lines():
    report = _report("fetch_dartsim.json")
    summary = summarize(report, budget=4000)
    assert summary.build is not None
    assert summary.log_lines_dropped > 0  # big logs, few evidence lines shown


def test_empty_report_summarizes_to_empty():
    summary = summarize(Report())
    assert summary.findings == []
    assert summary.build is None
    assert summary.findings_omitted == 0
