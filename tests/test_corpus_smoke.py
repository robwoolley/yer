"""Corpus smoke harness — SPEC-001 T1 (never crash) and §3 (parse within budget).

    T1  Every file in `error-reports/` yields a `Build`; none raises.
    §3  Streaming ingest + parse of the whole corpus (incl. the ~2 MB log) stays
        within the few-second budget.

`error-reports/` is the local ground-truth corpus and is **gitignored**, so these
tests are marked `slow` and skip when the corpus is absent (e.g. in CI). They run
locally over the 77 real reports.
"""

import time
from pathlib import Path

import pytest

from yocto_error_reports import ingest, parse
from yocto_error_reports.models import Build

CORPUS = Path(__file__).resolve().parent.parent / "error-reports"
CORPUS_BUDGET_S = 5.0
LARGE_LOG_BUDGET_S = 1.0


def _corpus_files() -> list[Path]:
    return sorted(CORPUS.glob("*.txt")) if CORPUS.is_dir() else []


pytestmark = pytest.mark.slow
_skip_if_absent = pytest.mark.skipif(
    not _corpus_files(), reason="error-reports/ corpus not present (gitignored)"
)


@_skip_if_absent
def test_corpus_ingests_without_raising():
    files = _corpus_files()
    crashed: list[tuple[str, str]] = []
    builds: list[Build] = []
    for path in files:
        try:
            build = ingest.load_report(path)  # SPEC-001 §1: never raises
        except Exception as exc:  # noqa: BLE001 — the point is to catch any crash
            crashed.append((path.name, repr(exc)))
            continue
        assert isinstance(build, Build)
        builds.append(build)
    assert not crashed, f"ingest crashed on {len(crashed)} file(s): {crashed[:5]}"
    assert len(builds) == len(files)


@_skip_if_absent
def test_corpus_parses_within_budget():
    start = time.perf_counter()
    builds = ingest.load_reports([CORPUS])
    logs = [f.log for b in builds for f in b.failures]
    for log in logs:
        parse.parse_log(log)
    elapsed = time.perf_counter() - start
    assert elapsed < CORPUS_BUDGET_S, f"corpus ingest+parse took {elapsed:.2f}s"

    # the single largest log (the ~2 MB report) parses within budget on its own
    biggest = max(logs, key=len)
    start = time.perf_counter()
    parse.parse_log(biggest)
    solo = time.perf_counter() - start
    assert solo < LARGE_LOG_BUDGET_S, f"{len(biggest)} B log took {solo:.2f}s"
