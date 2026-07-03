---
description: Scaffold a new numbered component SPEC from the house template
argument-hint: <short-name, e.g. trend-store>
---

Create a new component specification for **$ARGUMENTS**, consistent with the
existing specs in `docs/specs/`.

1. **Pick the next id.** List `docs/specs/SPEC-*.md`, find the highest number,
   and use the next one (zero-padded, e.g. `SPEC-006`). **Never reuse a
   number** — supersede instead of renumbering (see @docs/spec-driven-workflow.md).
2. **Create** `docs/specs/SPEC-00N-$ARGUMENTS.md` using the same structure and
   tone as @docs/specs/SPEC-002-analyzer.md, with these sections:
   - Title `# SPEC-00N — <Title>`
   - Metadata block: **Status** (start as `Draft`), **Depends on**, **Modules**
   - `## Scope`
   - The behavioral sections appropriate to the component
   - `## Acceptance tests` — concrete, numbered (T1, T2, …), each verifiable
     against `error-reports/` fixtures where relevant
3. **Ground it in reality.** Reference @docs/data-format.md and real corpus
   samples; do not invent input behavior.
4. **Cross-link.** Add the new spec to the table in
   @docs/specs/SPEC-000-overview.md §8 and, if it introduces a milestone, note
   it in @docs/roadmap.md.
5. Leave a `## Open questions` section for anything unresolved.

Report the new file path and a one-line summary of what it specifies. Keep
Status as `Draft` until I approve it.
