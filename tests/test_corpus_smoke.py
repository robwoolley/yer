"""Corpus smoke harness — SPEC-001 T1: never crash on the real corpus.

    T1  Every file in `error-reports/` yields a `Build`; none raises.

`error-reports/` is the local ground-truth corpus and is **gitignored**, so this
test is marked `slow` and skips when the corpus is absent (e.g. in CI). It runs
locally, where the 77 real reports live.

Stub-tolerant until M1: `ingest` does not exist yet, so today the harness asserts
that every file *loads without raising* (JSON smoke). When `yocto_error_reports.
ingest` lands in M1 it is used automatically — replace the JSON fallback with the
real `ingest` call and add the T2 malformed-input assertion at that point.
"""

import importlib
import json
from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parent.parent / "error-reports"


def _corpus_files() -> list[Path]:
    return sorted(CORPUS.glob("*.txt")) if CORPUS.is_dir() else []


pytestmark = pytest.mark.slow


@pytest.mark.skipif(
    not _corpus_files(), reason="error-reports/ corpus not present (gitignored)"
)
def test_corpus_never_raises():
    files = _corpus_files()
    assert files, "expected corpus files once the directory exists"

    try:
        ingest = importlib.import_module("yocto_error_reports.ingest")
    except ModuleNotFoundError:
        ingest = None  # M0 stub mode — ingest arrives in M1.

    crashed: list[tuple[str, str]] = []
    for path in files:
        try:
            if ingest is not None and hasattr(ingest, "load_report"):
                # M1: SPEC-001 §1 — must return a Build and never raise.
                assert ingest.load_report(path) is not None
            else:
                # Stub: proves the raw report parses; upgraded to ingest in M1.
                json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — the whole point is to catch any crash
            crashed.append((path.name, repr(exc)))

    assert not crashed, f"corpus smoke crashed on {len(crashed)} file(s): {crashed[:5]}"
