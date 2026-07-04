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
from ..trends.diff import TrendDiff
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


def _fixed_rows(trend: TrendDiff) -> list[dict[str, Any]]:
    return [
        {"category": f.category, "recipe": f.recipe or "(unknown recipe)", "title": f.title}
        for f in trend.fixed
    ]


def to_html(
    report: Report,
    *,
    tool_version: str,
    generated_at: str | None = None,
    trend: TrendDiff | None = None,
) -> str:
    """Render the report as a single self-contained HTML page.

    When `trend` is given (SPEC-006 §4), findings gain a new/recurring/regressed
    badge and a "fixed since baseline" list is appended — additive only; the
    canonical report.json (json_out) is untouched.
    """
    doc = report_document(report, tool_version=tool_version)
    # HTML-only augmentation: each finding's SPEC-005 Markdown copy payload
    # (SPEC-004 §2) and, when present, its trend status. Kept out of the canonical
    # report.json schema. doc["findings"] is built in report.findings order.
    build = report.builds[0] if report.builds else None
    for finding_dict, finding in zip(doc["findings"], report.findings, strict=True):
        finding_dict["copy_markdown"] = finding_markdown(build, finding)
        if trend is not None:
            finding_dict["trend_status"] = trend.status.get(finding.signature, "recurring")
    template = _env.get_template("report.html.j2")
    html = template.render(
        doc=doc,
        by_recipe=_group_by_recipe(doc["findings"]),
        generated_at=generated_at,
        fixed=_fixed_rows(trend) if trend is not None else [],
    )
    return html if html.endswith("\n") else html + "\n"
