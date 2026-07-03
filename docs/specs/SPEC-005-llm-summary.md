# SPEC-005 — LLM Summary

- **Status:** Approved
- **Depends on:** [SPEC-002](SPEC-002-analyzer.md)
- **Module:** `summarize.py`

## Scope

Project `Finding[]` into a compact, **token-bounded**, privacy-scrubbed summary
suitable for feeding to Claude. **No network calls** — the tool emits text; the
user pipes it (e.g. `yer summarize … | claude -p "…"`).

## 1. Design constraints
- **Token budget** (default ~4000 tokens; `--budget`). The 2.1 MB sample log
  MUST fit under budget after selection.
- **Selection:** top-K findings by rank (default K=5); within each, ≤ M evidence
  lines (default 8), **tail-biased** (real error sits near the log end, before
  the BB backtrace).
- **Always keep** per finding: recipe, task, category, `file:line`, and the
  first/root error line — even when trimming.
- **Be honest about loss:** include a `truncated` block (findings omitted, log
  lines dropped) so the model knows context was cut.

## 2. Output — Markdown (`--format md`, default)
Human-pasteable and model-friendly:

```markdown
# Yocto build failure — gz-gui9 (do_configure)
- machine: raspberrypi5 · distro: ros2 · target: aarch64-oe-linux
- bitbake: 2.18.0 · branch: wrynose:06dd66e

## Finding 1 — configure-error (confidence 0.86)
Root cause: package "Qt6" considered NOT FOUND at CMakeLists.txt:110

```
CMake Error at .../GzConfigureBuild.cmake ...
  package "Qt6" ... set Qt6_FOUND to FALSE ...
-- Configuring incomplete, errors occurred!
```

(2 further findings omitted; 812 log lines dropped)
```

## 3. Output — JSON (`--format json`)
Structured for programmatic feeding:

```jsonc
{
  "build": {"component":"gz-gui9","machine":"raspberrypi5","distro":"ros2",
            "target_sys":"aarch64-oe-linux","bitbake_version":"2.18.0",
            "branch_commit":"wrynose:06dd66e"},
  "findings": [ {
    "category":"configure","confidence":0.86,
    "recipe":"gz-gui9","task":"do_configure",
    "title":"package \"Qt6\" considered NOT FOUND",
    "file":"CMakeLists.txt","line":110,
    "likely_cause":"Qt6 not found in sysroot / missing DEPENDS",
    "evidence":["...", "..."]
  } ],
  "truncated": {"findings_omitted":2, "log_lines_dropped":812}
}
```

## 4. Privacy (hard requirement)
- **Exclude `local_conf` and `auto_conf` by default.** `--include-config`
  opts in.
- Even with opt-in, **redact** obvious secrets: lines matching
  password/token/key/secret patterns, and `*_password`/`allow-empty-password`
  style entries seen in samples.
- Anonymized `TOPDIR` paths are preserved as-is (already scrubbed by the
  reporter); do not re-expand.

## 5. Acceptance tests
- **T1** Summary for the largest corpus report is under the default token
  budget (approximate via a tokenizer or chars/4 heuristic).
- **T2** `--format json` validates and includes a `truncated` block when
  trimming occurred.
- **T3** No `local_conf`/`auto_conf` content appears without `--include-config`.
- **T4** With `--include-config`, a `password`-bearing line is redacted.
- **T5** For a multi-finding report, root cause (rank 1) is always present even
  at a small `--budget`.
- **T6** End-to-end: `yer summarize <sample> | claude -p "diagnose"` yields a
  plausible fix on ≥3 category samples (manual/CI-smoke).
