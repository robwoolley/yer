---
description: Generate the next milestone's task list from its spec's acceptance tests
argument-hint: (optional) milestone number, e.g. 1
---

Generate the next milestone task file, following @docs/roadmap.md sequencing and
the task conventions in @docs/spec-driven-workflow.md.

1. **Determine the milestone.** If `$ARGUMENTS` names a number, use it.
   Otherwise, find the highest existing `tasks/milestone-*.md`, confirm its
   tasks are all checked (if not, warn me and stop), and target the next number.
2. **Gate check.** Confirm the previous milestone's roadmap **exit criteria**
   are met (tests green, corpus smoke passes). If not, list what's missing and
   stop.
3. **Derive tasks** for the target milestone from @docs/roadmap.md and the
   relevant spec's **Acceptance tests** section(s). Each task must:
   - Use id format `M<n>-<nn>`, ordered by dependency.
   - Name a `Spec:` reference and a `DoD:` (definition of done) tied to a
     concrete acceptance test.
   - Be small enough to complete and verify in one `/task` run.
4. **Write** `tasks/milestone-<n>.md` using the same layout as
   @tasks/milestone-0.md (goal header, roadmap/DoD links, checkbox list,
   "Next milestone" footer).
5. Do **not** implement anything — this command only produces the task list.

Report the new file path and the number of tasks created.
