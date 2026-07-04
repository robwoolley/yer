"""Cross-run diff + signature history (SPEC-006 §2, §3).

Folds the run store into per-signature history, then classifies a new run's
findings against a baseline as **new / recurring / regressed**, plus the **fixed**
signatures that were in the baseline but are gone now. `Finding` stays
render-agnostic: statuses are returned as a signature-keyed mapping. Ordering is
deterministic given the store snapshot. Stdlib-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..models import Report
from .store import FindingRow, RunRecord


@dataclass
class SignatureHistory:
    """Folded history for one signature across all recorded runs (§2)."""

    signature: str = ""
    first_seen_run: str = ""
    first_seen_at: str = ""
    last_seen_run: str = ""
    last_seen_at: str = ""
    runs_present: int = 0
    total_occurrences: int = 0
    current_streak: int = 0


@dataclass
class FixedFinding:
    """A signature present in the baseline but absent from the current run (§3)."""

    signature: str = ""
    category: str = "unknown"
    severity: str = "error"
    recipe: str | None = None
    title: str = ""
    last_seen_run: str = ""
    last_seen_at: str = ""


@dataclass
class TrendDiff:
    """Current findings tagged vs a baseline, plus the fixed list (§3)."""

    baseline_run_id: str | None = None
    status: dict[str, str] = field(default_factory=dict)  # signature -> status
    new: list[str] = field(default_factory=list)
    recurring: list[str] = field(default_factory=list)
    regressed: list[str] = field(default_factory=list)
    fixed: list[FixedFinding] = field(default_factory=list)


def _run_signatures(run: RunRecord) -> set[str]:
    return {row.signature for row in run.findings}


def build_history(runs: list[RunRecord]) -> dict[str, SignatureHistory]:
    """Fold the (chronological) runs into per-signature history (§2)."""
    history: dict[str, SignatureHistory] = {}
    for run in runs:
        counts: dict[str, int] = {}
        for row in run.findings:
            counts[row.signature] = counts.get(row.signature, 0) + 1
        for signature, occurrences in counts.items():
            entry = history.get(signature)
            if entry is None:
                entry = SignatureHistory(
                    signature=signature,
                    first_seen_run=run.run_id,
                    first_seen_at=run.recorded_at,
                )
                history[signature] = entry
            entry.last_seen_run = run.run_id
            entry.last_seen_at = run.recorded_at
            entry.runs_present += 1
            entry.total_occurrences += occurrences
    # current_streak: consecutive most-recent runs containing the signature.
    run_sig_sets = [_run_signatures(run) for run in runs]
    for signature, entry in history.items():
        streak = 0
        for sig_set in reversed(run_sig_sets):
            if signature in sig_set:
                streak += 1
            else:
                break
        entry.current_streak = streak
    return history


def _baseline_index(runs: list[RunRecord], baseline: str | None) -> int | None:
    if not runs:
        return None
    if baseline is None:
        return len(runs) - 1  # the immediately previous run
    for index, run in enumerate(runs):
        if run.run_id == baseline:
            return index
    raise ValueError(f"unknown baseline run_id: {baseline}")


def diff(report: Report, runs: list[RunRecord], *, baseline: str | None = None) -> TrendDiff:
    """Classify `report`'s findings against a baseline run (§3)."""
    current = {f.signature for f in report.findings}
    index = _baseline_index(runs, baseline)

    if index is None:
        base_run: RunRecord | None = None
        base_sigs: set[str] = set()
        older_sigs: set[str] = set()
    else:
        base_run = runs[index]
        base_sigs = _run_signatures(base_run)
        older_sigs = set().union(*[_run_signatures(r) for r in runs[:index]]) if index else set()

    result = TrendDiff(baseline_run_id=base_run.run_id if base_run else None)
    for signature in current:
        if signature in base_sigs:
            status = "recurring"
        elif signature in older_sigs:
            status = "regressed"
        else:
            status = "new"
        result.status[signature] = status
        getattr(result, status).append(signature)

    # fixed: in the baseline, gone from the current run.
    if base_run is not None:
        base_rows: dict[str, FindingRow] = {}
        for row in base_run.findings:
            base_rows.setdefault(row.signature, row)
        for signature, row in base_rows.items():
            if signature not in current:
                result.fixed.append(
                    FixedFinding(
                        signature=signature,
                        category=row.category,
                        severity=row.severity,
                        recipe=row.recipe,
                        title=row.title,
                        last_seen_run=base_run.run_id,
                        last_seen_at=base_run.recorded_at,
                    )
                )

    result.new.sort()
    result.recurring.sort()
    result.regressed.sort()
    result.fixed.sort(key=lambda f: f.signature)
    return result


def to_trend_json(result: TrendDiff) -> str:
    """Deterministic, byte-stable JSON for the trend diff (§3, T6)."""
    document: dict[str, Any] = {
        "baseline_run_id": result.baseline_run_id,
        "new": result.new,
        "recurring": result.recurring,
        "regressed": result.regressed,
        "fixed": [
            {
                "signature": f.signature,
                "category": f.category,
                "severity": f.severity,
                "recipe": f.recipe,
                "title": f.title,
                "last_seen_run": f.last_seen_run,
                "last_seen_at": f.last_seen_at,
            }
            for f in result.fixed
        ],
        "counts": {
            "new": len(result.new),
            "recurring": len(result.recurring),
            "regressed": len(result.regressed),
            "fixed": len(result.fixed),
        },
    }
    return json.dumps(document, indent=2, sort_keys=True)
