"""E2E test utility functions for Playwright operations with timeouts.

This module provides helper functions that wrap Playwright operations with
10-second timeout enforcement to ensure tests fail fast on slow interactions.
"""

from __future__ import annotations

from typing import Any, TypeVar

from playwright.async_api import Page

T = TypeVar("T")

# Default timeout for user actions (10 seconds)
DEFAULT_ACTION_TIMEOUT = 10_000  # milliseconds


async def click_with_timeout(
    page: Page,
    selector: str,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
    **kwargs: Any,
) -> None:
    """Click element with strict timeout.

    Args:
        page: Playwright page object
        selector: CSS selector for element
        timeout: Timeout in milliseconds (default 10s)
        **kwargs: Additional arguments for page.click()

    Raises:
        TimeoutError: If click takes longer than timeout
    """
    try:
        await page.click(selector, timeout=timeout, **kwargs)
    except Exception as e:
        if "timeout" in str(e).lower():
            raise TimeoutError(f"Click action on '{selector}' timed out after {timeout}ms") from e
        raise


async def fill_with_timeout(
    page: Page,
    selector: str,
    text: str,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
    **kwargs: Any,
) -> None:
    """Fill input field with strict timeout.

    Args:
        page: Playwright page object
        selector: CSS selector for input
        text: Text to fill
        timeout: Timeout in milliseconds (default 10s)
        **kwargs: Additional arguments for page.fill()

    Raises:
        TimeoutError: If fill takes longer than timeout
    """
    try:
        await page.fill(selector, text, timeout=timeout, **kwargs)
    except Exception as e:
        if "timeout" in str(e).lower():
            raise TimeoutError(f"Fill action on '{selector}' timed out after {timeout}ms") from e
        raise


async def check_with_timeout(
    page: Page,
    selector: str,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
    **kwargs: Any,
) -> None:
    """Check checkbox with strict timeout.

    Args:
        page: Playwright page object
        selector: CSS selector for checkbox
        timeout: Timeout in milliseconds (default 10s)
        **kwargs: Additional arguments for page.check()

    Raises:
        TimeoutError: If check takes longer than timeout
    """
    try:
        await page.check(selector, timeout=timeout, **kwargs)
    except Exception as e:
        if "timeout" in str(e).lower():
            raise TimeoutError(f"Check action on '{selector}' timed out after {timeout}ms") from e
        raise


async def uncheck_with_timeout(
    page: Page,
    selector: str,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
    **kwargs: Any,
) -> None:
    """Uncheck checkbox with strict timeout.

    Args:
        page: Playwright page object
        selector: CSS selector for checkbox
        timeout: Timeout in milliseconds (default 10s)
        **kwargs: Additional arguments for page.uncheck()

    Raises:
        TimeoutError: If uncheck takes longer than timeout
    """
    try:
        await page.uncheck(selector, timeout=timeout, **kwargs)
    except Exception as e:
        if "timeout" in str(e).lower():
            raise TimeoutError(f"Uncheck action on '{selector}' timed out after {timeout}ms") from e
        raise


async def select_option_with_timeout(
    page: Page,
    selector: str,
    value: str,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
    **kwargs: Any,
) -> None:
    """Select dropdown option with strict timeout.

    Args:
        page: Playwright page object
        selector: CSS selector for select element
        value: Option value to select
        timeout: Timeout in milliseconds (default 10s)
        **kwargs: Additional arguments for page.select_option()

    Raises:
        TimeoutError: If select_option takes longer than timeout
    """
    try:
        await page.select_option(selector, value, timeout=timeout, **kwargs)
    except Exception as e:
        if "timeout" in str(e).lower():
            raise TimeoutError(f"Select action on '{selector}' timed out after {timeout}ms") from e
        raise


async def wait_for_selector_with_timeout(
    page: Page,
    selector: str,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
    **kwargs: Any,
) -> None:
    """Wait for element selector with strict timeout.

    Args:
        page: Playwright page object
        selector: CSS selector to wait for
        timeout: Timeout in milliseconds (default 10s)
        **kwargs: Additional arguments for page.wait_for_selector()

    Raises:
        TimeoutError: If selector not found within timeout
    """
    try:
        await page.wait_for_selector(selector, timeout=timeout, **kwargs)
    except Exception as e:
        if "timeout" in str(e).lower():
            raise TimeoutError(f"Wait for selector '{selector}' timed out after {timeout}ms") from e
        raise


async def wait_for_function_with_timeout(
    page: Page,
    script: str,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
    **kwargs: Any,
) -> None:
    """Wait for JavaScript function to return true with strict timeout.

    Args:
        page: Playwright page object
        script: JavaScript code that returns boolean
        timeout: Timeout in milliseconds (default 10s)
        **kwargs: Additional arguments for page.wait_for_function()

    Raises:
        TimeoutError: If function doesn't return true within timeout
    """
    try:
        await page.wait_for_function(script, timeout=timeout, **kwargs)
    except Exception as e:
        if "timeout" in str(e).lower():
            raise TimeoutError(
                f"Wait for function timed out after {timeout}ms: {script[:50]}"
            ) from e
        raise
