"""E2E Playwright fixtures using async API to avoid nested event loops."""

from __future__ import annotations

import itertools
import os

import pytest
from playwright.async_api import async_playwright

_NAME_COUNTER = itertools.count(1)
_PORT_COUNTER = itertools.count(0)


def _worker_offset() -> int:
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    if worker_id.startswith("gw") and worker_id[2:].isdigit():
        return int(worker_id[2:]) * 100
    return 0


@pytest.fixture
async def browser():
    """Provide an async Playwright browser instance for E2E tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()


@pytest.fixture
def unique_name():
    """Return a unique, per-test instance name."""
    offset = _worker_offset()

    def _make(base: str) -> str:
        return f"{base}-w{offset}-{next(_NAME_COUNTER)}"

    return _make


@pytest.fixture
def unique_port():
    """Return a unique port per test, offset per worker."""
    offset = _worker_offset()

    def _make(base: int) -> int:
        return base + offset + next(_PORT_COUNTER)

    return _make
