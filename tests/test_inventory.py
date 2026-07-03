"""M1-08: provisional failure inventory (roadmap M1 demoable; SPEC-001 §1 output).

The `category` here is derived from the task name only (data-format taxonomy),
not the content-aware analyzer that lands in M2.
"""

from pathlib import Path

import pytest

from yocto_error_reports import ingest, inventory
from yocto_error_reports.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CORPUS = Path(__file__).resolve().parent.parent / "error-reports"


def _fixture_inventory():
    return inventory.inventory(ingest.load_reports([FIXTURES]))


def test_inventory_counts_over_fixtures():
    inv = _fixture_inventory()
    assert inv.reports == 7
    assert inv.failures == 10
    assert inv.by_category == {
        "compile": 4, "qa": 2, "configure": 1, "patch": 1, "fetch": 1, "dependency": 1,
    }
    assert inv.by_task == {
        "do_compile": 4, "do_package_qa": 2, "do_configure": 1,
        "do_patch": 1, "do_fetch": 1, "<message>": 1,
    }
    # by_recipe accounts for every failure
    assert sum(inv.by_recipe.values()) == inv.failures


def test_inventory_orders_deterministically_by_count_then_name():
    inv = _fixture_inventory()
    counts = list(inv.by_category.values())
    assert counts == sorted(counts, reverse=True)


def test_format_inventory_is_readable_text():
    text = inventory.format_inventory(_fixture_inventory())
    assert "7 report(s), 10 failure(s)" in text
    assert "compile" in text and "dependency" in text


def test_cli_inventory_subcommand(capsys):
    assert main(["inventory", str(FIXTURES)]) == 0
    out = capsys.readouterr().out
    assert "report(s)" in out
    assert "compile" in out


@pytest.mark.slow
@pytest.mark.skipif(not CORPUS.is_dir(), reason="corpus not present (gitignored)")
def test_corpus_inventory_matches_data_format_distribution():
    inv = inventory.inventory(ingest.load_reports([CORPUS]))
    assert inv.by_category == {
        "compile": 60, "configure": 31, "patch": 27, "qa": 12, "fetch": 1, "dependency": 2,
    }
