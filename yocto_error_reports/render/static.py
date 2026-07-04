"""Self-contained static HTML report (SPEC-004 §2).

Renders one `index.html` with inline CSS/JS and **no external requests** via
Jinja2. Findings are grouped by recipe (rank order within), cascades nested.
Consumes the redacted `report_document` (SPEC-004 §4), so evidence is safe to
publish. Render-only module; the core stays stdlib-only.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models import Report
from ..summarize import finding_markdown
from .json_out import report_document

_TEMPLATES = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "j2"]),  # escape titles/evidence
    trim_blocks=True,
    lstrip_blocks=True,
)


def _group_by_recipe(findings: list[dict[str, Any]]) -> OrderedDict[str, list[dict[str, Any]]]:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for finding in findings:
        grouped.setdefault(finding["recipe"] or "(unknown recipe)", []).append(finding)
    return grouped


def to_html(report: Report, *, tool_version: str, generated_at: str | None = None) -> str:
    """Render the report as a single self-contained HTML page."""
    doc = report_document(report, tool_version=tool_version)
    # HTML-only augmentation: each finding's SPEC-005 Markdown copy payload
    # (SPEC-004 §2). Kept out of the canonical report.json schema. doc["findings"]
    # is built in report.findings order, so the zip pairs 1:1.
    build = report.builds[0] if report.builds else None
    for finding_dict, finding in zip(doc["findings"], report.findings, strict=True):
        finding_dict["copy_markdown"] = finding_markdown(build, finding)
    template = _env.get_template("report.html.j2")
    html = template.render(
        doc=doc,
        by_recipe=_group_by_recipe(doc["findings"]),
        generated_at=generated_at,
    )
    return html if html.endswith("\n") else html + "\n"
