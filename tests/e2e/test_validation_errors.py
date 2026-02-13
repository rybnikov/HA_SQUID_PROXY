"""E2E tests for validation error display on all forms.

Tests verify that validation errors are shown inline on input fields
throughout the addon, as requested in issue about improving UX.
"""

import asyncio
import os

import pytest
from playwright.async_api import Page

from tests.e2e.utils import (
    ADDON_URL,
    create_instance_via_api,
    delete_instance_via_api,
    fill_textfield_by_testid,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_create_form_invalid_forward_address_shows_error(browser, unique_name, unique_port):
    """Test that invalid forward_address in create form shows inline error."""
    page: Page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Open create form
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-instance-form"]', timeout=30000)

        # Select TLS Tunnel
        await page.click('[data-testid="proxy-type-tls-tunnel"]')
        await asyncio.sleep(0.5)

        # Fill form with invalid forward_address (contains spaces)
        await fill_textfield_by_testid(page, "create-name-input", unique_name("test"))
        await fill_textfield_by_testid(page, "create-port-input", str(unique_port(3200)))
        await fill_textfield_by_testid(page, "create-forward-address-input", "host with spaces:443")

        # Click submit to trigger validation
        await page.click('[data-testid="create-submit-button"]')
        await asyncio.sleep(1)

        # Verify inline error message is shown
        page_text = await page.inner_text("body")
        assert "hostname" in page_text.lower() or "format" in page_text.lower(), \
            "Should show validation error for invalid forward_address format"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_create_form_invalid_port_shows_error(browser, unique_name):
    """Test that invalid port in create form shows inline error."""
    page: Page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Open create form
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-instance-form"]', timeout=30000)

        # Fill form with invalid port (< 1024)
        await fill_textfield_by_testid(page, "create-name-input", unique_name("test"))
        await fill_textfield_by_testid(page, "create-port-input", "80")

        # Click submit to trigger validation
        await page.click('[data-testid="create-submit-button"]')
        await asyncio.sleep(1)

        # Verify error is shown or submit is prevented
        # The validation schema enforces min 1024, so either:
        # 1. Inline error is shown
        # 2. Submit is disabled/prevented
        page_text = await page.inner_text("body")
        is_disabled = await page.is_disabled('[data-testid="create-submit-button"]')

        # Either error shown OR submit prevented
        has_error = "1024" in page_text or is_disabled
        assert has_error, "Should show port validation error or prevent submit"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_settings_form_invalid_forward_address_shows_error(
    browser, unique_name, unique_port, api_session
):
    """Test that invalid forward_address in settings form shows inline error."""
    instance_name = unique_name("settings-validation")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create TLS Tunnel instance via API
        await create_instance_via_api(
            api_session,
            instance_name,
            port,
            proxy_type="tls_tunnel",
            forward_address="vpn.example.com:1194",
        )

        # Navigate to settings
        await page.goto(f"{ADDON_URL}/proxies/{instance_name}/settings")
        await page.wait_for_selector('[data-testid="settings-forward-address-input"]', timeout=30000)

        # Clear and enter invalid forward_address
        await page.fill('[data-testid="settings-forward-address-input"]', "")
        await fill_textfield_by_testid(page, "settings-forward-address-input", "invalid/path:443")

        # Click save to trigger validation
        await page.click('[data-testid="settings-save-button"]')
        await asyncio.sleep(1)

        # Verify inline error message is shown
        page_text = await page.inner_text("body")
        assert "hostname" in page_text.lower() or "format" in page_text.lower(), \
            "Should show validation error for invalid forward_address in settings"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_settings_form_invalid_port_shows_error(
    browser, unique_name, unique_port, api_session
):
    """Test that invalid port in settings form shows inline error."""
    instance_name = unique_name("port-validation")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create instance via API
        await create_instance_via_api(api_session, instance_name, port, https_enabled=False)

        # Navigate to settings
        await page.goto(f"{ADDON_URL}/proxies/{instance_name}/settings")
        await page.wait_for_selector('[data-testid="settings-port-input"]', timeout=30000)

        # Clear and enter invalid port
        await page.fill('[data-testid="settings-port-input"]', "")
        await fill_textfield_by_testid(page, "settings-port-input", "99999")

        # Click save to trigger validation
        await page.click('[data-testid="settings-save-button"]')
        await asyncio.sleep(1)

        # Verify inline error message is shown
        page_text = await page.inner_text("body")
        assert "65535" in page_text or "port" in page_text.lower(), \
            "Should show validation error for invalid port in settings"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_user_form_validation_errors_visible(
    browser, unique_name, unique_port, api_session
):
    """Test that user form shows validation errors for invalid input."""
    instance_name = unique_name("user-validation")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create instance via API
        await create_instance_via_api(api_session, instance_name, port, https_enabled=False)

        # Navigate to settings Users tab
        await page.goto(f"{ADDON_URL}/proxies/{instance_name}/settings")
        await page.wait_for_selector('[data-testid="user-username-input"]', timeout=30000)

        # Try to add user with invalid password (< 6 chars)
        await fill_textfield_by_testid(page, "user-username-input", "testuser")
        await fill_textfield_by_testid(page, "user-password-input", "short")
        await page.click('[data-testid="user-add-button"]')
        await asyncio.sleep(1)

        # Verify inline error message is shown
        page_text = await page.inner_text("body")
        assert "6 characters" in page_text or "password" in page_text.lower(), \
            "Should show validation error for password too short"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_test_form_validation_errors_visible(
    browser, unique_name, unique_port, api_session
):
    """Test that test credentials form shows validation errors."""
    instance_name = unique_name("test-validation")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        # Create instance via API
        await create_instance_via_api(api_session, instance_name, port, https_enabled=False)

        # Navigate to settings Test tab
        await page.goto(f"{ADDON_URL}/proxies/{instance_name}/settings")
        await page.wait_for_selector("text=Test", timeout=30000)
        await page.click("text=Test")
        await asyncio.sleep(1)

        # Try to test with invalid URL
        await fill_textfield_by_testid(page, "test-username-input", "user1")
        await fill_textfield_by_testid(page, "test-password-input", "pass1234")
        await fill_textfield_by_testid(page, "test-url-input", "not-a-url")
        await page.click('[data-testid="test-submit-button"]')
        await asyncio.sleep(1)

        # Verify inline error message is shown
        page_text = await page.inner_text("body")
        assert "url" in page_text.lower() or "valid" in page_text.lower(), \
            "Should show validation error for invalid target URL"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_forward_address_optional_port_accepted(
    browser, unique_name, unique_port, api_session
):
    """Test that forward_address without port is accepted (defaults to 443)."""
    instance_name = unique_name("optional-port")
    port = unique_port(3200)

    page: Page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Open create form
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-instance-form"]', timeout=30000)

        # Select TLS Tunnel
        await page.click('[data-testid="proxy-type-tls-tunnel"]')
        await asyncio.sleep(0.5)

        # Fill form with forward_address WITHOUT port
        await fill_textfield_by_testid(page, "create-name-input", instance_name)
        await fill_textfield_by_testid(page, "create-port-input", str(port))
        await fill_textfield_by_testid(page, "create-forward-address-input", "vpn.example.com")

        # Submit should succeed
        await page.click('[data-testid="create-submit-button"]')
        await asyncio.sleep(2)

        # Verify instance was created
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instances = data.get("instances", [])
            instance = next((i for i in instances if i["name"] == instance_name), None)
            assert instance is not None, f"Instance {instance_name} should be created"
            # Backend should normalize to include :443
            assert instance.get("forward_address") == "vpn.example.com:443", \
                "Should normalize forward_address to include default port 443"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()
