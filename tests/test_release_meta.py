"""M7-01: PyPI-ready metadata + a correct distribution (SPEC-007 §2, §3, §7).

Acceptance tests copied from SPEC-007 §8:
    T1  `python -m build` produces an sdist and a wheel; the wheel contains
        `yer/render/templates/report.html.j2` and declares the `yer`
        console-script entry point.
    T6  Neither the sdist nor the wheel contains any corpus report
        (`error_report_*.txt`), a `.yer/` trend store, or `redactions.local`.

Building is heavier than a unit test, so these are marked `slow` (they still run
in CI, which is not deselected). The build uses `--no-isolation` when the
backend (hatchling) is importable — the fast, hermetic path CI takes via the dev
extras — and otherwise falls back to an isolated build.
"""

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def dist(tmp_path_factory):
    """Build sdist + wheel once; return (wheel_path, sdist_path)."""
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


def _is_host_data(name: str) -> bool:
    base = name.rsplit("/", 1)[-1]
    return (
        base.startswith("error_report_")
        or base == "redactions.local"
        or "/.yer/" in name
        or name.endswith("/error-reports")
        or "/error-reports/" in name
    )


def test_t1_build_produces_wheel_with_template_and_entry_point(dist):
    wheel, sdist = dist
    assert wheel.name.startswith("yer-") and wheel.name.endswith(".whl")
    assert sdist.name.startswith("yer-") and sdist.name.endswith(".tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    # the Jinja2 template ships in the wheel
    assert "yer/render/templates/report.html.j2" in names
    # the `yer` console-script entry point is declared
    entry_points = [n for n in names if n.endswith("entry_points.txt")]
    assert entry_points, "wheel is missing entry_points.txt"
    text = zipfile.ZipFile(wheel).read(entry_points[0]).decode()
    assert "yer = yer.cli:main" in text


def test_t6_no_host_data_in_dists(dist):
    wheel, sdist = dist
    with zipfile.ZipFile(wheel) as zf:
        wheel_names = zf.namelist()
    with tarfile.open(sdist) as tf:
        sdist_names = tf.getnames()
    wheel_leaks = [n for n in wheel_names if _is_host_data(n)]
    sdist_leaks = [n for n in sdist_names if _is_host_data(n)]
    assert not wheel_leaks, f"host data in wheel: {wheel_leaks}"
    assert not sdist_leaks, f"host data in sdist: {sdist_leaks}"


def test_metadata_is_pypi_ready(dist):
    # §2: complete project URLs + a release-appropriate Development Status.
    wheel, _ = dist
    names = zipfile.ZipFile(wheel).namelist()
    metadata_name = next(n for n in names if n.endswith(".dist-info/METADATA"))
    metadata = zipfile.ZipFile(wheel).read(metadata_name).decode()
    assert "Development Status :: 3 - Alpha" in metadata
    for label in ("Homepage", "Repository", "Changelog", "Issues"):
        assert f"Project-URL: {label}," in metadata, f"missing project URL: {label}"
