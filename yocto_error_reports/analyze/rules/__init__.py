"""Rule modules. Importing each one registers its rule(s) (SPEC-002 §2).

The analyzer orchestrator imports this package so every rule self-registers; new
categories are added here without touching `analyze/__init__.py`.
"""

from . import fallback  # noqa: F401  — import side effect: registers the fallback
