"""M4-03: self-contained static HTML (SPEC-004 §2).

Acceptance tests copied from SPEC-004 §5:
    T2  index.html opens with no network access; contains no http(s):// asset
        references.
    T4  A finding with file/line renders a location; one without still renders.
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


def test_empty_report_html_is_valid():
    from yocto_error_reports.models import Report

    html = to_html(Report(), tool_version="1.0.0")
    assert html.lstrip().lower().startswith("<!doctype html>")
