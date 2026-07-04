"""M4-03/M4-04: self-contained static HTML (SPEC-004 §2).

Acceptance tests copied from SPEC-004 §5:
    T2  index.html opens with no network access; contains no http(s):// asset
        references.
    T4  A finding with file/line renders a location; one without still renders.
    T5  Long evidence lines do not cause horizontal page scroll (evidence
        scrolls within its own overflow-x container; long tokens elsewhere wrap).
    T6  Each finding renders a "Copy for Claude" button whose embedded payload
        is that finding's SPEC-005 Markdown (contains the SPEC-005 header and
        the finding's root-cause line). Copying is inline JS with no network.
"""

import re
from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.render.static import to_html

FIXTURES = Path(__file__).resolve().parent / "fixtures"

_ASSET_URL = re.compile(r'(?:href|src)\s*=\s*["\']https?://', re.IGNORECASE)


def _html(fixture):
    return to_html(analyze([ingest.load_report(FIXTURES / fixture)]), tool_version="1.0.0")


def test_t2_self_contained_no_external_assets():
    html = _html("configure_gz-gui9.json")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<style" in html  # inline CSS
    assert _ASSET_URL.search(html) is None  # no external asset href/src
    assert "url(http" not in html and "@import" not in html  # no external CSS
    assert "<link" not in html.lower()  # no external stylesheet/font links


def test_t2_prefers_color_scheme_dark():
    assert "prefers-color-scheme: dark" in _html("configure_gz-gui9.json")


def test_t4_finding_with_location_renders_it():
    html = _html("configure_gz-gui9.json")
    assert "CMakeLists.txt:86" in html  # file:line rendered
    assert "gz-gui9" in html  # grouped by recipe


def test_t4_finding_without_location_still_renders():
    html = _html("dependency_moveit.json")  # dependency finding has no file/line
    assert "dependency" in html
    assert "moveit-ros-planning-interface-dev" in html


def test_t5_long_lines_do_not_break_the_page():
    # Synthesize an overlong evidence line and an overlong title token; neither
    # may widen the page — evidence scrolls in its own container, text wraps.
    from yocto_error_reports.models import Finding, Report

    long_line = "x" * 4000
    long_token = "/" + "seg-" * 500 + "/CMakeLists.txt"
    report = Report(
        findings=[
            Finding(
                category="configure",
                severity="error",
                confidence=0.9,
                title="package considered NOT FOUND " + long_token,
                recipe="demo",
                task="do_configure",
                evidence=[long_line],
            )
        ]
    )
    html = to_html(report, tool_version="1.0.0")
    # evidence has its own horizontal scroll container (does not wrap; scrolls)
    assert re.search(r"pre\.evidence\s*\{[^}]*overflow-x:\s*auto", html, re.S)
    assert re.search(r"pre\.evidence\s*\{[^}]*white-space:\s*pre\b", html, re.S)
    # long tokens outside <pre> wrap instead of widening the page body
    assert re.search(r"overflow-wrap:\s*(anywhere|break-word)", html)
    # the overlong content is present but constrained by the above, not stripped
    assert long_line in html
    assert long_token in html


def test_t6_copy_button_per_finding_with_markdown_payload():
    report = analyze([ingest.load_report(FIXTURES / "configure_gz-gui9.json")])
    html = to_html(report, tool_version="1.0.0")
    # a button per finding
    assert html.count(">Copy for Claude<") == len(report.findings)
    assert html.count('data-markdown="') == len(report.findings)
    # the embedded payload is SPEC-005 Markdown for the finding
    assert "# Yocto build failure" in html  # only source is the copy payload
    assert "Root cause:" in html
    # inline JS clipboard, with an offline fallback, and no network
    assert "navigator.clipboard" in html
    assert "execCommand" in html  # file:// / insecure-context fallback
    assert _ASSET_URL.search(html) is None


def test_t6_copy_payload_is_html_escaped():
    # titles carry double-quotes ('package "Qt5" ...'); the attribute must escape
    # them so the payload can't break out of data-markdown="...".
    html = _html("configure_gz-gui9.json")
    assert 'package "Qt5"' not in html.split("data-markdown=", 1)[1][:2000]
    assert "&#34;Qt5&#34;" in html or "&quot;Qt5&quot;" in html


def test_empty_report_html_is_valid():
    from yocto_error_reports.models import Report

    html = to_html(Report(), tool_version="1.0.0")
    assert html.lstrip().lower().startswith("<!doctype html>")
