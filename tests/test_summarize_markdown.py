"""M3-03: Markdown summary output (SPEC-005 §2).

DoD: output matches the SPEC-005 §2 shape on the configure_gz-gui9 fixture;
root cause + file:line present.
"""

from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.summarize import summarize, to_markdown

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _markdown(fixture, **kw):
    report = analyze([ingest.load_report(FIXTURES / fixture)])
    return to_markdown(summarize(report, **kw)), report


def test_markdown_shape_on_configure_fixture():
    md, _ = _markdown("configure_gz-gui9.json")
    # header uses the failing recipe + task (SPEC-005 §2)
    assert md.startswith("# Yocto build failure — gz-gui9 (do_configure)")
    # build metadata line
    assert "machine: raspberrypi5" in md
    assert "distro: ros2" in md
    assert "target: aarch64-oe-linux" in md
    assert "bitbake: 2.18.0" in md
    # per-finding section with confidence, root cause, and file:line
    assert "## Finding 1 — configure-error (confidence 0.85)" in md
    assert 'Root cause: package "Qt5" considered NOT FOUND at CMakeLists.txt:86' in md
    # a fenced evidence block
    assert md.count("```") >= 2


def test_markdown_reports_truncation():
    md, report = _markdown("fetch_dartsim.json", budget=4000, top_k=1)
    # 3 findings, only 1 kept -> "further findings omitted"
    assert "further findings omitted" in md
    assert "log lines dropped" in md


def test_markdown_empty_summary_is_safe():
    from yocto_error_reports.models import Report

    md = to_markdown(summarize(Report()))
    assert isinstance(md, str)
