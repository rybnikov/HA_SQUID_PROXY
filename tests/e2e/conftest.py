"""E2E Playwright fixtures using async API to avoid nested event loops."""

from __future__ import annotations

import pytest
from playwright.async_api import async_playwright


@pytest.fixture
async def browser():
    """Provide an async Playwright browser instance for E2E tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()
