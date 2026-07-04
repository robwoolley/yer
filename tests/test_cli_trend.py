"""M6-03: `yer trend` CLI subcommand (SPEC-006 §4; SPEC-003 §1).

Acceptance test copied from SPEC-006 §6:
    T4  `yer trend <inputs> --record` writes a record; a later run with a
        brand-new failure and --fail-on-new exits 1; a run with only recurring
        findings and --fail-on-new exits 0.
"""

import json
from pathlib import Path

import pytest

from yocto_error_reports.cli import main
from yocto_error_reports.trends.store import load_runs

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONFIGURE = str(FIXTURES / "configure_gz-gui9.json")
COMPILE = str(FIXTURES / "compile_nanoflann.json")


def test_t4_record_then_fail_on_new(tmp_path):
    store = str(tmp_path / "trends.jsonl")

    # 1) record a baseline run — no gating flag, so exit 0
    assert main(["trend", CONFIGURE, "--store", store, "--record"]) == 0
    assert len(load_runs(store)) == 1

    # 2) same input, --fail-on-new: only recurring findings -> exit 0
    assert main(["trend", CONFIGURE, "--store", store, "--fail-on-new"]) == 0

    # 3) a different report (brand-new signatures) + --fail-on-new -> exit 1
    assert main(["trend", COMPILE, "--store", store, "--fail-on-new"]) == 1


def test_record_is_explicit(tmp_path):
    store = tmp_path / "trends.jsonl"
    # a dry run (no --record) must not create/append to the store
    assert main(["trend", CONFIGURE, "--store", str(store)]) == 0
    assert not store.exists()


def test_trend_json_output(tmp_path, capsys):
    store = str(tmp_path / "trends.jsonl")
    main(["trend", CONFIGURE, "--store", store, "--record"])
    capsys.readouterr()
    main(["trend", COMPILE, "--store", store, "--format", "json"])
    doc = json.loads(capsys.readouterr().out)
    assert doc["new"]  # compile signatures are new vs the configure baseline
    assert "counts" in doc


def test_trend_no_inputs_exits_2(tmp_path, capsys):
    code = main(["trend", str(FIXTURES / "nope.json"), "--store", str(tmp_path / "s.jsonl")])
    assert code == 2
    assert capsys.readouterr().err


def test_unknown_baseline_exits_2(tmp_path, capsys):
    store = str(tmp_path / "trends.jsonl")
    main(["trend", CONFIGURE, "--store", store, "--record"])
    capsys.readouterr()
    code = main(["trend", CONFIGURE, "--store", store, "--baseline", "sha1:nope"])
    assert code == 2
    assert capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--record"])
def test_first_run_all_new_is_not_gated_without_flag(tmp_path, flag):
    # first ever run: everything is new, but without --fail-on-new the exit is 0
    store = str(tmp_path / "trends.jsonl")
    assert main(["trend", CONFIGURE, "--store", store, flag]) == 0
