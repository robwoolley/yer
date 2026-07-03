# SPEC-002 — Analyzer (rules, dedup, ranking)

- **Status:** Approved
- **Depends on:** [SPEC-001](SPEC-001-parser.md)
- **Modules:** `analyze/__init__.py`, `analyze/signatures.py`, `analyze/rules/*`, `analyze/dedup.py`

## Scope

`Failure[]` (with parsed `LogLine[]`) → ranked, deduplicated `Finding[]`. This is
the core of the product.

## 1. Rule registry (`signatures.py`)

A rule is a record:

```python
@dataclass(frozen=True)
class Rule:
    name: str
    category: str                 # compile|configure|patch|qa|fetch|dependency|unknown
    severity: str                 # error|failure|warning|anomaly
    match: Callable[[Failure, list[LogLine]], bool]
    extract: Callable[[Failure, list[LogLine]], Finding | None]
    confidence: float             # base confidence when matched
    order: int                    # tie-break / phase ordering
```

Rules register into a module-level registry. `analyze()` runs a failure through
all rules, collects hits, and picks/combines findings. Adding a category = a new
module in `rules/` that appends a rule. **No edits to the orchestrator.**

## 2. Seed rules (from real corpus — see data-format §grammar)

| Module | Category | Match signals | Extract |
| --- | --- | --- | --- |
| `dependency.py` | `dependency` | `Failure.kind=="message"` or `task`/log starts with `Nothing provides` / `No provider` | title = the missing provide; recipe from `package`. |
| `patch.py` | `patch` | `Hunk #\d+ FAILED`, `does not apply`, `rejects in file` | title = patch name + first failing file/hunk; `file`/`line` from `Hunk #N FAILED at <line>`. |
| `qa.py` | `qa` | `ERROR: QA Issue:`, `Fatal QA errors were found` | title = distinct QA-issue class(es); collapse the many per-symlink lines into one finding with a count. |
| `configure.py` | `configure` | `CMake Error at`, `Configuring incomplete, errors occurred!`, `package "X" … NOT FOUND` | title = the NOT FOUND package or first CMake Error; `file`/`line` from `CMakeLists.txt:<n>`. |
| `compile.py` | `compile` | `ninja: build stopped`, gcc/clang `error:`, `undefined reference to` | title = first compiler `error:` (or the cmake cause if compile wraps configure); `file:line` from the diagnostic. |
| `fetch.py` | `fetch` | `do_fetch` + `Unable to fetch`/`Network`/checksum mismatch | title = URI + reason. |
| `fallback.py` | `unknown` | any remaining `level=="ERROR"` (else last `WARNING`) | title = that line. **Guarantees every failure yields ≥1 finding.** |

**Notes grounded in samples:**
- Some `do_compile` failures are really configure-time (`gz-sim-vendor`: cmake
  `NOT FOUND` inside `do_compile`). Rules match on **content**, not just the
  `task` name; `configure`-style signals win the category even under
  `do_compile`.
- QA reports emit dozens of near-identical `ERROR: QA Issue:` lines — dedup MUST
  collapse these (see §4).

## 3. Evidence extraction
- Each finding carries **≤ N evidence lines** (default N=15), chosen around the
  matched line — prefer the matched line + a few of context, **tail-biased** for
  compile/configure (the real error is near the end before the BB backtrace).
- Strip `NOTE:`/`DEBUG:` noise from evidence unless it is the only content.
- Never place whole logs in evidence.

## 4. Deduplication (`dedup.py`)
- **Within a finding:** collapse consecutive identical/normalized-identical
  evidence lines to `line ×N`.
- **Across findings:** group by `signature`. `signature = sha1(normalize(
  category + "\n" + title + "\n" + top_evidence))` using the shared `normalize()`
  from SPEC-001. Conservative normalization in v1 (OQ1).
- Duplicates across reports in one run are grouped with an occurrence count and
  the list of affected recipes.

## 5. Ranking & root-cause vs cascade
- Sort findings by `(severity_rank, phase_order, -confidence, recipe)`.
- Within one failure, the **earliest** `error`-severity finding in log order is
  the presumptive root cause; later same-category errors get
  `cascade_of = <root signature>` rather than being dropped.
- `phase_order`: fetch < patch < configure < compile < qa (earlier phase =
  more likely the true blocker when multiple categories co-occur).

## 6. Output
`analyze(builds) -> Report` where `Report` holds `Build[]`, flat `Finding[]`,
and dedup groups. Deterministic ordering.

## 7. Acceptance tests (golden files)
- **T1** Each corpus category sample classifies to the expected `category`.
- **T2** `gz-physics-vendor` QA sample → **one** qa finding with a symlink-count,
  not 14.
- **T3** `gz-sim-vendor do_compile` → category `configure` (Qt6 NOT FOUND), not
  `compile`.
- **T4** `ogre-next do_patch` → `patch`, `file` = `OgreMathlibNEON.h`, hunk line 601.
- **T5** A file with 22 failures produces ≤22 findings, correctly deduped, ranked.
- **T6** Every corpus file yields ≥1 finding (fallback guarantee).

## Changelog

- **2026-07-03 (M2-02):** Clarified §2 fallback title selection. To uphold the
  "every failure yields ≥1 finding" guarantee for the 2 dependency failures that
  carry neither an `ERROR` nor a `WARNING` line, the fallback falls back to the
  failure's `task`/message when no level line is present: first `ERROR`, else
  last `WARNING`, else `task`/message. The orchestrator applies the fallback only
  when no category rule produced a finding for that failure.
