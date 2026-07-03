"""Redact host identity from shareable text (SPEC-005 §4, data-format.md).

The reporter anchors most paths to `TOPDIR/...` but not everything: `do_fetch`
env dumps carry an `SSH_AUTH_SOCK` socket path and the dependency `RPROVIDES`
message carries an absolute `/<host>/<user>/<date>/…` build root, both leaking a
username/hostname. These are redacted by **structure** — no specific host, mount,
or user is named. Same approach as the fixture scrubber. Stdlib-only.
"""

from __future__ import annotations

import re

_REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'SSH_AUTH_SOCK="[^"]*"'), 'SSH_AUTH_SOCK="<redacted>"'),
    (re.compile(r"/[\w.+-]+/[\w.+-]+/\.(?:gnupg|ssh)/[\w./+-]*"), "<redacted-path>"),
    (re.compile(r"/[\w.+-]+/[\w.+-]+/\d{4}-\d{2}-\d{2}"), "HOSTDIR"),
]


def redact_host_identity(text: str) -> str:
    """Replace host-identity structures with neutral placeholders."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text
