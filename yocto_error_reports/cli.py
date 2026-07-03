"""CLI entrypoint for `yer` (SPEC-003).

`--version` plus the `analyze` subcommand: parse + analyze inputs, render ranked
findings as text, and return the CI exit code. Rendering and exit-code policy
live here so they never leak into `parse`/`analyze`. `--format json`, filters, and
`--no-color` land in M2-10; `report`/`summarize` in M3/M4.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__, ingest
from .analyze import analyze
from .models import Report

# Severity thresholding for --fail-on (SPEC-003 §4): error > failure > warning > anomaly.
_SEVERITY_RANK = {"error": 0, "failure": 1, "warning": 2, "anomaly": 3}


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
    analyze_cmd.add_argument(
        "--fail-on",
        choices=["error", "failure", "warning", "none"],
        default="error",
        help="minimum severity that makes the run fail with exit 1 (default: error)",
    )
    analyze_cmd.add_argument("-o", "--output", help="write output to a file (default: stdout)")
    return parser


def _exit_code(report: Report, fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = _SEVERITY_RANK[fail_on]
    hit = any(_SEVERITY_RANK.get(f.severity, 9) <= threshold for f in report.findings)
    return 1 if hit else 0


def render_text(report: Report, exit_code: int) -> str:
    """Render ranked findings as plain, deterministic ASCII (SPEC-003 §3)."""
    lines: list[str] = []
    for finding in report.findings:
        recipe = finding.recipe or "(unknown recipe)"
        head = f"[{finding.severity.upper()}] {recipe}"
        if finding.task:
            head += f" · {finding.task}"
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

    errors = sum(1 for f in report.findings if f.severity == "error")
    warnings = sum(1 for f in report.findings if f.severity == "warning")
    lines.append(f"{errors} error(s), {warnings} warning(s) - exit {exit_code}")
    return "\n".join(lines)


def _run_analyze(args: argparse.Namespace) -> int:
    builds = ingest.load_reports(args.inputs)
    if not builds:
        print(f"yer: no matching inputs: {' '.join(args.inputs)}", file=sys.stderr)
        return 2

    report = analyze(builds)
    code = _exit_code(report, args.fail_on)
    text = render_text(report, code)

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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _run_analyze(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
