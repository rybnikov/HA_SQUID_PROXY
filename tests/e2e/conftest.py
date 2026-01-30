"""E2E Playwright fixtures with parallel execution support.

Design for maximum parallelization:
- Per-test browser contexts (not shared)
- Per-worker port allocation (no conflicts)
- Isolated instances (unique names + ports)
- Session-scoped browser (one per worker process)
- Reusable browser launch configuration
"""

from __future__ import annotations

import itertools
import os
from collections.abc import AsyncGenerator

import aiohttp
import pytest
from playwright.async_api import Browser, async_playwright

# Per-worker counters (reset each test to avoid collisions)
_NAME_COUNTER = itertools.count(1)
_PORT_COUNTER = itertools.count(0)

# Configuration
ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "test_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


def _worker_offset() -> int:
    """Calculate port offset based on worker ID for parallel execution.

    Each worker gets 1000 ports to avoid conflicts:
    - Worker 0: ports 3200-4199
    - Worker 1: ports 4200-5199
    - etc.
    """
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    if worker_id.startswith("gw") and worker_id[2:].isdigit():
        return int(worker_id[2:]) * 1000
    return 0


@pytest.fixture(scope="session")
async def browser_instance() -> AsyncGenerator[Browser, None]:
    """Session-scoped browser instance (one per worker process).

    This reduces overhead by reusing one browser across multiple tests
    within the same worker.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",  # Reduce memory usage
            ],
        )
        try:
            yield browser
        finally:
            await browser.close()


@pytest.fixture
async def browser(browser_instance: Browser):
    """Per-test browser context from session browser.

    Returns the session browser but each test should create
    its own page via browser.new_page() for isolation.
    """
    return browser_instance


@pytest.fixture
def unique_name():
    """Return a unique, per-test instance name with worker offset.

    Format: {base}-w{worker}-{counter}
    Example: "proxy-w0-1", "proxy-w1-1" (parallel workers)
    """
    offset = _worker_offset()

    def _make(base: str) -> str:
        return f"{base}-w{offset // 1000}-{next(_NAME_COUNTER)}"

    return _make


@pytest.fixture
def unique_port():
    """Return a unique port with worker offset to avoid conflicts.

    Base ports 3200-3210 are allocated per test, with worker offset applied.
    Worker 0: 3200-3210
    Worker 1: 4200-4210
    etc.
    """
    offset = _worker_offset()

    def _make(base: int) -> int:
        port = base + offset + next(_PORT_COUNTER)
        # Ensure port is in valid range
        if port < 3128:
            port = 3200 + offset + next(_PORT_COUNTER)
        return port

    return _make


@pytest.fixture
async def api_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Reusable aiohttp session for API tests with proper headers."""
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        yield session


@pytest.fixture
async def clean_instance_cleanup(api_session: aiohttp.ClientSession):
    """Fixture for cleanup of created instances after test.

    Usage:
        instances_to_clean = []
        yield instances_to_clean
        # ... instances_to_clean.append(name) during test ...
        # Cleanup happens automatically here
    """
    instances: list[str] = []
    yield instances

    # Cleanup: remove all instances created during test
    for instance_name in instances:
        try:
            async with api_session.delete(f"{ADDON_URL}/api/instances/{instance_name}") as resp:
                _ = resp.status  # Consume response
        except Exception:
            pass  # Ignore cleanup errors
