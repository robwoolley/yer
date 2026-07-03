"""Trivial smoke test for M0-03: the package and its stages import cleanly."""

import importlib


def test_package_imports():
    pkg = importlib.import_module("yocto_error_reports")
    assert isinstance(pkg.__version__, str)


def test_core_modules_import():
    # Stage modules present so far (more arrive in later milestones).
    for name in ("yocto_error_reports.models", "yocto_error_reports.cli"):
        assert importlib.import_module(name) is not None
