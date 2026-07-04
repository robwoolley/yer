# SPEC-004 — Static Report Rendering

- **Status:** Approved
- **Depends on:** [SPEC-002](SPEC-002-analyzer.md)
- **Modules:** `render/json_out.py`, `render/static.py`, `render/sarif.py`, `render/templates/`

## Scope

Project the `Report` into publishable artifacts: canonical `report.json`, a
self-contained HTML page, and (fast-follow) SARIF.

## 1. `report.json` (canonical, `json_out.py`)
- **Deterministic:** stable key order, findings sorted per SPEC-002, **no
  wall-clock timestamps** in the document body (determinism/NFR3). Any run
  metadata (tool version) is fixed-position and optional.
- Schema (versioned via `schema_version`):

```jsonc
{
  "schema_version": "1.0",
  "tool_version": "x.y.z",
  "builds": [ { "component": "...", "machine": "...", "distro": "...",
               "source": "error_report_....txt", "failure_count": 1 } ],
  "findings": [ {
    "category": "configure", "severity": "error", "confidence": 0.86,
    "title": "package \"Qt6\" considered NOT FOUND",
    "recipe": "gz-gui9", "task": "do_configure",
    "file": "CMakeLists.txt", "line": 110,
    "evidence": ["...", "..."],
    "signature": "sha1:...", "cascade_of": null,
    "occurrences": 1, "affected_recipes": ["gz-gui9"]
  } ],
  "summary": { "errors": 1, "warnings": 0, "by_category": {"configure": 1} }
}
```

- This schema is the interchange contract for CI and any future dashboard.

## 2. Static HTML (`static.py`)
- **Single self-contained file** `index.html`: inline CSS + JS, **no external
  requests** (CI/offline/air-gapped safe). Any assets are data-URIs.
- **Light & dark** via `prefers-color-scheme`.
- Layout:
  - Header: build metadata (component/machine/distro/branch_commit),
    totals, by-category counts.
  - Findings grouped by recipe, then category; each collapsible, showing
    severity, confidence, `file:line`, and evidence in a horizontally
    scrollable `<pre>` (never break page layout on long lines).
  - Cascade findings nested under their root.
  - Per-finding **"Copy for Claude"** button yielding that finding's SPEC-005
    Markdown summary.
- Responsive; wide content (evidence, tables) scrolls within its own container.
- Rendered with Jinja2; templates in `render/templates/`.

## 3. SARIF (`sarif.py`, fast-follow M5)
- Emit SARIF 2.1.0: each finding → a `result` with `ruleId = category`, level
  mapped from severity, and `physicalLocation` from `file`/`line` when present.
- Enables GitHub/GitLab code-scanning annotations for near-zero extra cost.

## 4. Determinism & privacy
- Same input → byte-identical `report.json`. HTML may carry a generated-at
  timestamp only in non-semantic chrome.
- `local_conf`/`auto_conf` never rendered unless `--include-config`; redaction
  per SPEC-005 applies even then.
- **Redact host identity from evidence — always.** `report.json` and the HTML
  page are **published** artifacts (CI, Pages), so finding evidence/titles MUST
  be run through the SPEC-005 §4 host-identity redaction (the reporter does not
  anonymize `do_fetch` env dumps / the dependency build root — data-format.md).

## Changelog
- **2026-07-04 (M4-04):** Added **T6** to §5. §2 already required a per-finding
  "Copy for Claude" button; T6 makes it verifiable — each finding embeds that
  finding's SPEC-005 Markdown as the copy payload, and copying is inline JS with
  no network.
- **2026-07-03 (M4-02):** Added the host-identity redaction requirement to §4.
  `report.json`/HTML are shareable artifacts, so evidence must be scrubbed of
  `SSH_AUTH_SOCK` socket paths and `/<host>/<user>/<date>/…` build roots, the
  same as the LLM summary (SPEC-005 §4).

## 5. Acceptance tests
- **T1** `yer report error-reports/*.txt --html out/` writes `out/index.html`
  and `out/report.json`.
- **T2** `index.html` opens with no network access; contains no `http(s)://`
  asset references.
- **T3** `report.json` validated against schema; identical across two runs
  (diff is empty).
- **T4** A finding with `file`/`line` renders a location; one without still
  renders.
- **T5** Long evidence lines do not cause horizontal page scroll.
- **T6** Each finding renders a "Copy for Claude" button whose embedded payload
  is that finding's SPEC-005 Markdown (contains the SPEC-005 header and the
  finding's root-cause line). Copying is inline JS with no network request.
