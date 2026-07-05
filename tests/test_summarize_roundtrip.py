"""M3-08: round-trip smoke — summaries are pipe-ready across categories (T6).

The full round-trip `yer summarize <sample> | claude -p "diagnose"` needs the
`claude` CLI + network, so it is a documented manual smoke (docs/quickstart.md).
This test covers the automatable part: for ≥3 category samples the summary is
well-formed, non-empty, and free of host identity — safe to pipe out.
"""

import json
import re
from pathlib import Path

import pytest

from yer.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"
_IDENTITY = re.compile(r"rwoolley|/folk/|ala-lpggp|SSH_AUTH_SOCK=\"/")


@pytest.mark.parametrize(
    "fixture",
    [
        "compile_nanoflann.json",
        "configure_gz-gui9.json",
        "patch_ogre-next.json",
        "dependency_moveit.json",
    ],
)
def test_summary_is_pipe_ready_and_clean(fixture, capsys):
    assert main(["summarize", str(FIXTURES / fixture)]) == 0
    markdown = capsys.readouterr().out
    assert markdown.startswith("# Yocto build failure")
    assert "Root cause:" in markdown

    assert main(["summarize", str(FIXTURES / fixture), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["findings"] and data["findings"][0]["title"]

    assert not _IDENTITY.search(markdown + json.dumps(data))  # no host identity leaks
