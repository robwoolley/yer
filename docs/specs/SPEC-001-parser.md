# SPEC-001 — Ingest & Parse

- **Status:** Approved
- **Depends on:** [SPEC-000](SPEC-000-overview.md), [data-format](../data-format.md)
- **Modules:** `ingest.py`, `parse.py`, `models.py`

## Scope

Turn input sources into `Build` objects, and each failure's raw `log` string
into structured `LogLine` events. **No classification here.**

## 1. Ingest (`ingest.py`)

### Inputs
- One or more of: file path, glob, directory (recursively scanned for report
  files), or `-` (stdin). A directory yields all files that parse as reports.

### Parsing rules (defensive — see data-format §"Robustness rules")
- **File extension is opaque.** Detect by attempting `json.loads`.
- Every top-level and failure field is **optional**. Missing → `None`.
- Unknown extra keys are ignored (preserved in `Build.raw`).
- `failures` absent/empty → `Build` with `failures == []`.
- A failure whose `task` is not a `do_*` name is `kind="message"` (dependency /
  parse failure); its `task` string is the error message.
- Missing `recipe` (2 legacy samples) is allowed.

### Error handling (hard requirement FR2)
- A file that is not valid JSON, or is JSON but not a report shape, MUST NOT
  raise. Instead produce a `Build` carrying a synthetic parse `Finding`
  (`category="unknown"`, `severity="error"`, title = the parse problem) so it
  surfaces in output and affects exit code.
- Duplicate input paths are de-duplicated.

### Output
`list[Build]`, in stable input order.

## 2. Parse (`parse.py`)

### `log` → `LogLine[]`
- Iterate lines (do **not** regex the whole 2 MB string at once).
- Detect a leading bitbake level token and split it out:
  `^(ERROR|WARNING|NOTE|DEBUG):\s?` → `LogLine.level`, remainder → `.text`.
  Lines without a token get `level=None`.
- Preserve original 1-based line numbers in `.n`.
- Lines may carry leading indentation from sub-tools (cmake/ninja); keep it in
  `.text` (do not strip — indentation is sometimes meaningful).

### Backtrace block
- Detect the block beginning `WARNING: Backtrace (BB generated script):` and the
  following `#N: <func>, <path>, line <n>` frames. Expose as
  `Failure`-associated structured frames (or a parsed side-channel) for the
  analyzer to confirm the failing function/task.

### Path normalization helper
- Provide a reusable `normalize(text)` that maps `TOPDIR/...` paths, absolute
  temp paths, line numbers, hex addresses, and PIDs (e.g.
  `run.do_compile.2609824`) to stable placeholders. Used by `signature`
  computation in SPEC-002 — defined here so parse/analyze share one
  normalizer.

## 3. Performance
- Streaming line iteration; O(n) in log size. The 2.1 MB sample must parse well
  within the corpus-wide few-second budget.

## 4. Acceptance tests
- **T1** Every file in `error-reports/` yields a `Build`; none raises.
- **T2** A truncated/garbage file yields a parse-finding Build, not an exception.
- **T3** `task="Nothing provides '…'"` → `kind="message"`.
- **T4** A failure missing `recipe` parses (recipe `None`).
- **T5** Level prefixes correctly split on the `do_package_qa` sample
  (`ERROR: QA Issue:` → level `ERROR`, text `QA Issue:…`).
- **T6** Backtrace frames extracted from the `gz-gui9 do_configure` sample.
