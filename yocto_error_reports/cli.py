"""CLI entrypoint for `yer`.

M0-01 scope: wire the console_script and `--version` only. Subcommands
(`analyze`, `summarize`, `report`) land in later milestones per the roadmap.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    # No subcommands yet (M0-01); print help so the bare invocation is useful.
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
