"""M7-02: validate the distribution (SPEC-007 §3, §2).

Acceptance tests copied from SPEC-007 §8:
    T2  Installing the built wheel into a clean virtualenv exposes
        `yer --version` equal to `__version__`, and `yer analyze <fixture>` runs
        end-to-end (proves the template and entry point ship correctly).
    T3  `twine check dist/*` passes (valid metadata; README renders as the long
        description).

Marked `slow`: both build (via the shared fixture) and, for T2, create a
virtualenv and install the wheel.
"""

import subprocess
import sys
import venv
from pathlib import Path

import pytest

import yer

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "configure_gz-gui9.json"

pytestmark = pytest.mark.slow


def test_t3_twine_check_passes(built_dist):
    pytest.importorskip("twine", reason="pip install '.[dev]' to run twine check")
    wheel, sdist = built_dist
    proc = subprocess.run(
        [sys.executable, "-m", "twine", "check", str(wheel), str(sdist)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"twine check failed:\n{proc.stdout}\n{proc.stderr}"
    assert "PASSED" in proc.stdout
    assert "warning" not in proc.stdout.lower()  # README renders cleanly


def test_t2_clean_install_runs(built_dist, tmp_path):
    wheel, _ = built_dist
    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    pip = bindir / "pip"
    yer_cmd = bindir / "yer"

    install = subprocess.run(
        [str(pip), "install", str(wheel)], capture_output=True, text=True
    )
    assert install.returncode == 0, f"install failed:\n{install.stdout}\n{install.stderr}"

    # entry point + version match the source
    version = subprocess.run([str(yer_cmd), "--version"], capture_output=True, text=True)
    assert version.returncode == 0
    assert yer.__version__ in version.stdout

    # analyze runs end-to-end from the installed wheel (exit 1 = findings present)
    analyze = subprocess.run(
        [str(yer_cmd), "analyze", str(FIXTURE), "--no-color"], capture_output=True, text=True
    )
    assert analyze.returncode == 1
    assert "configure" in analyze.stdout

    # report exercises the packaged Jinja2 template end-to-end
    out_dir = tmp_path / "out"
    report = subprocess.run(
        [str(yer_cmd), "report", str(FIXTURE), "--html", str(out_dir)],
        capture_output=True,
        text=True,
    )
    assert report.returncode == 1
    assert (out_dir / "index.html").is_file()
    assert (out_dir / "report.json").is_file()
