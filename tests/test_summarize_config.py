"""M3-06: --include-config opt-in + secret redaction (SPEC-005 §4).

Acceptance test copied from SPEC-005 §5:
    T4  With --include-config, a `password`-bearing line is redacted.

Uses a synthetic build config (never a real report) carrying a fake secret.
"""

from yocto_error_reports.analyze import analyze
from yocto_error_reports.models import Build, Failure
from yocto_error_reports.summarize import summarize, to_json, to_markdown

_LOCAL_CONF = (
    'DISTRO = "poky"\n'
    'MY_SERVICE_password = "hunter2"\n'
    'IMAGE_FEATURES += "allow-empty-password"\n'
)


def _report():
    build = Build(
        raw={"local_conf": _LOCAL_CONF},
        failures=[Failure(task="do_compile", recipe="r", log="ERROR: boom", kind="task")],
    )
    return analyze([build])


def test_t4_include_config_redacts_password_line():
    summary = summarize(_report(), include_config=True)
    blob = to_markdown(summary) + to_json(summary)
    assert 'DISTRO = "poky"' in blob  # non-secret config is included
    assert "hunter2" not in blob  # the secret value is redacted
    assert "allow-empty-password" not in blob  # policy-secret line redacted


def test_config_excluded_by_default():
    summary = summarize(_report())  # include_config defaults False
    blob = to_markdown(summary) + to_json(summary)
    assert "hunter2" not in blob
    assert "DISTRO" not in blob  # no config at all without opt-in
    assert summary.config is None
