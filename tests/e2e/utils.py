"""E2E test utility functions for Playwright operations with timeouts.

This module provides helper functions that wrap Playwright operations with
10-second timeout enforcement to ensure tests fail fast on slow interactions.
"""

from __future__ import annotations

from typing import Any, TypeVar

import aiohttp
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


async def fill_textfield_by_testid(
    page: Page,
    testid: str,
    text: str,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
) -> None:
    """Fill HA textfield through inner input selector, fallback to host event dispatch."""
    selector = f'[data-testid="{testid}"] input'
    if await page.locator(selector).count():
        await fill_with_timeout(page, selector, text, timeout=timeout)
        return

    host_selector = f'[data-testid="{testid}"]'
    await page.wait_for_selector(host_selector, state="attached", timeout=timeout)
    await page.eval_on_selector(
        host_selector,
        """(el, value) => {
            el.value = value;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        text,
    )


async def set_switch_state_by_testid(
    page: Page,
    testid: str,
    checked: bool,
    timeout: int = DEFAULT_ACTION_TIMEOUT,
) -> None:
    """Set HA switch state using Playwright's native check/uncheck.

    The HASwitch wrapper renders data-testid on a <span>.  Inside that span
    there is either a native <input type="checkbox"> (fallback) or an
    <ha-switch> custom element.

    For the fallback checkbox we use Playwright's set_checked() which
    simulates a real user click and properly triggers React's event system.
    For <ha-switch> we set the property and dispatch a change event.
    """
    import asyncio as _asyncio

    wrapper_selector = f'[data-testid="{testid}"]'
    await page.wait_for_selector(wrapper_selector, state="attached", timeout=timeout)

    # Try fallback checkbox first (most common in E2E without HA elements)
    checkbox_selector = f'[data-testid="{testid}"] input[type="checkbox"]'
    checkbox = page.locator(checkbox_selector)
    if await checkbox.count() > 0:
        await checkbox.set_checked(checked, timeout=timeout)
        await _asyncio.sleep(0.2)
        return

    # Fall back to ha-switch custom element
    await page.eval_on_selector(
        wrapper_selector,
        """(el, nextChecked) => {
            const switchEl = el.querySelector('ha-switch');
            if (switchEl) {
                switchEl.checked = Boolean(nextChecked);
                switchEl.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }""",
        checked,
    )
    await _asyncio.sleep(0.2)


async def create_instance_via_ui(
    page: Page,
    addon_url: str,
    name: str,
    port: int,
    https_enabled: bool = False,
    timeout: int = 60000,
) -> None:
    """Create an instance via the UI create form.

    Navigates to create page, fills form, submits, and waits for
    the instance card to appear on the dashboard.
    """
    await page.click('[data-testid="add-instance-button"]')
    await page.wait_for_selector('[data-testid="create-name-input"]', timeout=10000)

    await fill_textfield_by_testid(page, "create-name-input", name)
    await fill_textfield_by_testid(page, "create-port-input", str(port))

    if https_enabled:
        await set_switch_state_by_testid(page, "create-https-switch", True)
        import asyncio as _asyncio

        await _asyncio.sleep(0.3)

    await page.click('[data-testid="create-submit-button"]')

    await page.wait_for_selector(f'[data-testid="instance-card-{name}"]', timeout=timeout)


async def create_tls_tunnel_via_ui(
    page: Page,
    addon_url: str,
    name: str,
    port: int,
    forward_address: str,
    cover_domain: str = "",
    timeout: int = 60000,
) -> None:
    """Create a TLS Tunnel instance via the UI create form.

    Navigates to create page, selects TLS Tunnel type, fills required fields,
    submits, and waits for the instance card to appear on the dashboard.

    Args:
        page: Playwright page object
        addon_url: Base URL of the addon
        name: Instance name
        port: Listen port
        forward_address: VPN server address (required for TLS tunnel)
        cover_domain: Cover domain for the cover website SSL cert (optional)
        timeout: Max wait time for instance card to appear
    """
    import asyncio as _asyncio

    await page.click('[data-testid="add-instance-button"]')
    await page.wait_for_selector('[data-testid="create-name-input"]', timeout=10000)

    # Select TLS Tunnel proxy type
    await page.click('[data-testid="proxy-type-tls-tunnel"]')
    await _asyncio.sleep(0.3)

    await fill_textfield_by_testid(page, "create-name-input", name)
    await fill_textfield_by_testid(page, "create-port-input", str(port))
    await fill_textfield_by_testid(page, "create-forward-address-input", forward_address)

    if cover_domain:
        await fill_textfield_by_testid(page, "create-cover-domain-input", cover_domain)

    await page.click('[data-testid="create-submit-button"]')

    await page.wait_for_selector(f'[data-testid="instance-card-{name}"]', timeout=timeout)


async def navigate_to_settings(
    page: Page,
    instance_name: str,
    timeout: int = 10000,
) -> None:
    """Navigate to instance settings page by clicking the settings gear icon."""
    await page.click(f'[data-testid="instance-settings-chip-{instance_name}"]')
    await page.wait_for_selector('[data-testid="settings-tabs"]', timeout=timeout)


async def navigate_to_dashboard(
    page: Page,
    addon_url: str,
    timeout: int = 10000,
) -> None:
    """Navigate back to dashboard."""
    await page.goto(addon_url)
    await page.wait_for_selector('[data-testid="add-instance-button"]', timeout=timeout)


async def wait_for_instance_running(
    page: Page,
    addon_url: str,
    api_session: Any,
    instance_name: str,
    timeout: int = 60000,
) -> None:
    """Wait for an instance to reach running state via API polling.

    Default 60s to handle container degradation during full suite runs.
    """
    import asyncio

    max_attempts = timeout // 2000
    for _ in range(max_attempts):
        try:
            async with api_session.get(
                f"{addon_url}/api/instances", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                if instance and instance.get("running"):
                    return
        except Exception:
            pass  # API might be slow during restart
        await asyncio.sleep(2)
    raise TimeoutError(f"Instance {instance_name} did not reach running state within {timeout}ms")


async def wait_for_instance_stopped(
    page: Page,
    addon_url: str,
    api_session: Any,
    instance_name: str,
    timeout: int = 60000,
) -> None:
    """Wait for an instance to reach stopped state via API polling.

    Default 60s to handle container degradation during full suite runs.
    """
    import asyncio

    max_attempts = timeout // 2000
    for _ in range(max_attempts):
        try:
            async with api_session.get(
                f"{addon_url}/api/instances", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                if instance and not instance.get("running"):
                    return
        except Exception:
            pass  # API might be slow during stop
        await asyncio.sleep(2)
    raise TimeoutError(f"Instance {instance_name} did not stop within {timeout}ms")


async def wait_for_addon_healthy(
    addon_url: str,
    api_session: Any,
    timeout: int = 60000,
) -> None:
    """Wait for the addon to be healthy and responding to API requests.

    Useful after operations that may cause the addon container to restart
    (e.g., certificate regeneration under load).
    """
    import asyncio

    max_attempts = timeout // 2000
    for _ in range(max_attempts):
        try:
            async with api_session.get(
                f"{addon_url}/api/instances", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass  # Connection refused, reset, etc.
        await asyncio.sleep(2)
    raise TimeoutError(f"Addon did not become healthy within {timeout}ms")


async def get_icon_color(page: Page, instance_name: str) -> str:
    """Get the status indicator background color for an instance card.

    The status indicator is a div with data-testid="instance-status-indicator-{name}"
    that changes background color based on running/stopped status.
    Reloads the dashboard first to ensure the UI reflects the latest backend state.
    """
    import asyncio

    # Reload to pick up latest state from react-query
    await page.reload()
    await page.wait_for_selector(f'[data-testid="instance-card-{instance_name}"]', timeout=30000)
    await asyncio.sleep(1)

    result: str = await page.evaluate(
        """(instanceName) => {
            const indicator = document.querySelector(`[data-testid="instance-status-indicator-${instanceName}"]`);
            if (!indicator) return '';
            return getComputedStyle(indicator).backgroundColor;
        }""",
        instance_name,
    )
    return result


def is_success_color(color: str) -> bool:
    """Check if color represents running/success (green).

    Matches CSS var(--success-color, #43a047) which computes to rgb(67, 160, 71) or rgba(67, 160, 71, ...).
    """
    color_lower = color.lower()
    return (
        "success" in color_lower
        or "43a047" in color_lower
        or "rgb(67, 160, 71)" in color_lower
        or "rgba(67, 160, 71" in color_lower  # Match rgba with any alpha value
    )


def is_error_color(color: str) -> bool:
    """Check if color represents stopped/inactive (gray in new UI design).

    New design uses gray for stopped instances: rgba(158, 158, 158, 0.15) background
    and var(--secondary-text-color, #9b9b9b) for the icon.
    Returns True for gray/secondary colors indicating stopped state.
    """
    color_lower = color.lower()
    # Check for gray/secondary colors (new design)
    return (
        "secondary" in color_lower
        or "9b9b9b" in color_lower
        or "158" in color_lower  # rgba(158, 158, 158, ...)
        or "rgb(158, 158, 158)" in color_lower
        or
        # Empty string also indicates no status (stopped)
        color_lower == ""
    )
