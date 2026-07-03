"""Acceptance test for M0-01: `yer --version` prints a version.

DoD (tasks/milestone-0.md M0-01): `yer --version` prints a version string.
This exercises the CLI entrypoint the console_script points at.
"""

import re

import pytest

from yocto_error_reports import __version__
from yocto_error_reports.cli import main

_SEMVER = re.compile(r"\d+\.\d+\.\d+")


def test_version_constant_is_semver():
    assert _SEMVER.fullmatch(__version__)


def test_cli_version_flag_prints_version(capsys):
    # argparse's version action prints to stdout then exits 0.
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out
