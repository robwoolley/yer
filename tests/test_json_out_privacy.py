"""M4-02: artifacts redact host identity + exclude config (SPEC-004 §4).

report.json / HTML are published artifacts, so evidence must be scrubbed of
host-identity structure — even when the input report is unscrubbed.
"""

import json

from yer.analyze import analyze
from yer.models import Build, Failure
from yer.render.json_out import to_report_json


def test_host_identity_redacted_from_report_json():
    log = (
        "Nothing RPROVIDES 'foo' (but /ala-host99/rwoolley/2026-06-30/build/../"
        "layers/meta/foo_1.0.bb RDEPENDS on it)\n"
        "No eligible RPROVIDERs exist for 'foo'"
    )
    failure = Failure(task="Nothing provides 'foo'", package="foo", log=log, kind="message")
    report = analyze([Build(failures=[failure])])
    text = to_report_json(report, tool_version="1.0.0")
    assert "rwoolley" not in text
    assert "/ala-host99" not in text
    assert "2026-06-30" not in text
    assert "HOSTDIR" in text  # redaction placeholder present


def test_config_not_in_report_json():
    # report.json carries findings + build metadata, never local_conf/auto_conf
    build = Build(raw={"local_conf": "SECRET_XYZ\nallow-empty-password"}, failures=[])
    text = to_report_json(analyze([build]), tool_version="1.0.0")
    assert "SECRET_XYZ" not in text
    assert "allow-empty-password" not in text
    assert "local_conf" not in json.loads(text)["builds"][0]
