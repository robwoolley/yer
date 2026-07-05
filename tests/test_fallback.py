"""M2-02: fallback rule + evidence extraction (SPEC-002 §2 fallback, §3 evidence).

Acceptance test copied from SPEC-002 §7:
    T6  Every corpus file yields >=1 finding (fallback guarantee).
"""

from pathlib import Path

import pytest

from yer import ingest, parse
from yer.analyze import analyze
from yer.analyze.evidence import MAX_EVIDENCE
from yer.analyze.rules import fallback
from yer.models import Failure

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CORPUS = Path(__file__).resolve().parent.parent / "error-reports"


def _extract(task, log, kind="task", **kw):
    failure = Failure(task=task, log=log, kind=kind, **kw)
    return fallback.FALLBACK_RULE.extract(failure, parse.parse_log(log))


def test_fallback_title_from_first_error_line():
    log = "NOTE: configuring\nDEBUG: x\nERROR: ninja: build stopped\nNOTE: done"
    f = _extract("do_compile", log)
    assert f.category == "unknown"
    assert f.severity == "error"
    assert f.title == "ninja: build stopped"


def test_fallback_uses_last_warning_when_no_error():
    f = _extract("do_compile", "NOTE: hi\nWARNING: deprecated\nWARNING: last warning")
    assert f.title == "last warning"
    assert f.severity == "warning"


def test_fallback_uses_task_message_when_no_error_or_warning():
    f = _extract("Nothing provides 'x'", "Nothing provides 'x'", kind="message", package="x")
    assert f.title == "Nothing provides 'x'"
    assert f.severity == "error"


def test_evidence_bounded_and_strips_note_debug():
    log = "\n".join(["NOTE: noise"] * 30 + ["DEBUG: more"] * 30 + ["ERROR: real error here"])
    f = _extract("do_compile", log)
    assert 1 <= len(f.evidence) <= MAX_EVIDENCE
    assert all(not e.startswith(("NOTE:", "DEBUG:")) for e in f.evidence)
    assert any("real error here" in e for e in f.evidence)


def test_evidence_keeps_noise_only_when_sole_content():
    f = _extract("do_compile", "NOTE: only note\nDEBUG: only debug")
    assert f.evidence  # not empty — noise is the only content


def test_t6_every_fixture_failure_yields_a_finding():
    for build in ingest.load_reports([FIXTURES]):
        assert len(analyze([build]).findings) >= 1


@pytest.mark.slow
@pytest.mark.skipif(not CORPUS.is_dir(), reason="corpus not present (gitignored)")
def test_t6_every_corpus_file_yields_a_finding():
    for build in ingest.load_reports([CORPUS]):
        assert len(analyze([build]).findings) >= 1
