"""M2-04: patch rule (SPEC-002 §2).

Acceptance test copied from SPEC-002 §7:
    T4  ogre-next do_patch -> patch, file = OgreMathlibNEON.h, hunk line 601.
"""

from pathlib import Path

from yer import ingest, parse
from yer.analyze import analyze
from yer.analyze.rules import patch

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _failure(fixture):
    build = ingest.load_report(FIXTURES / fixture)
    return build, build.failures[0], parse.parse_log(build.failures[0].log)


def test_t4_patch_ogre_next_file_and_hunk_line():
    _, failure, lines = _failure("patch_ogre-next.json")
    assert patch.PATCH_RULE.match(failure, lines)
    finding = patch.PATCH_RULE.extract(failure, lines)
    assert finding.category == "patch"
    assert finding.file == "OgreMathlibNEON.h"  # first failing file (basename)
    assert finding.line == 601  # first "Hunk #1 FAILED at 601"
    assert finding.recipe == "ogre-next"
    assert "0001-Fixed-compile-error-2.3.3.patch" in finding.title


def test_patch_integration_single_finding():
    build, *_ = _failure("patch_ogre-next.json")
    findings = analyze([build]).findings
    assert len(findings) == 1
    assert findings[0].category == "patch"
    assert findings[0].file == "OgreMathlibNEON.h"
    assert findings[0].line == 601


def test_patch_rule_does_not_match_compile():
    _, failure, lines = _failure("compile_nanoflann.json")
    assert not patch.PATCH_RULE.match(failure, lines)
