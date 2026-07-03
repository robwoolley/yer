# SPEC-003 — CLI & Exit Codes

- **Status:** Approved
- **Depends on:** [SPEC-002](SPEC-002-analyzer.md)
- **Module:** `cli.py` (console script `yer`)

## Scope

The command surface, argument contract, terminal rendering, and CI exit-code
behaviour. CLI concerns MUST NOT leak into `parse`/`analyze`.

## 1. Subcommands

### `yer analyze <inputs...>`
Parse + analyze; render findings.
- `--format {text,json,sarif}` (default `text`). `sarif` may land in M5.
- `-o, --output <path>` (default stdout).
- `--fail-on {error,failure,warning,none}` (default `error`).
- `--category <c>` (repeatable) filter; `--recipe <name>` filter.
- `--max-evidence <n>` (default 15).
- `-v/--verbose`, `-q/--quiet`, `--no-color` (also honor `NO_COLOR`).

### `yer report <inputs...> --html <dir>`
Write static artifacts (SPEC-004): `<dir>/index.html` + `<dir>/report.json`.
- `--html <dir>` (required for this subcommand).
- `--format json -o <path>` may additionally emit canonical JSON elsewhere.
- Same filters and `--fail-on` as `analyze`.

### `yer summarize <inputs...> --for-llm`
Emit the token-bounded LLM summary (SPEC-005).
- `--for-llm` (implied by the subcommand; kept for clarity).
- `--format {md,json}` (default `md`).
- `--budget <tokens>` (default per SPEC-005).
- `--include-config` (opt-in; still redacted). Default: config excluded.

### Global
- `yer --version`, `yer --help`, `yer <cmd> --help`.

## 2. Input resolution
Paths, globs, directories, and `-` (stdin) per SPEC-001. No matching inputs →
exit `2` with a clear message.

## 3. Terminal rendering (`text`)
- Use `rich` if available; degrade to plain text if not or under `--no-color`.
- Per finding: `recipe  task  <severity-glyph> category (confidence)`, then
  indented title and evidence. Group by recipe; cascades shown nested/dimmed.
- Footer summary line: `N errors, M warnings — exit K`.
- Deterministic ordering from SPEC-002.

## 4. Exit codes (CI contract — FR8)
| Code | Meaning |
| --- | --- |
| `0` | No finding at or above `--fail-on` (or `--fail-on none`). |
| `1` | At least one finding at/above `--fail-on`. |
| `2` | Tool/usage error (bad args, no inputs, unwritable output). |

Severity order for thresholding: `error` > `failure` > `warning` > `anomaly`.
A malformed report contributes a parse finding at `error` severity (SPEC-001),
so a corrupt input under default `--fail-on error` yields exit `1`, not `2`.

## 5. Acceptance tests
- **T1** `yer analyze error-reports/*.txt` exits `1` (corpus has errors), prints
  ranked findings.
- **T2** `--fail-on none` on the same input exits `0`.
- **T3** `--format json` output validates against the `report.json` schema
  (SPEC-004) and is byte-stable across runs.
- **T4** No inputs / bad path → exit `2`, message on stderr.
- **T5** `--no-color`/`NO_COLOR` produces plain ASCII.
- **T6** `--recipe gz-gui9` filters to that recipe only.
