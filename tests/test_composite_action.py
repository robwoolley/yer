"""M7-06: reusable composite GitHub Action (SPEC-007 §6).

DoD: action.yml wraps the docs/ci.md recipe (yer report + yer analyze
--format sarif + artifact/SARIF upload) so consumers write one `uses:` line; a
test parses it and asserts those references; documented in docs/ci.md.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ACTION = ROOT / "action.yml"
CI_DOC = ROOT / "docs" / "ci.md"


def _action():
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))


def test_action_exists():
    assert ACTION.is_file(), "expected action.yml at the repo root"


def test_is_composite_with_name_and_description():
    doc = _action()
    assert doc["name"]
    assert doc["description"]
    assert doc["runs"]["using"] == "composite"


def test_wraps_the_ci_recipe():
    text = ACTION.read_text(encoding="utf-8")
    assert "yer report" in text
    assert "yer analyze" in text and "--format sarif" in text
    assert "actions/upload-artifact" in text
    assert "upload-sarif" in text


def test_run_steps_declare_a_shell():
    # every `run` step in a composite action MUST set `shell`
    for step in _action()["runs"]["steps"]:
        if "run" in step:
            assert step.get("shell"), f"run step missing shell: {step}"


def test_has_inputs_with_defaults():
    inputs = _action()["inputs"]
    for name in ("reports", "html-dir", "sarif-file", "fail-on"):
        assert name in inputs, f"missing input: {name}"
        assert "default" in inputs[name]


def test_documented_in_ci_md():
    assert "uses: robwoolley/yer@" in CI_DOC.read_text(encoding="utf-8")
