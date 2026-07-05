"""M7-01: PyPI-ready metadata + a correct distribution (SPEC-007 §2, §3, §7).

Acceptance tests copied from SPEC-007 §8:
    T1  `python -m build` produces an sdist and a wheel; the wheel contains
        `yer/render/templates/report.html.j2` and declares the `yer`
        console-script entry point.
    T6  Neither the sdist nor the wheel contains any corpus report
        (`error_report_*.txt`), a `.yer/` trend store, or `redactions.local`.

Building is heavier than a unit test, so these are marked `slow` (they still run
in CI, which is not deselected). The `built_dist` fixture (in conftest.py) builds
the sdist + wheel once per session.
"""

import tarfile
import zipfile

import pytest

pytestmark = pytest.mark.slow


def _is_host_data(name: str) -> bool:
    base = name.rsplit("/", 1)[-1]
    return (
        base.startswith("error_report_")
        or base == "redactions.local"
        or "/.yer/" in name
        or name.endswith("/error-reports")
        or "/error-reports/" in name
    )


def test_t1_build_produces_wheel_with_template_and_entry_point(built_dist):
    wheel, sdist = built_dist
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


def test_t6_no_host_data_in_dists(built_dist):
    wheel, sdist = built_dist
    with zipfile.ZipFile(wheel) as zf:
        wheel_names = zf.namelist()
    with tarfile.open(sdist) as tf:
        sdist_names = tf.getnames()
    wheel_leaks = [n for n in wheel_names if _is_host_data(n)]
    sdist_leaks = [n for n in sdist_names if _is_host_data(n)]
    assert not wheel_leaks, f"host data in wheel: {wheel_leaks}"
    assert not sdist_leaks, f"host data in sdist: {sdist_leaks}"


def test_metadata_is_pypi_ready(built_dist):
    # §2: complete project URLs + a release-appropriate Development Status.
    wheel, _ = built_dist
    names = zipfile.ZipFile(wheel).namelist()
    metadata_name = next(n for n in names if n.endswith(".dist-info/METADATA"))
    metadata = zipfile.ZipFile(wheel).read(metadata_name).decode()
    assert "Development Status :: 3 - Alpha" in metadata
    for label in ("Homepage", "Repository", "Changelog", "Issues"):
        assert f"Project-URL: {label}," in metadata, f"missing project URL: {label}"
