---
description: Work a single spec-driven task through the full development loop
argument-hint: <task-id, e.g. M0-01>
---

You are executing task **$ARGUMENTS** under this project's spec-driven workflow.

Follow the loop in @docs/spec-driven-workflow.md exactly. Do not skip steps and
do not go beyond the cited spec.

1. **Locate the task.** Find `$ARGUMENTS` in the relevant `tasks/milestone-*.md`
   file. Read its `Spec:` reference and `DoD:` (definition of done). If the id
   doesn't exist, stop and say so.
2. **Read the cited spec section** in `docs/specs/`, plus @CLAUDE.md conventions.
3. **Confirm ground truth.** Verify any input-format assumptions against real
   files in `error-reports/` and @docs/data-format.md. Never invent format
   details. Ensure a matching `tests/fixtures/` sample exists (add one,
   anonymized, if needed).
4. **Write the acceptance test first**, copied from the spec's "Acceptance
   tests" section (golden files where applicable) — not paraphrased.
5. **Implement** the smallest change that satisfies the spec section. Keep core
   `parse`/`analyze`/`models` stdlib-only; keep CLI/render concerns out of them.
6. **Run** the new test and the corpus smoke check — the tool must not crash on
   any file in `error-reports/`.
7. **Update docs** only if behavior changed: edit the SPEC first (add a dated
   note under a `## Changelog` heading), then `data-format.md` if the input
   understanding changed, then code. State the rationale.
8. **Check the box** for `$ARGUMENTS` in the milestone file.

If the spec is wrong or underspecified, follow the **Spec change protocol** in
the workflow doc — update the spec before the code.

Finish with a short summary: what changed, which tests now pass, and any spec
edits you made.
