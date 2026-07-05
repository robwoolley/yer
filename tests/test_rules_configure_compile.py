"""M2-06: configure + compile rules, content over task name (SPEC-002 §2).

Acceptance test copied from SPEC-002 §7:
    T3  gz-sim-vendor do_compile -> category configure (Qt6 NOT FOUND), not
        compile — configure-style signals win even under do_compile.
Plus T1 across the compile/configure category fixtures.
"""

from pathlib import Path

from yer import ingest, parse
from yer.analyze import analyze
from yer.analyze.rules import compile as compile_rule
from yer.analyze.rules import configure

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _failure(fixture, idx=0):
    build = ingest.load_report(FIXTURES / fixture)
    failure = build.failures[idx]
    return build, failure, parse.parse_log(failure.log)


def test_t3_gz_sim_vendor_compile_classifies_as_configure():
    build, *_ = _failure("compile_gz-sim-vendor.json")
    cats = [f.category for f in analyze([build]).findings]
    assert "configure" in cats  # the do_compile failure is really configure
    assert "compile" not in cats  # NOT compile
    cfg = next(f for f in analyze([build]).findings if f.category == "configure")
    assert "Qt6" in cfg.title


def test_configure_gz_gui9():
    build, *_ = _failure("configure_gz-gui9.json")
    findings = analyze([build]).findings
    assert len(findings) == 1
    assert findings[0].category == "configure"
    assert "Qt5" in findings[0].title
    assert findings[0].file == "CMakeLists.txt"
    assert findings[0].line and findings[0].line > 0


def test_compile_nanoflann_is_real_compile():
    build, *_ = _failure("compile_nanoflann.json")
    findings = analyze([build]).findings
    assert len(findings) == 1
    assert findings[0].category == "compile"
    assert "error:" in findings[0].title


def test_compile_rule_defers_to_configure_signals():
    # gz-sim-vendor do_compile log has `ninja: build stopped` AND CMake errors:
    # configure matches, compile stands down.
    _, failure, lines = _failure("compile_gz-sim-vendor.json", idx=1)
    assert configure.CONFIGURE_RULE.match(failure, lines)
    assert not compile_rule.COMPILE_RULE.match(failure, lines)
