"""M2-08: ranking + root-cause vs cascade (SPEC-002 §5).

Acceptance test copied from SPEC-002 §7:
    T5  A file with 22 failures produces <=22 findings, correctly deduped, ranked.
"""

from pathlib import Path

import pytest

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.models import Build, Failure

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CORPUS = Path(__file__).resolve().parent.parent / "error-reports"


def test_ranking_orders_by_phase_then_severity():
    # fetch_dartsim has do_fetch + two do_compile failures; fetch (earlier phase)
    # ranks ahead of compile.
    report = analyze([ingest.load_report(FIXTURES / "fetch_dartsim.json")])
    cats = [f.category for f in report.findings]
    assert cats[0] == "fetch"
    assert cats.index("fetch") < cats.index("compile")


def test_ranking_is_deterministic():
    a = [f.signature for f in analyze(ingest.load_reports([FIXTURES])).findings]
    b = [f.signature for f in analyze(ingest.load_reports([FIXTURES])).findings]
    assert a == b


def test_repeated_identical_error_marked_cascade_within_build():
    twin = [
        Failure(task="do_compile", recipe="foo", log="ERROR: boom", kind="task"),
        Failure(task="do_compile", recipe="foo", log="ERROR: boom", kind="task"),
    ]
    report = analyze([Build(failures=twin)])
    assert len(report.findings) == 2
    assert len({f.signature for f in report.findings}) == 1  # identical
    cascades = [f for f in report.findings if f.cascade_of]
    roots = [f for f in report.findings if not f.cascade_of]
    assert len(roots) == 1 and len(cascades) == 1
    assert cascades[0].cascade_of == roots[0].signature


def test_independent_failures_are_not_cascades():
    # two different errors in one build -> both roots, no false cascade
    build = Build(
        failures=[
            Failure(task="do_compile", recipe="a", log="ERROR: alpha", kind="task"),
            Failure(task="do_compile", recipe="b", log="ERROR: beta", kind="task"),
        ]
    )
    report = analyze([build])
    assert all(f.cascade_of is None for f in report.findings)


@pytest.mark.slow
@pytest.mark.skipif(not CORPUS.is_dir(), reason="corpus not present (gitignored)")
def test_t5_max_failure_report_bounded_and_ranked():
    biggest = max(ingest.load_reports([CORPUS]), key=lambda b: len(b.failures))
    assert len(biggest.failures) == 22
    report = analyze([biggest])
    assert len(report.findings) <= 22  # <=1 finding per failure, deduped
    # ranked: keys are non-decreasing
    from yocto_error_reports.analyze.rank import rank_key

    keys = [rank_key(f) for f in report.findings]
    assert keys == sorted(keys)
