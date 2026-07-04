"""M6-04: trend render layer in the HTML report (SPEC-006 §4; SPEC-004 §1-2).

Additive only: per-finding badge (new/recurring/regressed) + a "fixed since
baseline" list. The canonical report.json is untouched (SPEC-004 T3) and the HTML
stays self-contained (T2).
"""

import re
from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.cli import main
from yocto_error_reports.models import Finding, Report
from yocto_error_reports.render.json_out import to_report_json
from yocto_error_reports.render.static import to_html
from yocto_error_reports.trends.diff import diff
from yocto_error_reports.trends.store import load_runs, record_run

FIXTURES = Path(__file__).resolve().parent / "fixtures"
_ASSET_URL = re.compile(r'(?:href|src)\s*=\s*["\']https?://', re.IGNORECASE)


def _report():
    return analyze([ingest.load_report(FIXTURES / "configure_gz-gui9.json")])


def test_badge_per_finding_and_fixed_list(tmp_path):
    report = _report()
    recurring_sig = report.findings[0].signature
    # a baseline containing one of the current signatures (recurring) plus one
    # that is gone now (fixed).
    baseline = Report(
        findings=[
            Finding(signature=recurring_sig, category="configure", severity="error",
                    title="old", recipe="gz-gui9"),
            Finding(signature="sig-gone", category="compile", severity="error",
                    title="Vanished failure", recipe="oldrecipe"),
        ]
    )
    store = tmp_path / "trends.jsonl"
    record_run(baseline, store_path=store, tool_version="1.0.0")
    trend = diff(report, load_runs(store))

    html = to_html(report, tool_version="1.0.0", trend=trend)
    # a badge per finding, matching its status
    for finding in report.findings:
        status = trend.status[finding.signature]
        assert f'class="badge trend-{status}"' in html
    assert trend.status[recurring_sig] == "recurring"
    # the fixed list is rendered
    assert "Fixed since baseline" in html
    assert "Vanished failure" in html
    # still self-contained (T2)
    assert _ASSET_URL.search(html) is None


def test_new_badge_when_no_history():
    report = _report()
    trend = diff(report, [])  # first run -> all new
    html = to_html(report, tool_version="1.0.0", trend=trend)
    assert 'class="badge trend-new"' in html
    assert "Fixed since baseline" not in html  # nothing fixed on a first run


def test_html_without_trend_is_unchanged():
    report = _report()
    html = to_html(report, tool_version="1.0.0")
    # the CSS is static; assert no badge element is emitted and no fixed section
    assert 'class="badge trend-' not in html
    assert "Fixed since baseline" not in html


def test_report_json_untouched_by_trend(tmp_path):
    # the canonical report.json does not carry trend data and is byte-identical
    # whether or not a trend is rendered (SPEC-004 T3).
    report = _report()
    store = tmp_path / "trends.jsonl"
    record_run(report, store_path=store, tool_version="1.0.0")
    trend = diff(report, load_runs(store))
    plain = to_report_json(report, tool_version="1.0.0")
    assert "trend" not in plain
    # rendering HTML with a trend must not mutate the report used for JSON
    to_html(report, tool_version="1.0.0", trend=trend)
    assert to_report_json(report, tool_version="1.0.0") == plain


def test_report_cli_store_annotates_html_only(tmp_path):
    fixture = str(FIXTURES / "configure_gz-gui9.json")
    store = str(tmp_path / "trends.jsonl")
    # seed history so the current run has a baseline
    main(["trend", fixture, "--store", store, "--record"])

    plain_dir = tmp_path / "plain"
    trend_dir = tmp_path / "trend"
    assert main(["report", fixture, "--html", str(plain_dir)]) == 1
    assert main(["report", fixture, "--html", str(trend_dir), "--store", store]) == 1

    # HTML carries a trend badge only in the --store run
    assert 'class="badge trend-' not in (plain_dir / "index.html").read_text(encoding="utf-8")
    assert 'class="badge trend-' in (trend_dir / "index.html").read_text(encoding="utf-8")
    # report.json is byte-identical regardless of the trend layer (SPEC-004 T3)
    assert (plain_dir / "report.json").read_bytes() == (trend_dir / "report.json").read_bytes()
