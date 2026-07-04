"""CLI entrypoint for `yer` (SPEC-003).

`--version` plus the `analyze`, `report`, and `summarize` subcommands: parse +
analyze inputs, then render ranked findings (text/JSON), static artifacts
(HTML + canonical JSON), or a token-bounded LLM summary, applying category/recipe
filters and returning the CI exit code. Rendering and exit-code policy live here
so they never leak into `parse`/`analyze`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from . import __version__, ingest
from .analyze import analyze
from .models import Finding, Report
from .render.json_out import to_report_json
from .render.sarif import to_sarif
from .render.static import to_html
from .summarize import DEFAULT_BUDGET, summarize, to_json, to_markdown
from .trends.diff import TrendDiff, diff, to_trend_json
from .trends.store import DEFAULT_STORE, load_runs, record_run

# Severity thresholding for --fail-on (SPEC-003 §4): error > failure > warning > anomaly.
_SEVERITY_RANK = {"error": 0, "failure": 1, "warning": 2, "anomaly": 3}
_ANSI = {"error": "\033[31m", "failure": "\033[31m", "warning": "\033[33m", "anomaly": "\033[36m"}
_RESET = "\033[0m"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yer",
        description="Parse Yocto error-report.txt files into ranked build findings.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    analyze_cmd = subparsers.add_parser("analyze", help="parse + analyze reports; print findings")
    analyze_cmd.add_argument(
        "inputs", nargs="+", help="report files, globs, directories, or - for stdin"
    )
    analyze_cmd.add_argument("--format", choices=["text", "json", "sarif"], default="text")
    analyze_cmd.add_argument(
        "--fail-on",
        choices=["error", "failure", "warning", "none"],
        default="error",
        help="minimum severity that makes the run fail with exit 1 (default: error)",
    )
    analyze_cmd.add_argument(
        "--category", action="append", metavar="CAT", help="only show this category (repeatable)"
    )
    analyze_cmd.add_argument("--recipe", metavar="NAME", help="only show this recipe")
    analyze_cmd.add_argument("--max-evidence", type=int, default=15, metavar="N")
    analyze_cmd.add_argument("--no-color", action="store_true", help="disable ANSI color")
    analyze_cmd.add_argument("-o", "--output", help="write output to a file (default: stdout)")

    report_cmd = subparsers.add_parser(
        "report", help="write static artifacts: <dir>/index.html + <dir>/report.json"
    )
    report_cmd.add_argument(
        "inputs", nargs="+", help="report files, globs, directories, or - for stdin"
    )
    report_cmd.add_argument(
        "--html", required=True, metavar="DIR", help="output directory (index.html + report.json)"
    )
    report_cmd.add_argument(
        "--format",
        choices=["json", "sarif"],
        help="also emit canonical JSON (SPEC-004 §1) or SARIF (§3) to -o",
    )
    report_cmd.add_argument(
        "-o", "--output", metavar="PATH", help="path for the extra --format json/sarif output"
    )
    report_cmd.add_argument(
        "--fail-on",
        choices=["error", "failure", "warning", "none"],
        default="error",
        help="minimum severity that makes the run fail with exit 1 (default: error)",
    )
    report_cmd.add_argument(
        "--category", action="append", metavar="CAT", help="only include this category (repeatable)"
    )
    report_cmd.add_argument("--recipe", metavar="NAME", help="only include this recipe")

    sum_cmd = subparsers.add_parser("summarize", help="emit a token-bounded LLM summary")
    sum_cmd.add_argument(
        "inputs", nargs="+", help="report files, globs, directories, or - for stdin"
    )
    sum_cmd.add_argument("--for-llm", action="store_true", help="(implied by the subcommand)")
    sum_cmd.add_argument("--format", choices=["md", "json"], default="md")
    sum_cmd.add_argument("--budget", type=int, default=DEFAULT_BUDGET, metavar="TOKENS")
    sum_cmd.add_argument(
        "--include-config", action="store_true", help="include build config (still redacted)"
    )
    sum_cmd.add_argument("-o", "--output", help="write output to a file (default: stdout)")

    trend_cmd = subparsers.add_parser(
        "trend", help="diff a run against recorded history (new/recurring/regressed/fixed)"
    )
    trend_cmd.add_argument(
        "inputs", nargs="+", help="report files, globs, directories, or - for stdin"
    )
    trend_cmd.add_argument(
        "--store", metavar="PATH", default=str(DEFAULT_STORE), help="run store (JSONL)"
    )
    trend_cmd.add_argument(
        "--baseline", metavar="RUN_ID", help="baseline run id (default: previous run)"
    )
    trend_cmd.add_argument(
        "--record", action="store_true", help="append this run to the store (else dry run)"
    )
    trend_cmd.add_argument(
        "--fail-on-new", action="store_true", help="exit 1 if any new/regressed finding"
    )
    trend_cmd.add_argument("--format", choices=["text", "json"], default="text")
    trend_cmd.add_argument("-o", "--output", help="write output to a file (default: stdout)")
    return parser


def _exit_code(findings: list[Finding], fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = _SEVERITY_RANK[fail_on]
    hit = any(_SEVERITY_RANK.get(f.severity, 9) <= threshold for f in findings)
    return 1 if hit else 0


def _filter(
    findings: list[Finding], categories: list[str] | None, recipe: str | None
) -> list[Finding]:
    if categories:
        findings = [f for f in findings if f.category in categories]
    if recipe:
        findings = [f for f in findings if f.recipe == recipe]
    return findings


def _truncate_evidence(findings: list[Finding], n: int) -> None:
    if n < 0:
        return
    for finding in findings:
        if n == 0:
            finding.evidence = []
        elif len(finding.evidence) > n:
            finding.evidence = finding.evidence[-n:]  # tail-biased: keep the last n


def _should_color(no_color: bool, output: str | None) -> bool:
    if no_color or output or os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def render_text(findings: list[Finding], exit_code: int, *, color: bool) -> str:
    """Render ranked findings as deterministic ASCII (SPEC-003 §3)."""
    lines: list[str] = []
    for finding in findings:
        recipe = finding.recipe or "(unknown recipe)"
        tag = f"[{finding.severity.upper()}]"
        if color:
            tag = f"{_ANSI.get(finding.severity, '')}{tag}{_RESET}"
        head = f"{tag} {recipe}"
        if finding.task:
            head += f" [{finding.task}]"
        head += f" - {finding.category} ({finding.confidence:.2f})"
        if finding.cascade_of:
            head += "  (cascade)"
        lines.append(head)
        lines.append(f"    {finding.title}")
        if finding.file:
            loc = finding.file + (f":{finding.line}" if finding.line else "")
            lines.append(f"    at {loc}")
        lines.extend(f"      | {ev}" for ev in finding.evidence)
        lines.append("")

    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    lines.append(f"{errors} error(s), {warnings} warning(s) - exit {exit_code}")
    return "\n".join(lines)


def render_json(findings: list[Finding], report: Report) -> str:
    """Deterministic, byte-stable JSON of findings (SPEC-003 §5; SPEC-004 schema in M4)."""
    groups = {g.signature: g for g in report.groups}
    out_findings = []
    for finding in findings:
        group = groups.get(finding.signature)
        out_findings.append(
            {
                "category": finding.category,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "title": finding.title,
                "recipe": finding.recipe,
                "task": finding.task,
                "file": finding.file,
                "line": finding.line,
                "evidence": finding.evidence,
                "signature": finding.signature,
                "cascade_of": finding.cascade_of,
                "occurrences": group.occurrences if group else 1,
                "affected_recipes": group.affected_recipes if group else (
                    [finding.recipe] if finding.recipe else []
                ),
            }
        )
    by_category: dict[str, int] = {}
    for finding in findings:
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
    summary = {
        "errors": sum(1 for f in findings if f.severity == "error"),
        "warnings": sum(1 for f in findings if f.severity == "warning"),
        "by_category": by_category,
    }
    document = {"schema_version": "1.0", "findings": out_findings, "summary": summary}
    return json.dumps(document, indent=2, sort_keys=True)


def _run_analyze(args: argparse.Namespace) -> int:
    builds = ingest.load_reports(args.inputs)
    if not builds:
        print(f"yer: no matching inputs: {' '.join(args.inputs)}", file=sys.stderr)
        return 2

    report = analyze(builds)
    findings = _filter(report.findings, args.category, args.recipe)
    _truncate_evidence(findings, args.max_evidence)
    code = _exit_code(findings, args.fail_on)

    if args.format == "sarif":
        text = to_sarif(replace(report, findings=findings), tool_version=__version__)
    elif args.format == "json":
        text = render_json(findings, report)
    else:
        text = render_text(findings, code, color=_should_color(args.no_color, args.output))

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except OSError as exc:
            print(f"yer: cannot write output: {exc}", file=sys.stderr)
            return 2
    else:
        print(text)
    return code


def _write_output(text: str, output: str | None) -> int | None:
    """Write text to a file or stdout. Returns 2 on write error, else None."""
    if output:
        try:
            with open(output, "w", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except OSError as exc:
            print(f"yer: cannot write output: {exc}", file=sys.stderr)
            return 2
    else:
        print(text)
    return None


def _run_report(args: argparse.Namespace) -> int:
    """Write `<dir>/index.html` + `<dir>/report.json` (SPEC-004); exit like analyze."""
    builds = ingest.load_reports(args.inputs)
    if not builds:
        print(f"yer: no matching inputs: {' '.join(args.inputs)}", file=sys.stderr)
        return 2

    report = analyze(builds)
    findings = _filter(report.findings, args.category, args.recipe)
    code = _exit_code(findings, args.fail_on)
    # Filters scope the artifacts too (consistent with analyze). Rendering reads
    # report.findings; groups are keyed by signature, so extra groups are inert.
    rendered = replace(report, findings=findings) if (args.category or args.recipe) else report

    json_text = to_report_json(rendered, tool_version=__version__)
    html_text = to_html(rendered, tool_version=__version__)

    out_dir = Path(args.html)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html_text, encoding="utf-8")
        (out_dir / "report.json").write_text(json_text + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"yer: cannot write artifacts: {exc}", file=sys.stderr)
        return 2

    if args.format and args.output:
        if args.format == "sarif":
            extra = to_sarif(rendered, tool_version=__version__)
        else:
            extra = json_text
        rc = _write_output(extra, args.output)
        if rc is not None:
            return rc
    return code


def _run_summarize(args: argparse.Namespace) -> int:
    builds = ingest.load_reports(args.inputs)
    if not builds:
        print(f"yer: no matching inputs: {' '.join(args.inputs)}", file=sys.stderr)
        return 2
    summary = summarize(analyze(builds), budget=args.budget, include_config=args.include_config)
    text = to_json(summary) if args.format == "json" else to_markdown(summary)
    return _write_output(text, args.output) or 0


def render_trend(report: Report, result: TrendDiff) -> str:
    """Render the trend diff as deterministic ASCII (SPEC-006 §4)."""
    counts = (
        f"new {len(result.new)}, recurring {len(result.recurring)}, "
        f"regressed {len(result.regressed)}, fixed {len(result.fixed)}"
    )
    baseline = result.baseline_run_id or "(no baseline — first run)"
    lines = [f"Trend vs {baseline}", counts, ""]
    for finding in report.findings:  # rank order (SPEC-002 §6)
        status = result.status.get(finding.signature, "recurring")
        recipe = finding.recipe or "(unknown recipe)"
        lines.append(f"[{status}] {recipe} - {finding.category}: {finding.title}")
    if result.fixed:
        lines.append("")
        lines.append("Fixed since baseline:")
        for fixed in result.fixed:
            recipe = fixed.recipe or "(unknown recipe)"
            lines.append(f"[fixed] {recipe} - {fixed.category}: {fixed.title}")
    return "\n".join(lines)


def _run_trend(args: argparse.Namespace) -> int:
    """Diff a run against recorded history (SPEC-006 §4)."""
    builds = ingest.load_reports(args.inputs)
    if not builds:
        print(f"yer: no matching inputs: {' '.join(args.inputs)}", file=sys.stderr)
        return 2

    report = analyze(builds)
    runs = load_runs(args.store)
    try:
        result = diff(report, runs, baseline=args.baseline)
    except ValueError as exc:
        print(f"yer: {exc}", file=sys.stderr)
        return 2

    if args.record:  # explicit: a dry run never mutates history
        record_run(report, store_path=args.store, tool_version=__version__)

    text = to_trend_json(result) if args.format == "json" else render_trend(report, result)
    rc = _write_output(text, args.output)
    if rc is not None:
        return rc
    if args.fail_on_new and (result.new or result.regressed):
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _run_analyze(args)
    if args.command == "report":
        return _run_report(args)
    if args.command == "summarize":
        return _run_summarize(args)
    if args.command == "trend":
        return _run_trend(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
