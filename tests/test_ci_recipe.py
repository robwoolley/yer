"""M5-04: documented exit-code contract + GitHub Actions recipe (SPEC-003 §4).

DoD: docs/ci.md contains a copy-pasteable workflow and the exit-code table; this
test asserts the documented workflow YAML parses and references the artifacts
(HTML report + SARIF upload).
"""

import re
from pathlib import Path

import yaml

CI_DOC = Path(__file__).resolve().parent.parent / "docs" / "ci.md"


def _first_yaml_block(markdown: str) -> str:
    match = re.search(r"```yaml\n(.*?)```", markdown, re.DOTALL)
    assert match, "docs/ci.md must contain a ```yaml workflow block"
    return match.group(1)


def test_ci_doc_exists():
    assert CI_DOC.is_file(), "expected docs/ci.md"


def test_exit_code_table_documented():
    text = CI_DOC.read_text(encoding="utf-8")
    # the 0/1/2 contract (SPEC-003 §4) is spelled out
    assert "| `0`  |" in text
    assert "| `1`  |" in text
    assert "| `2`  |" in text


def test_workflow_yaml_parses_and_references_artifacts():
    block = _first_yaml_block(CI_DOC.read_text(encoding="utf-8"))
    doc = yaml.safe_load(block)  # parses as valid YAML
    assert "jobs" in doc  # a real workflow (note: `on:` parses as the bool key True)

    # references the yer commands and the published artifacts
    assert "yer report" in block
    assert "--html out/" in block
    assert "yer analyze" in block and "--format sarif" in block
    assert "results.sarif" in block
    # publishes both the HTML/JSON artifact and the SARIF code-scanning upload
    assert "actions/upload-artifact" in block
    assert "upload-sarif" in block
