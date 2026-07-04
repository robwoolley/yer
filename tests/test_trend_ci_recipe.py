"""M6-05: documented trend gating recipe + gitignored store (SPEC-006 §1, §4).

DoD: docs/ci.md shows the trend gating step and references the store; this test
asserts the documented trend workflow parses and references `yer trend` + the
store path; `.yer/` is gitignored.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CI_DOC = ROOT / "docs" / "ci.md"
GITIGNORE = ROOT / ".gitignore"


def _yaml_blocks(markdown: str) -> list[str]:
    return re.findall(r"```yaml\n(.*?)```", markdown, re.DOTALL)


def _trend_block(markdown: str) -> str:
    blocks = [b for b in _yaml_blocks(markdown) if "yer trend" in b]
    assert blocks, "docs/ci.md must contain a ```yaml block invoking `yer trend`"
    return blocks[0]


def test_trend_workflow_parses_and_references_store():
    block = _trend_block(CI_DOC.read_text(encoding="utf-8"))
    doc = yaml.safe_load(block)  # parses as valid YAML
    assert "jobs" in doc

    assert "yer trend" in block
    assert "--record" in block  # persists the run to the store
    assert "--fail-on-new" in block  # regression gate
    assert ".yer/trends.jsonl" in block  # references the store path
    # the store is carried between runs (cache/artifact persistence)
    assert "actions/cache" in block
    assert "path: .yer" in block


def test_store_is_gitignored():
    assert ".yer/" in GITIGNORE.read_text(encoding="utf-8")
