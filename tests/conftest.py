# z-manager/tests/conftest.py
"""
Pytest configuration and shared fixtures.

Marking conventions:
    @pytest.mark.privileged  — requires root; auto-skipped unless --privileged flag is passed
    @pytest.mark.integration — real system state; slow; not mocked
"""

from __future__ import annotations

import os
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "privileged: tests that require root (skipped by default)"
    )
    config.addinivalue_line("markers", "integration: tests that hit real system state")


def pytest_addoption(parser):
    parser.addoption(
        "--privileged",
        action="store_true",
        default=False,
        help="Run privileged integration tests that require root.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--privileged"):
        return
    skip_privileged = pytest.mark.skip(
        reason="requires --privileged flag (root needed)"
    )
    for item in items:
        if "privileged" in item.keywords:
            item.add_marker(skip_privileged)


@pytest.fixture
def requires_root():
    """Skip test if not running as root."""
    if os.geteuid() != 0:
        pytest.skip("Requires root")
    return True


@pytest.fixture
def is_root():
    """Return True if already root."""
    return os.geteuid() == 0


@pytest.fixture
def tmp_swap_path(tmp_path):
    """Provide a safe temp path for swapfile creation during tests."""
    return str(tmp_path / "test-swapfile")
