"""M6-02: cross-run diff + signature history (SPEC-006 §2, §3).

Acceptance tests copied from SPEC-006 §6:
    T1  Record run A then run B; diff B vs A: a signature only in B -> new;
        in both -> recurring; only in A -> fixed.
    T5  A signature present in run 1, absent in run 2, present in run 3 ->
        status regressed (not new) when the baseline is run 2.
    T6  The diff document is deterministic: the same (inputs, store snapshot)
        yields byte-identical trend JSON across runs.
"""

from pathlib import Path

from yocto_error_reports.models import Finding, Report
from yocto_error_reports.trends.diff import build_history, diff, to_trend_json
from yocto_error_reports.trends.store import load_runs, record_run


def _report(*signatures: str) -> Report:
    return Report(
        findings=[
            Finding(
                signature=sig,
                category="compile",
                severity="error",
                title=f"title {sig}",
                recipe="demo",
            )
            for sig in signatures
        ]
    )


def _record(store: Path, *signatures: str, ts: str) -> None:
    record_run(_report(*signatures), store_path=store, tool_version="1.0.0", recorded_at=ts)


def test_t1_new_recurring_fixed(tmp_path):
    store = tmp_path / "trends.jsonl"
    _record(store, "sig-a", "sig-b", ts="2026-07-01T00:00:00Z")  # run A (baseline)
    result = diff(_report("sig-b", "sig-c"), load_runs(store))  # run B
    assert result.status["sig-c"] == "new"
    assert result.status["sig-b"] == "recurring"
    assert "sig-a" not in result.status  # fixed findings aren't in the current run
    assert [f.signature for f in result.fixed] == ["sig-a"]


def test_t5_regressed_not_new(tmp_path):
    store = tmp_path / "trends.jsonl"
    _record(store, "sig-x", ts="2026-07-01T00:00:00Z")  # run 1: has x
    _record(store, "sig-y", ts="2026-07-02T00:00:00Z")  # run 2: no x  (baseline)
    result = diff(_report("sig-x"), load_runs(store))  # run 3: x is back
    assert result.status["sig-x"] == "regressed"


def test_baseline_override_selects_earlier_run(tmp_path):
    store = tmp_path / "trends.jsonl"
    _record(store, "sig-x", ts="2026-07-01T00:00:00Z")  # run 1 (id known)
    _record(store, "sig-y", ts="2026-07-02T00:00:00Z")  # run 2
    runs = load_runs(store)
    run1_id = runs[0].run_id
    # against run 1, x is recurring (present in both), not regressed
    result = diff(_report("sig-x"), runs, baseline=run1_id)
    assert result.status["sig-x"] == "recurring"


def test_t6_trend_json_is_deterministic(tmp_path):
    store = tmp_path / "trends.jsonl"
    _record(store, "sig-a", "sig-b", ts="2026-07-01T00:00:00Z")
    runs = load_runs(store)
    current = _report("sig-b", "sig-c")
    assert to_trend_json(diff(current, runs)) == to_trend_json(diff(current, runs))


def test_signature_history_fold(tmp_path):
    store = tmp_path / "trends.jsonl"
    _record(store, "sig-x", ts="2026-07-01T00:00:00Z")  # run 1
    _record(store, "sig-y", ts="2026-07-02T00:00:00Z")  # run 2 (streak break for x)
    _record(store, "sig-x", ts="2026-07-03T00:00:00Z")  # run 3
    history = build_history(load_runs(store))
    hx = history["sig-x"]
    assert hx.runs_present == 2
    assert hx.total_occurrences == 2
    assert hx.current_streak == 1  # only the most recent run has x
    assert hx.first_seen_at == "2026-07-01T00:00:00Z"
    assert hx.last_seen_at == "2026-07-03T00:00:00Z"


def test_empty_history_is_all_new():
    result = diff(_report("sig-a"), [])
    assert result.status["sig-a"] == "new"
    assert result.baseline_run_id is None
    assert result.fixed == []
