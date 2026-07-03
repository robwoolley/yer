"""CLI entrypoint for `yer`.

`--version` (M0-01) plus a provisional `inventory` subcommand (M1-08) that prints
a raw failure inventory. The full `analyze`/`summarize`/`report` subcommands land
in M2+ per SPEC-003, which supersedes `inventory`.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__, ingest, inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yer",
        description="Parse Yocto error-report.txt files into ranked build findings.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    inv = subparsers.add_parser(
        "inventory",
        help="print a raw failure inventory (provisional; superseded by `analyze`)",
    )
    inv.add_argument(
        "paths",
        nargs="+",
        help="report files, globs, directories, or - for stdin",
    )
    return parser


def _run_inventory(paths: Sequence[str]) -> int:
    builds = ingest.load_reports(paths)
    print(inventory.format_inventory(inventory.inventory(builds)))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inventory":
        return _run_inventory(args.paths)
    # No command given — print help so the bare invocation is useful.
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
