"""M5-05: verify artifact publishing on a sample pipeline (roadmap M5).

Runs the documented CI path — `yer report … --html <dir> --format sarif -o
results.sarif` — and asserts all three publishable artifacts are produced,
self-contained, shaped for code-scanning, and re-runnable to byte-identical
output. The fixture-based checks run in CI; a `slow` check exercises the whole
gitignored corpus locally.

DoD: the smoke test produces and validates index.html + report.json +
results.sarif; the corpus run does not crash.
"""

import json
import re
from pathlib import Path

import pytest

from yer.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CORPUS = Path(__file__).resolve().parent.parent / "error-reports"

_ASSET_URL = re.compile(r'(?:href|src)\s*=\s*["\']https?://', re.IGNORECASE)


def _run_pipeline(inputs: str, dest: Path) -> int:
    sarif = dest / "results.sarif"
    return main(
        ["report", inputs, "--html", str(dest), "--format", "sarif", "-o", str(sarif)]
    )


def test_pipeline_produces_all_three_artifacts(tmp_path):
    out = tmp_path / "out"
    code = _run_pipeline(str(FIXTURES), out)
    assert code == 1  # fixtures have error findings -> gate fails, artifacts still written
    assert (out / "index.html").is_file()
    assert (out / "report.json").is_file()
    assert (out / "results.sarif").is_file()

    # index.html is self-contained (no external asset requests)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert _ASSET_URL.search(html) is None

    # report.json is the canonical schema
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == "1.0"
    assert report["findings"]

    # results.sarif is shaped for code-scanning upload
    sarif = json.loads((out / "results.sarif").read_text(encoding="utf-8"))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"]


def test_artifacts_byte_identical_across_runs(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _run_pipeline(str(FIXTURES), a)
    _run_pipeline(str(FIXTURES), b)
    for name in ("index.html", "report.json", "results.sarif"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), f"{name} not deterministic"


@pytest.mark.slow
@pytest.mark.skipif(
    not (CORPUS.is_dir() and any(CORPUS.glob("*.txt"))),
    reason="error-reports/ corpus not present (gitignored)",
)
def test_pipeline_over_corpus_does_not_crash(tmp_path):
    out = tmp_path / "corpus"
    code = _run_pipeline(str(CORPUS), out)
    assert code in (0, 1)  # findings gate, never a tool error
    assert (out / "index.html").is_file()
    assert (out / "report.json").is_file()
    assert (out / "results.sarif").is_file()
    sarif = json.loads((out / "results.sarif").read_text(encoding="utf-8"))
    assert sarif["runs"][0]["results"]  # the corpus has findings
