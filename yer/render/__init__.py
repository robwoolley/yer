"""Render: project a `Report` into publishable artifacts (SPEC-004).

`json_out.py` — canonical deterministic `report.json`. `static.py` (M4-03) — a
self-contained HTML page. `sarif.py` (M5) — SARIF for code-scanning UIs. Render
may use Jinja2; the core stays stdlib-only.
"""
