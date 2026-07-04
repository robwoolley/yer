"""Cross-run trend history (SPEC-006).

Persist each run's findings to a local, privacy-safe store keyed by the stable
`signature`, then diff a new run against history (new/recurring/regressed/fixed).
Stdlib-only; no network. `store.py` lands in M6-01, `diff.py` in M6-02.
"""
