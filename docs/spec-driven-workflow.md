# Spec-Driven Development with Claude Code

This project uses a lightweight, explicit spec-driven workflow. The point is
that **intent is written down and reviewed before code exists**, and Claude Code
works against that intent rather than guessing. This document explains the file
layout, the loop, and the conventions.

## The document hierarchy

```
CLAUDE.md                     ← operating rules Claude loads every session
README.md                     ← human entry point + doc map
docs/
  data-format.md              ← REFERENCE: ground truth about the input
  architecture.md             ← HOW: the system decomposition (stable)
  roadmap.md                  ← WHEN: milestones and sequencing
  spec-driven-workflow.md     ← this file: the process itself
  specs/
    SPEC-000-overview.md      ← WHAT & WHY: product requirements (the root spec)
    SPEC-00N-*.md             ← WHAT per component: testable behaviour + acceptance
tasks/
  milestone-N.md              ← DO: small, ordered, checkable tasks per milestone
error-reports/                ← the real sample corpus (ground truth data)
tests/fixtures/               ← anonymized samples + golden expected outputs
```

Why this split:

- **Specs** answer *what and why*, in verifiable terms (requirements +
  acceptance tests). They change rarely and are reviewed deliberately.
- **Architecture** answers *how* at the structural level, once, so specs and
  tasks don't each re-invent it.
- **Roadmap** answers *in what order*, decoupled from *what*.
- **Tasks** answer *do this next*, are disposable, and always cite a spec.
- **CLAUDE.md** is the always-loaded contract so every session starts aligned.

## Roles of each layer (keep them separate)

| Layer | Question | Volatility | Owner of truth for… |
| --- | --- | --- | --- |
| SPEC | What/why, acceptance | Low | Behaviour |
| Architecture | How (structure) | Low | Module boundaries |
| Roadmap | When/order | Medium | Sequencing |
| Tasks | Do next | High | Work in flight |
| Code + tests | Reality | High | Actual behaviour |

If two layers disagree, fix the higher (more stable) one deliberately, then
propagate down. Never let code silently diverge from a spec.

## The development loop

For each task:

1. **Read the spec section** the task cites (e.g. `SPEC-002 §2 seed rules`).
2. **Confirm ground truth** against `error-reports/` — never invent format
   details. Add/confirm a `tests/fixtures/` sample.
3. **Write the acceptance test first** from the spec's "Acceptance tests"
   section (golden files where applicable).
4. **Implement** the smallest change that satisfies the spec section.
5. **Run against the real corpus** — the tool must not crash on any of the 77
   files.
6. **Update docs** if you changed behaviour: spec first, then code, then
   fixture. Note the rationale.
7. **Check the box** in the milestone task file.

### Spec change protocol
When reality forces a spec change (new log pattern, wrong assumption):
- Edit the SPEC, bump nothing but add a dated note under a `## Changelog`
  heading if the change is non-trivial.
- Reflect it in `data-format.md` if it's about the input.
- Only then touch code. This keeps the spec authoritative.

## Conventions

- **Spec IDs are stable.** `SPEC-00N` numbers never get reused; supersede
  rather than renumber.
- **Every task cites a spec.** Task id format `M<milestone>-<nn>`; each task
  names `Spec:` and `DoD:` (definition of done).
- **Acceptance tests are copied from specs into code**, not paraphrased.
- **Fixtures are anonymized.** Never commit un-scrubbed customer data.
- **Determinism & privacy** are cross-cutting spec requirements — re-check them
  in every review (see NFR3/NFR4 in SPEC-000).

## How this maps to Claude Code features (optional, recommended)

These are conventions you can adopt as the team grows; none are required to
start:

- **`CLAUDE.md`** (already present) — loaded automatically; keep the golden
  rules terse and current.
- **Slash commands** (`.claude/commands/*.md`) — codify the loop, e.g.
  `/spec <name>` (scaffold a new SPEC), `/task <id>` (open a task and its cited
  spec), `/verify-corpus` (run the tool over `error-reports/` and report
  crashes). Add these when the loop stabilizes.
- **Subagents** (`.claude/agents/*.md`) — e.g. a "rule-author" agent scoped to
  `analyze/rules/` + fixtures for adding new failure categories.
- **Hooks** (`.claude/settings.json`) — run `ruff`/`pytest` on stop, or block
  commits that add un-anonymized fixtures.

Introduce these incrementally; the docs above are the substance, the automation
is convenience.

## Getting started as a contributor (or Claude)

1. Read `CLAUDE.md`, then `SPEC-000`, then `architecture.md`.
2. Open the current milestone in `tasks/`.
3. Pick the first unchecked task; follow the development loop above.
