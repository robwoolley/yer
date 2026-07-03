# Reference: Yocto `error-report.txt` Format

> **Status:** Reference (descriptive, not normative). Derived from 77 real sample
> reports in [`error-reports/`](../error-reports/). Update when new schema
> variants are observed.

## What the files are

Files named `error_report_<UTCtimestamp>.txt` are emitted by OpenEmbedded's
`report-error.bbclass` (the `send-error-report` tool). **Despite the `.txt`
extension, each file is a single UTF-8 JSON object.** The parser MUST treat the
extension as opaque and detect content by parsing.

## Top-level schema

Observed stable across all 77 samples:

| Key              | Type   | Notes                                                            |
| ---------------- | ------ | --------------------------------------------------------------- |
| `failures`       | array  | One or more failure objects. **The payload of interest.**       |
| `component`      | string | The build target / recipe being built, e.g. `core-image-minimal`. |
| `machine`        | string | e.g. `raspberrypi5`, `qemux86-64`.                              |
| `distro`         | string | e.g. `poky`, `ros2`.                                            |
| `build_sys`      | string | Host, e.g. `x86_64-linux`.                                      |
| `target_sys`     | string | e.g. `aarch64-oe-linux`.                                        |
| `nativelsb`      | string | Host distro, e.g. `universal/ubuntu-22.04`.                     |
| `bitbake_version`| string | e.g. `2.18.0`.                                                  |
| `branch_commit`  | string | e.g. `wrynose: 06dd66e…`.                                       |
| `layer_version`  | string | Newline-joined list of layer revisions.                        |
| `local_conf`     | string | Contents of `local.conf` (may contain secrets — see below).    |
| `auto_conf`      | string | Contents of `auto.conf` (often empty).                          |

## Failure object schema

| Key       | Type   | Notes                                                                 |
| --------- | ------ | --------------------------------------------------------------------- |
| `task`    | string | Usually a task name (`do_compile`, …). **May instead be an error message** for parse/dependency failures (e.g. `"Nothing provides 'moveit-ros-planning-interface-dev'"`). |
| `package` | string | Recipe/package name.                                                  |
| `recipe`  | string | Recipe id+version. **Absent in 2 legacy samples** — treat as optional.|
| `log`     | string | Full raw task log. 295 B – 2.1 MB. Empty/short for dependency failures.|

**Robustness rules the parser MUST follow:** every field is optional at parse
time; never index a missing key; tolerate unknown extra keys; `failures` may be
absent or empty.

## Failure taxonomy (observed distribution)

| `task` value                     | Count | Category                    |
| -------------------------------- | ----- | --------------------------- |
| `do_compile`                     | 60    | `compile`                   |
| `do_configure`                   | 31    | `configure`                 |
| `do_patch`                       | 27    | `patch`                     |
| `do_package_qa`                  | 12    | `qa`                        |
| `do_fetch`                       | 1     | `fetch`                     |
| `Nothing provides '…'` (in task) | 2     | `dependency` / `parse`      |

Per-file failure counts: mostly 1, but observed up to 22 in a single report.

## Log line grammar

Task logs are line-oriented. bitbake prefixes many lines with a level token:

- `ERROR:` — task-fatal errors. **Primary signal.**
- `WARNING:` — warnings + the BB script backtrace header.
- `NOTE:` / `DEBUG:` — progress noise; usually filtered from evidence.

Build paths are anonymized to a `TOPDIR/...` prefix by the reporter.

### High-signal patterns (seed the analyzer rules from these)

| Category    | Representative signatures (regex-able)                                             |
| ----------- | ---------------------------------------------------------------------------------- |
| `compile`   | `ninja: build stopped`, `error:` from gcc/clang, `undefined reference to`          |
| `configure` | `CMake Error at`, `Configuring incomplete, errors occurred!`, `package "X" … NOT FOUND` |
| `patch`     | `Hunk #\d+ FAILED`, `does not apply`, `rejects in file`                             |
| `qa`        | `ERROR: QA Issue:`, `Fatal QA errors were found, failing task.`                     |
| `fetch`     | `do_fetch` + `Unable to fetch`, `Network`, checksum mismatch                        |
| `dependency`| `task` field starts with `Nothing provides` / `No provider`                        |

### The BB backtrace block

Many logs end with a machine-parseable backtrace that pins the failing shell
function and the run-script line:

```
WARNING: Backtrace (BB generated script):
	#1: cmake_do_configure, TOPDIR/.../temp/run.do_configure.642082, line 153
	#2: do_configure, TOPDIR/.../temp/run.do_configure.642082, line 132
```

The analyzer SHOULD use this to confirm the failing task and phase.

## Privacy warning

`local_conf` can contain developer paths, hostnames, tokens, or passwords
(sample reports contain `empty-root-password`, `allow-empty-password`, etc.).
The tool MUST NOT copy `local_conf`/`auto_conf` verbatim into shareable reports
or LLM summaries without an explicit `--include-config` opt-in, and SHOULD offer
redaction. See [SPEC-005](specs/SPEC-005-llm-summary.md).
