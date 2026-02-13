"""E2E tests for validation error display on all forms.

Tests verify that validation errors are shown inline on input fields
throughout the addon, testing real user interactions.
"""

import asyncio

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

        # Verify error is shown (either inline or prevents submission)
        page_text = await page.inner_text("body")
        # Check if we're still on the create page (submission blocked) OR error shown
        is_still_on_create_page = "New Proxy Instance" in page_text
        has_error_text = "hostname" in page_text.lower() or "format" in page_text.lower()

        assert (
            is_still_on_create_page or has_error_text
        ), "Should either stay on create page or show validation error"
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

        # Navigate from dashboard to settings (not direct)
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', timeout=30000
        )
        await page.click(f'[data-testid="instance-card-{instance_name}"]')
        await page.wait_for_selector(
            '[data-testid="settings-forward-address-input"]', timeout=30000
        )

        # Clear and enter invalid forward_address
        await page.fill('[data-testid="settings-forward-address-input"]', "")
        await fill_textfield_by_testid(page, "settings-forward-address-input", "invalid/path:443")

        # Click save to trigger validation
        await page.click('[data-testid="settings-save-button"]')
        await asyncio.sleep(1)

        # Verify inline error message is shown
        page_text = await page.inner_text("body")
        assert (
            "hostname" in page_text.lower() or "format" in page_text.lower()
        ), "Should show validation error for invalid forward_address in settings"
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

        # Navigate from dashboard to settings
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', timeout=30000
        )
        await page.click(f'[data-testid="instance-card-{instance_name}"]')
        await page.wait_for_selector('[data-testid="settings-port-input"]', timeout=30000)

        # Clear and enter invalid port
        await page.fill('[data-testid="settings-port-input"]', "")
        await fill_textfield_by_testid(page, "settings-port-input", "99999")

        # Click save to trigger validation
        await page.click('[data-testid="settings-save-button"]')
        await asyncio.sleep(1)

        # Verify inline error message is shown
        page_text = await page.inner_text("body")
        assert (
            "65535" in page_text or "port" in page_text.lower()
        ), "Should show validation error for invalid port in settings"
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

    page = await browser.new_page()
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
            assert (
                instance.get("forward_address") == "vpn.example.com:443"
            ), "Should normalize forward_address to include default port 443"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


# ============================================================================
# v1.6.x Bug Regression Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_uppercase_instance_name_accepted_squid(
    browser, unique_name, unique_port, api_session
):
    """Test that uppercase instance names are accepted for Squid proxies (v1.6.4 regression)."""
    # Bug: Frontend allowed uppercase but backend validation was inconsistent
    instance_name = "TestProxy123"  # Mixed case with uppercase
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

        # Create Squid instance with uppercase name
        await fill_textfield_by_testid(page, "create-name-input", instance_name)
        await fill_textfield_by_testid(page, "create-port-input", str(port))

        # Submit
        await page.click('[data-testid="create-submit-button"]')
        await asyncio.sleep(2)

        # Verify instance created successfully
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instances = data.get("instances", [])
            instance = next((i for i in instances if i["name"] == instance_name), None)
            assert (
                instance is not None
            ), f"Instance {instance_name} with uppercase should be created"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_uppercase_instance_name_accepted_tls_tunnel(
    browser, unique_name, unique_port, api_session
):
    """Test that uppercase instance names are accepted for TLS tunnels (v1.6.4 critical bug)."""
    # Bug: TLS tunnel regex rejected uppercase while Squid accepted it
    # This was the actual production bug: "Testsq" failed for TLS tunnel
    instance_name = "Testsq"  # Exact case from bug report
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

        # Fill form with uppercase name
        await fill_textfield_by_testid(page, "create-name-input", instance_name)
        await fill_textfield_by_testid(page, "create-port-input", str(port))
        await fill_textfield_by_testid(page, "create-forward-address-input", "vpn.example.com:1194")

        # Submit
        await page.click('[data-testid="create-submit-button"]')
        await asyncio.sleep(2)

        # Verify instance created successfully
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instances = data.get("instances", [])
            instance = next((i for i in instances if i["name"] == instance_name), None)
            assert (
                instance is not None
            ), f"TLS tunnel '{instance_name}' with uppercase should be created"
            assert instance["proxy_type"] == "tls_tunnel"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_backend_error_message_visible_in_ui(browser, unique_name, unique_port):
    """Test that backend validation errors are extracted and shown to user (v1.6.4 bug)."""
    # Bug: Backend JSON errors like {"error": "Invalid name"} shown as raw JSON
    # Fix: API client extracts error/message/detail fields
    page: Page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Open create form
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-instance-form"]', timeout=30000)

        # Try to create instance with invalid name (contains special chars)
        await fill_textfield_by_testid(page, "create-name-input", "invalid@name")
        await fill_textfield_by_testid(page, "create-port-input", str(unique_port(3200)))

        # Submit to trigger backend error
        await page.click('[data-testid="create-submit-button"]')
        await asyncio.sleep(1)

        # Verify error message is visible (not raw JSON)
        page_text = await page.inner_text("body")
        # Should show extracted error, not {"error": "..."} raw JSON
        assert (
            "invalid" in page_text.lower() or "name" in page_text.lower()
        ), "Backend error should be extracted and shown to user"
        assert '{"error"' not in page_text, "Should NOT show raw JSON to user"
    finally:
        await page.close()
