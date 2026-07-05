"""M1-01: ingest one report into a defensive `Build` (SPEC-001 §1).

Acceptance tests copied from SPEC-001 §4:
    T3  task="Nothing provides '…'"  -> kind="message".
    T4  A failure missing `recipe` parses (recipe None).
Plus the M1-01 DoD: every committed fixture loads to a `Build`.
"""

from pathlib import Path

import pytest

from yer import ingest
from yer.models import Build

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ALL_FIXTURES = sorted(FIXTURES.glob("*.json"))
DEPENDENCY = FIXTURES / "dependency_moveit.json"


@pytest.mark.parametrize("path", ALL_FIXTURES, ids=lambda p: p.name)
def test_fixture_loads_to_build(path):
    build = ingest.load_report(path)
    assert isinstance(build, Build)
    assert isinstance(build.failures, list)
    assert build.source_path == str(path)
    # raw preserves the original JSON (unknown keys like local_conf survive there).
    assert isinstance(build.raw, dict)


def test_t3_nothing_provides_is_message_kind():
    build = ingest.load_report(DEPENDENCY)
    failure = build.failures[0]
    assert failure.task.startswith("Nothing provides")
    assert failure.kind == "message"


def test_t4_missing_recipe_is_none():
    build = ingest.load_report(DEPENDENCY)
    assert build.failures[0].recipe is None


def test_do_task_is_task_kind_and_metadata_mapped():
    build = ingest.load_report(FIXTURES / "configure_gz-gui9.json")
    failure = build.failures[0]
    assert failure.task == "do_configure"
    assert failure.kind == "task"
    assert failure.recipe == "gz-gui9"
    # top-level metadata is mapped onto the Build
    assert build.machine == "raspberrypi5"
    assert build.distro == "ros2"
