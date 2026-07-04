"""M6-01: append-only run store (SPEC-006 §1).

Acceptance tests copied from SPEC-006 §6:
    T2  The store is append-only JSONL: recording twice appends two lines and
        leaves the first untouched; an absent store makes the first run all-new
        (readable as empty history); a malformed line is skipped, not fatal.
    T3  A run record contains no host-identity structure, no local_conf/
        auto_conf, no evidence, and no input paths.
"""

from pathlib import Path

from yocto_error_reports import ingest
from yocto_error_reports.analyze import analyze
from yocto_error_reports.models import Build, Failure
from yocto_error_reports.trends.store import load_runs, record_run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _report():
    return analyze([ingest.load_report(FIXTURES / "configure_gz-gui9.json")])


def test_t2_store_is_append_only(tmp_path):
    store = tmp_path / "trends.jsonl"
    record_run(_report(), store_path=store, tool_version="1.0.0")
    first = store.read_text(encoding="utf-8")
    record_run(_report(), store_path=store, tool_version="1.0.0")
    after = store.read_text(encoding="utf-8")
    assert after.startswith(first)  # the first line is untouched
    assert len(after.splitlines()) == 2  # appended, not rewritten
    assert len(load_runs(store)) == 2


def test_t2_absent_store_is_empty_history(tmp_path):
    assert load_runs(tmp_path / "does-not-exist.jsonl") == []


def test_t2_malformed_line_is_skipped(tmp_path):
    store = tmp_path / "trends.jsonl"
    record_run(_report(), store_path=store, tool_version="1.0.0")
    with store.open("a", encoding="utf-8") as handle:
        handle.write("{ this is not json\n")
        handle.write("\n")  # blank line
    runs = load_runs(store)
    assert len(runs) == 1  # the one valid record survives; junk skipped


def test_t3_record_has_no_host_identity_config_evidence_or_paths(tmp_path):
    # an unscrubbed report: host identity in the title/evidence, secrets in
    # config, and a real input path on the build.
    log = (
        "Nothing RPROVIDES 'foo' (but /ala-host99/rwoolley/2026-06-30/build/../"
        "layers/meta/foo_1.0.bb RDEPENDS on it)\n"
        "No eligible RPROVIDERs exist for 'foo'"
    )
    failure = Failure(
        task="Nothing provides '/ala-host99/rwoolley/2026-06-30/foo'",
        package="foo",
        log=log,
        kind="message",
    )
    build = Build(
        failures=[failure],
        raw={"local_conf": "allow-empty-password\nSECRET_XYZ"},
        source_path="/home/rcwoolley/secret/place/error_report.txt",
    )
    store = tmp_path / "trends.jsonl"
    record_run(analyze([build]), store_path=store, tool_version="1.0.0")
    text = store.read_text(encoding="utf-8")

    # host identity redacted
    assert "rwoolley" not in text
    assert "/ala-host99" not in text
    assert "2026-06-30" not in text
    assert "HOSTDIR" in text  # redaction placeholder present in the stored title
    # no config
    assert "SECRET_XYZ" not in text
    assert "allow-empty-password" not in text
    assert "local_conf" not in text
    # no evidence
    assert "No eligible RPROVIDERs" not in text
    assert '"evidence"' not in text
    # no input paths
    assert "/home/rcwoolley/secret" not in text
