---
description: Run the tool over the real error-reports corpus and report crashes / gaps
argument-hint: (optional) extra yer flags
---

Verify the current build of the tool against the **real sample corpus** in
`error-reports/` (the crash-safety gate — SPEC-001 T1 and SPEC-002 T6).

Do **not** fix anything in this command — this is a report-only health check.

1. Determine how to invoke the tool (installed `yer`, or
   `python -m yocto_error_reports` if not yet installed). If no runnable entry
   point exists yet, say so and stop.
2. Run analysis over **every** file in `error-reports/*.txt` (pass through any
   extra flags in `$ARGUMENTS`). Capture failures per file.
3. Report, as a concise table:
   - **Crashes / exceptions** — file + error (this is a hard failure; SPEC-001
     requires a parse *finding*, never a raised exception).
   - **Files with zero findings** — violates the SPEC-002 fallback guarantee.
   - **Miscategorized** — spot-check against @docs/data-format.md taxonomy
     (e.g. a Qt6 NOT FOUND under `do_compile` should be category `configure`).
   - **Total wall-clock time** — flag if the full corpus exceeds a few seconds
     (NFR2).
4. End with a verdict: PASS (no crashes, every file ≥1 finding, within budget)
   or FAIL with the specific offending files.

If you find issues, list them as candidate follow-up tasks — do not implement.
