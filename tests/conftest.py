"""Shared test fixtures.

`built_dist` builds the sdist + wheel once per session for the release tests
(SPEC-007). The build uses `--no-isolation` when the backend (hatchling) is
importable — CI's fast, offline path via the dev extras — and otherwise falls
back to an isolated build.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def built_dist(tmp_path_factory):
    """Build sdist + wheel once; return (wheel_path, sdist_path)."""
    pytest.importorskip("build", reason="pip install '.[dev]' to run the release tests")
    out = tmp_path_factory.mktemp("dist")
    cmd = [sys.executable, "-m", "build", "--outdir", str(out)]
    try:
        import hatchling  # noqa: F401  -- backend present -> skip isolation (fast, offline)

        cmd.insert(3, "--no-isolation")
    except ImportError:
        pass  # fall back to an isolated build (fetches the backend)
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    assert proc.returncode == 0, f"build failed:\n{proc.stdout}\n{proc.stderr}"
    wheels = list(out.glob("*.whl"))
    sdists = list(out.glob("*.tar.gz"))
    assert len(wheels) == 1 and len(sdists) == 1, list(out.iterdir())
    return wheels[0], sdists[0]
