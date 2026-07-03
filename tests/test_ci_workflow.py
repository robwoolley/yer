"""Guard for M0-04: the CI workflow runs lint + type + tests on the 3.11/3.12 matrix.

Roadmap M0 exit criteria require CI to run lint, type, and tests. This test is
dependency-free (no PyYAML) so it holds in CI itself; it pins the pieces the
roadmap names rather than the full YAML structure.
"""

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


def test_workflow_exists():
    assert WORKFLOW.is_file(), "expected .github/workflows/ci.yml"


def test_workflow_matrix_and_steps():
    text = WORKFLOW.read_text(encoding="utf-8")
    # Python version matrix (roadmap M0: 3.11/3.12).
    assert "3.11" in text and "3.12" in text
    # lint + type + tests are all invoked.
    assert "ruff check" in text
    assert "mypy" in text
    assert "pytest" in text
