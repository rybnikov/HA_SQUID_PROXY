"""E2E tests for DPI UX rework features.

Tests for:
- Proxy type badges (Squid blue, TLS Tunnel green)
- TLS Tunnel routing diagram visibility
- TLS Tunnel test tab (cover site & VPN forwarding tests)
- Nginx logs for TLS Tunnel
- No DPI toggle for Squid
- Rate limiting configuration
"""

import asyncio

import pytest
from playwright.async_api import Page

from .utils import (
    ADDON_URL,
    create_instance_via_api,
    delete_instance_via_api,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_proxy_type_badges_visible(browser, unique_name, unique_port, api_session):
    """Test that proxy type badges are visible on dashboard cards."""
    squid_name = unique_name("squid-badge-test")
    tls_name = unique_name("tls-badge-test")
    squid_port = unique_port(3200)
    tls_port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create a Squid instance
        await create_instance_via_api(api_session, squid_name, squid_port, https_enabled=False)

        # Create a TLS Tunnel instance
        await create_instance_via_api(
            api_session,
            tls_name,
            tls_port,
            proxy_type="tls_tunnel",
            forward_address="vpn.example.com:1194",
        )

        # Navigate to dashboard
        await page.goto(ADDON_URL)
        await page.wait_for_selector(f'[data-testid="instance-card-{squid_name}"]', timeout=30000)

        # Check Squid badge
        squid_badge = page.locator(f'[data-testid="instance-type-badge-{squid_name}"]')
        assert await squid_badge.count() > 0, "Squid badge should be visible"
        squid_text = await squid_badge.inner_text()
        assert (
            "Squid Proxy" in squid_text
        ), f"Squid badge should say 'Squid Proxy', got: {squid_text}"

        # Check Squid badge color (blue)
        squid_bg = await squid_badge.evaluate("el => getComputedStyle(el).backgroundColor")
        assert (
            "3, 169, 244" in squid_bg or "rgb(3, 169, 244)" in squid_bg
        ), f"Squid badge should have blue background, got: {squid_bg}"

        # Check TLS Tunnel badge
        tls_badge = page.locator(f'[data-testid="instance-type-badge-{tls_name}"]')
        assert await tls_badge.count() > 0, "TLS Tunnel badge should be visible"
        tls_text = await tls_badge.inner_text()
        assert (
            "TLS Tunnel" in tls_text
        ), f"TLS Tunnel badge should say 'TLS Tunnel', got: {tls_text}"

        # Check TLS Tunnel badge color (green)
        tls_bg = await tls_badge.evaluate("el => getComputedStyle(el).backgroundColor")
        assert (
            "76, 175, 80" in tls_bg or "rgb(76, 175, 80)" in tls_bg
        ), f"TLS Tunnel badge should have green background, got: {tls_bg}"

    finally:
        await delete_instance_via_api(api_session, squid_name)
        await delete_instance_via_api(api_session, tls_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_no_dpi_toggle_for_squid(browser, unique_name, unique_port):
    """Test that DPI prevention toggle is not visible when creating Squid instances."""
    page: Page = await browser.new_page()
    try:
        # Navigate to dashboard first, then click to create
        await page.goto(ADDON_URL)
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-instance-form"]', timeout=30000)
        await page.wait_for_selector('[data-testid="proxy-type-squid"]', timeout=30000)

        # Ensure Squid is selected
        await page.click('[data-testid="proxy-type-squid"]')
        await asyncio.sleep(0.5)

        # DPI toggle should NOT exist
        dpi_toggle = page.locator('[data-testid="create-dpi-switch"]')
        assert await dpi_toggle.count() == 0, "DPI toggle should not be visible for Squid instances"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_routing_diagram_visible(browser, unique_name, unique_port):
    """Test that TLS Tunnel routing diagram is visible on create page."""
    page: Page = await browser.new_page()
    try:
        # Navigate to dashboard first, then click to create
        await page.goto(ADDON_URL)
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-instance-form"]', timeout=30000)
        await page.wait_for_selector('[data-testid="proxy-type-tls-tunnel"]', timeout=30000)

        # Select TLS Tunnel
        await page.click('[data-testid="proxy-type-tls-tunnel"]')
        await asyncio.sleep(0.5)

        # Check for routing diagram text
        page_text = await page.inner_text("body")
        assert "How TLS Tunnel Works" in page_text, "TLS Tunnel routing diagram should be visible"
        assert (
            "Cover Website" in page_text or "VPN Server" in page_text
        ), "Routing diagram should explain dual-destination behavior"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_field_labels(browser, unique_name, unique_port):
    """Test that TLS Tunnel has improved field labels and helper text."""
    page: Page = await browser.new_page()
    try:
        # Navigate to dashboard first, then click to create
        await page.goto(ADDON_URL)
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-instance-form"]', timeout=30000)
        await page.wait_for_selector('[data-testid="proxy-type-tls-tunnel"]', timeout=30000)

        # Select TLS Tunnel
        await page.click('[data-testid="proxy-type-tls-tunnel"]')
        await asyncio.sleep(0.5)

        # Check for improved labels
        page_text = await page.inner_text("body")
        assert (
            "VPN Server Destination" in page_text or "VPN" in page_text
        ), "Should have 'VPN Server Destination' label"
        assert "Cover Domain" in page_text, "Should have 'Cover Domain' field"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_test_tab_exists(browser, unique_name, unique_port, api_session):
    """Test that TLS Tunnel instances have a Test tab with test buttons."""
    instance_name = unique_name("tls-test-tab")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create TLS Tunnel instance
        await create_instance_via_api(
            api_session,
            instance_name,
            port,
            proxy_type="tls_tunnel",
            forward_address="127.0.0.1:22",  # SSH port for VPN forward test
        )

        # Navigate to instance settings
        await page.goto(f"{ADDON_URL}/proxies/{instance_name}/settings")
        await page.wait_for_selector("text=Test", timeout=30000)

        # Click Test tab
        await page.click("text=Test")
        await asyncio.sleep(1)

        # Check for test buttons
        page_text = await page.inner_text("body")
        assert (
            "Test Cover Site" in page_text or "Cover Site" in page_text
        ), "Should have 'Test Cover Site' button"
        assert (
            "Test VPN Forwarding" in page_text or "VPN Forwarding" in page_text
        ), "Should have 'Test VPN Forwarding' button"

    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_nginx_logs_tab(browser, unique_name, unique_port, api_session):
    """Test that TLS Tunnel instances show Nginx logs tab."""
    instance_name = unique_name("tls-nginx-logs")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create TLS Tunnel instance
        await create_instance_via_api(
            api_session,
            instance_name,
            port,
            proxy_type="tls_tunnel",
            forward_address="vpn.example.com:1194",
        )

        # Navigate to instance settings
        await page.goto(f"{ADDON_URL}/proxies/{instance_name}/settings")
        await page.wait_for_selector("text=Logs", timeout=30000)

        # Click Logs tab
        await page.click("text=Logs")
        await asyncio.sleep(1)

        # Check for nginx logs
        page_text = await page.inner_text("body")
        assert (
            "Nginx" in page_text or "nginx" in page_text
        ), "Should show Nginx logs for TLS Tunnel instances"

    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_squid_instance_no_test_tab(browser, unique_name, unique_port, api_session):
    """Test that Squid instances do NOT have the TLS Tunnel test tab."""
    instance_name = unique_name("squid-no-test-tab")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create Squid instance
        await create_instance_via_api(api_session, instance_name, port, https_enabled=False)

        # Navigate to instance settings
        await page.goto(f"{ADDON_URL}/proxies/{instance_name}/settings")
        await asyncio.sleep(2)

        # Check that Test tab exists (for connectivity test)
        # But it should NOT have TLS-specific tests
        page_text = await page.inner_text("body")

        # Squid should have Test Credentials but not Test Cover Site
        if "Test" in page_text:
            await page.click("text=Test")
            await asyncio.sleep(1)
            page_text = await page.inner_text("body")
            assert (
                "Test Cover Site" not in page_text
            ), "Squid instances should not have TLS Tunnel test buttons"
            assert (
                "Test VPN Forwarding" not in page_text
            ), "Squid instances should not have TLS Tunnel test buttons"

    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_rate_limiting_default_value(browser, unique_name, unique_port, api_session):
    """Test that TLS Tunnel instances have default rate limit of 10."""
    instance_name = unique_name("rate-limit-default")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create TLS Tunnel instance without specifying rate_limit
        await create_instance_via_api(
            api_session,
            instance_name,
            port,
            proxy_type="tls_tunnel",
            forward_address="vpn.example.com:1194",
        )

        # Verify via API that rate_limit is 10
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instances = data.get("instances", [])
            instance = next((i for i in instances if i["name"] == instance_name), None)
            assert instance is not None, f"Instance {instance_name} not found"
            assert (
                instance.get("rate_limit") == 10
            ), f"Default rate_limit should be 10, got: {instance.get('rate_limit')}"

    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()
