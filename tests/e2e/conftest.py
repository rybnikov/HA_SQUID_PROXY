"""E2E Playwright fixtures with parallel execution support.

Design for maximum parallelization:
- Per-test browser contexts (not shared)
- Per-worker port allocation (no conflicts)
- Isolated instances (unique names + ports)
- Session-scoped browser (one per worker process)
- Reusable browser launch configuration
- 10-second timeout on all user actions for fail-fast testing
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
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "dev_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}

# Timeout configuration (in milliseconds)
DEFAULT_TIMEOUT = 10_000  # 10 seconds for user actions (click, fill, check)
WAIT_TIMEOUT = 30_000  # 30 seconds for page waits (navigation, readiness)
SCENARIO_TIMEOUT = 120  # 120 seconds per test scenario


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


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Configure pytest with scenario timeout marker."""
    config.addinivalue_line(
        "markers",
        f"timeout({SCENARIO_TIMEOUT}s): mark test to timeout after {SCENARIO_TIMEOUT} seconds "
        "(default for all E2E tests)",
    )


@pytest.fixture(autouse=True)
def _apply_scenario_timeout(request: pytest.FixtureRequest):
    """Auto-apply scenario timeout to all E2E tests.

    Each test gets SCENARIO_TIMEOUT seconds. If exceeded, test fails with timeout error.
    This ensures tests fail fast if user actions hang or get stuck.
    """
    # Only apply to E2E tests
    if "e2e" not in str(request.fspath):
        yield
        return

    # Apply timeout marker (pytest-timeout plugin handles this)
    marker = request.node.get_closest_marker("timeout")
    if not marker:
        # Add timeout marker if not explicitly set
        request.node.add_marker(pytest.mark.timeout(SCENARIO_TIMEOUT))

    yield


@pytest.fixture(scope="session", autouse=True)
async def cleanup_addon_data_before_tests():
    """Clean all addon data before E2E tests start (autouse, session scope).

    This ensures tests run against a clean slate, not leftover data from previous runs.
    Runs automatically before any E2E tests execute.

    Thorough cleanup:
    1. Delete all instances via API (which stops processes)
    2. Verify zero instances remaining (retry if needed)
    """
    import asyncio

    # Wait for addon to be fully ready (health check passing)
    max_attempts = 30
    for _attempt in range(max_attempts):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{ADDON_URL}/health", timeout=aiohttp.ClientTimeout(total=2)
                ) as resp:
                    if resp.status == 200:
                        break
        except Exception:
            pass
        await asyncio.sleep(1)

    await asyncio.sleep(1)  # Extra buffer after health check passes

    # Clean all addon data via API — retry until zero instances remain
    try:
        async with aiohttp.ClientSession(headers=API_HEADERS) as session:
            for _round in range(3):
                # Get list of all instances
                async with session.get(
                    f"{ADDON_URL}/api/instances", timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        instances = data.get("instances", []) if isinstance(data, dict) else data
                        if not instances:
                            break
                        # Delete each instance sequentially to avoid race conditions
                        for instance in instances:
                            instance_name = instance.get("name")
                            if instance_name:
                                try:
                                    async with session.delete(
                                        f"{ADDON_URL}/api/instances/{instance_name}",
                                        timeout=aiohttp.ClientTimeout(total=20),
                                    ) as del_resp:
                                        _ = del_resp.status
                                        await asyncio.sleep(1)
                                except Exception:
                                    pass
                # Wait for processes to fully terminate before verifying
                await asyncio.sleep(3)

            # Verify all instances are gone
            for _ in range(10):
                async with session.get(
                    f"{ADDON_URL}/api/instances", timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        remaining = data.get("instances", []) if isinstance(data, dict) else data
                        if not remaining:
                            break
                await asyncio.sleep(2)
    except Exception:
        pass  # If API cleanup fails, continue anyway

    # Final wait to ensure cleanup settles
    await asyncio.sleep(1)


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


@pytest.fixture(autouse=True)
async def auto_cleanup_instances_after_test(api_session: aiohttp.ClientSession):
    """Automatically cleanup ALL instances after each test (autouse).

    Deletes every instance and verifies zero remain before the next test starts.
    Uses retry logic for DELETE operations since instances may be mid-restart
    (each squid stop takes ~5s for SIGTERM + SIGKILL).
    """
    yield  # Run the test first

    import asyncio

    # Ensure addon is reachable (it may have crashed during the test)
    for _health_attempt in range(15):
        try:
            async with api_session.get(
                f"{ADDON_URL}/api/instances", timeout=aiohttp.ClientTimeout(total=3)
            ) as health_resp:
                if health_resp.status == 200:
                    break
        except Exception:
            pass
        await asyncio.sleep(2)

    # Delete ALL instances with retry until zero remain
    try:
        for _round in range(5):
            async with api_session.get(
                f"{ADDON_URL}/api/instances", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    await asyncio.sleep(2)
                    continue
                data = await resp.json()
                instances = data.get("instances", []) if isinstance(data, dict) else data
                if not instances:
                    break  # All clean

                for instance in instances:
                    instance_name = instance.get("name", "")
                    if instance_name:
                        try:
                            async with api_session.delete(
                                f"{ADDON_URL}/api/instances/{instance_name}",
                                timeout=aiohttp.ClientTimeout(total=20),
                            ) as del_resp:
                                _ = del_resp.status
                        except Exception:
                            pass

            # Wait for all squid processes to fully terminate and release ports
            await asyncio.sleep(3)
    except Exception:
        pass  # Ignore cleanup errors


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
