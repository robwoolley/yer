"""Provisional failure inventory (M1-08 — roadmap M1 demoable outcome).

Pure counting over `Build[]` plus a minimal text rendering. This is a thin demo
that the M2 `analyze` CLI (SPEC-003) supersedes; its `category` is derived from
the **task name only** (data-format §"Failure taxonomy"), *not* the content-aware
analyzer (which reclassifies e.g. a `do_compile` that is really a configure
failure). Stdlib-only; no `ingest`/`parse` internals leak in here.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from .models import Build, Failure

_TASK_CATEGORY = {
    "do_compile": "compile",
    "do_configure": "configure",
    "do_patch": "patch",
    "do_package_qa": "qa",
    "do_fetch": "fetch",
}


def task_category(failure: Failure) -> str:
    """Map a failure to a category by task name (data-format taxonomy)."""
    task = failure.task or ""
    if failure.kind == "message" or task.startswith(("Nothing provides", "No provider")):
        return "dependency"
    return _TASK_CATEGORY.get(task, "other")


@dataclass(frozen=True)
class Inventory:
    reports: int
    failures: int
    by_category: dict[str, int]
    by_task: dict[str, int]
    by_recipe: dict[str, int]


def _ordered(counter: Counter[str]) -> dict[str, int]:
    # deterministic: descending count, then name (NFR3)
    return dict(sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])))


def inventory(builds: Iterable[Build]) -> Inventory:
    builds = list(builds)
    by_category: Counter[str] = Counter()
    by_task: Counter[str] = Counter()
    by_recipe: Counter[str] = Counter()
    failures = 0
    for build in builds:
        for failure in build.failures:
            failures += 1
            by_category[task_category(failure)] += 1
            task = failure.task if failure.kind == "task" and failure.task else "<message>"
            by_task[task] += 1
            by_recipe[failure.recipe or failure.package or "<unknown>"] += 1
    return Inventory(
        reports=len(builds),
        failures=failures,
        by_category=_ordered(by_category),
        by_task=_ordered(by_task),
        by_recipe=_ordered(by_recipe),
    )


def format_inventory(inv: Inventory, *, top_recipes: int = 10) -> str:
    """Render an `Inventory` as compact, deterministic text."""
    lines = [f"{inv.reports} report(s), {inv.failures} failure(s)", "", "By category:"]
    lines += [f"  {count:5d}  {name}" for name, count in inv.by_category.items()]
    lines += ["", f"Top recipes (of {len(inv.by_recipe)}):"]
    lines += [
        f"  {count:5d}  {name}"
        for name, count in list(inv.by_recipe.items())[:top_recipes]
    ]
    return "\n".join(lines)
