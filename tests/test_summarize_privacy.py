"""M3-05: privacy — exclude config + redact host identity from evidence (SPEC-005 §4).

Acceptance test copied from SPEC-005 §5:
    T3  No local_conf/auto_conf content appears without --include-config.
Plus: host-identity structure never appears in a summary of unscrubbed input.
"""

from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.models import Build, Failure
from yocto_error_reports.summarize import summarize, to_json, to_markdown

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_t3_no_config_content_in_summary():
    # config lives in Build.raw, never in findings; it must not surface by default
    report = analyze([ingest.load_report(FIXTURES / "configure_gz-gui9.json")])
    report.builds[0].raw = {"local_conf": "SECRET_MARKER_XYZ\nallow-empty-password"}
    blob = to_markdown(summarize(report)) + to_json(summarize(report))
    assert "SECRET_MARKER_XYZ" not in blob
    assert "allow-empty-password" not in blob


def test_host_identity_redacted_from_evidence():
    # UNSCRUBBED synthetic report (as a real corpus report would be)
    log = (
        "Nothing RPROVIDES 'foo' (but /ala-host99/rwoolley/2026-06-30/build/../"
        "layers/meta/foo_1.0.bb RDEPENDS on it)\n"
        "No eligible RPROVIDERs exist for 'foo'"
    )
    build = Build(
        failures=[Failure(task="Nothing provides 'foo'", package="foo", log=log, kind="message")]
    )
    summary = summarize(analyze([build]))
    blob = to_markdown(summary) + to_json(summary)
    assert "rwoolley" not in blob
    assert "/ala-host99" not in blob
    assert "2026-06-30" not in blob
    assert "HOSTDIR" in blob  # redaction placeholder present


def test_ssh_auth_sock_value_redacted():
    from yocto_error_reports.redact import redact_host_identity

    line = 'export SSH_AUTH_SOCK="/folk/rwoolley/.gnupg/S.gpg-agent.ssh"; other'
    out = redact_host_identity(line)
    assert "rwoolley" not in out and "/folk/" not in out
    assert 'SSH_AUTH_SOCK="<redacted>"' in out
