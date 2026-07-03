"""CLI entrypoint for `yer` (SPEC-003).

`--version` plus the `analyze` subcommand: parse + analyze inputs, render ranked
findings as text or JSON, apply category/recipe filters, and return the CI exit
code. Rendering and exit-code policy live here so they never leak into
`parse`/`analyze`. `report`/`summarize` land in M3/M4.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence

from . import __version__, ingest
from .analyze import analyze
from .models import Finding, Report
from .summarize import DEFAULT_BUDGET, summarize, to_json, to_markdown

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
    analyze_cmd.add_argument("--format", choices=["text", "json"], default="text")
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

    if args.format == "json":
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


def _run_summarize(args: argparse.Namespace) -> int:
    builds = ingest.load_reports(args.inputs)
    if not builds:
        print(f"yer: no matching inputs: {' '.join(args.inputs)}", file=sys.stderr)
        return 2
    summary = summarize(analyze(builds), budget=args.budget, include_config=args.include_config)
    text = to_json(summary) if args.format == "json" else to_markdown(summary)
    return _write_output(text, args.output) or 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _run_analyze(args)
    if args.command == "summarize":
        return _run_summarize(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
