"""E2E tests for OpenVPN config patcher dialog feature.

Tests the full user flow:
1. Create Squid/TLS tunnel instance
2. Navigate to instance settings
3. Open OpenVPN patcher dialog from Test Connectivity (Squid) or Connection Info (TLS)
4. Upload .ovpn file in dialog
5. Patch config in dialog
6. Download patched config
"""

import asyncio
import os
from pathlib import Path

import pytest

from tests.e2e.utils import (
    create_instance_via_ui,
    navigate_to_settings,
    wait_for_instance_running,
)

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "dev_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_ovpn"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_and_patch_ovpn_squid(browser, unique_name, unique_port, api_session):
    """E2E test: Upload and patch .ovpn file for Squid instance via dialog.

    User Flow:
    1. Create Squid instance
    2. Navigate to instance settings
    3. Navigate to Test Connectivity tab
    4. Click "Patch OpenVPN Config" button to open dialog
    5. Upload .ovpn file in dialog
    6. Click patch button in dialog
    7. Verify patched content preview appears in dialog
    8. Verify download button enabled in dialog
    """
    instance_name = unique_name("ovpn-squid")
    port = unique_port(3400)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create Squid instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Wait for instance to be running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 2: Navigate to instance settings
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', timeout=30000
        )
        await navigate_to_settings(page, instance_name)

        # Step 3: Click "Patch OpenVPN Config" button (in Test Connectivity card)
        await page.wait_for_selector(
            '[data-testid="test-connectivity-openvpn-button"]', timeout=10000
        )
        await page.click('[data-testid="test-connectivity-openvpn-button"]')

        # Wait for dialog to appear
        await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

        # Verify dialog title
        dialog_title = await page.query_selector('[data-testid="openvpn-dialog"] h2')
        title_text = await dialog_title.inner_text() if dialog_title else ""
        assert "OpenVPN" in title_text, "Dialog should show OpenVPN title"

        # Step 5: Upload .ovpn file in dialog
        ovpn_file_path = FIXTURES_DIR / "basic_client.ovpn"
        assert ovpn_file_path.exists(), f"Test fixture not found: {ovpn_file_path}"

        file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(str(ovpn_file_path))

        # Wait for file name to appear (file info display shows filename + size)
        await page.wait_for_selector("text=/basic_client.ovpn/", timeout=10000)

        # Step 6: Click patch button in dialog
        patch_button = await page.query_selector('[data-testid="openvpn-patch-button"]')
        assert patch_button, "Patch button not found in dialog"

        # Verify button is enabled
        is_disabled = await patch_button.get_attribute("disabled")
        assert is_disabled is None, "Patch button should be enabled after file upload"

        await patch_button.click()

        # Step 7: Wait for either preview or error message
        try:
            await page.wait_for_selector(
                '[data-testid="openvpn-preview"], .error-color, [style*="error-color"]',
                timeout=15000,
            )
        except Exception:
            # If timeout, take screenshot for debugging
            page_content = await page.content()
            raise AssertionError(f"Neither preview nor error appeared. Page HTML: {page_content[:500]}")

        # Check if error appeared instead of preview
        error_element = await page.query_selector('[style*="error-color"]')
        if error_element:
            error_text = await error_element.inner_text()
            raise AssertionError(f"API error occurred: {error_text}")

        # Wait for preview to be visible
        await page.wait_for_selector(
            '[data-testid="openvpn-preview"]', state="visible", timeout=5000
        )

        # Verify preview contains http-proxy directive
        preview = await page.query_selector('[data-testid="openvpn-preview"]')
        preview_content = await preview.input_value()
        assert (
            "http-proxy" in preview_content
        ), "Patched content should contain http-proxy directive"
        assert (
            "localhost" in preview_content or "127.0.0.1" in preview_content
        ), "Patched content should contain proxy host"
        assert str(port) in preview_content, f"Patched content should contain port {port}"

        # Verify original content is preserved
        assert "client" in preview_content, "Original 'client' directive should be preserved"
        assert "dev tun" in preview_content, "Original 'dev tun' directive should be preserved"

        # Step 8: Verify download button is enabled in dialog
        download_button = await page.query_selector('[data-testid="openvpn-download"]')
        assert download_button, "Download button should appear after successful patch"

        is_disabled = await download_button.get_attribute("disabled")
        assert is_disabled is None, "Download button should be enabled"

        # Verify copy button is also enabled
        copy_button = await page.query_selector('[data-testid="openvpn-copy"]')
        assert copy_button, "Copy button should appear after successful patch"

        # Close dialog
        close_button = await page.query_selector('[data-testid="openvpn-dialog-close"]')
        await close_button.click()

        # Verify dialog closed
        await asyncio.sleep(0.5)
        dialog = await page.query_selector('[data-testid="openvpn-dialog"]')
        assert dialog is None, "Dialog should close after clicking close button"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_and_patch_ovpn_tls_tunnel(browser, unique_name, unique_port, api_session):
    """E2E test: Upload and patch .ovpn file for TLS Tunnel instance via dialog.

    User Flow:
    1. Create TLS Tunnel instance
    2. Navigate to instance settings
    3. Navigate to Connection Info tab
    4. Click "Patch OpenVPN Config" button to open dialog
    5. Upload .ovpn file with remote directive in dialog
    6. Click patch button in dialog
    7. Verify patched content has tunnel endpoint in dialog
    8. Verify instance forward_address updated
    """
    instance_name = unique_name("ovpn-tls")
    port = unique_port(4500)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create TLS Tunnel instance
        await page.wait_for_selector('[data-testid="empty-state-add-button"]', timeout=30000)
        await page.click('[data-testid="empty-state-add-button"]')

        # Wait for navigation to create page
        await page.wait_for_url("**/proxies/new", timeout=10000)

        # Fill in instance details
        await page.wait_for_selector('[data-testid="instance-name-input"]', timeout=10000)
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))

        # Select TLS Tunnel proxy type
        proxy_type_select = await page.query_selector('[data-testid="proxy-type-select"]')
        if proxy_type_select:
            await page.select_option('[data-testid="proxy-type-select"]', value="tls_tunnel")
        else:
            # If using custom select component
            await page.click('[data-testid="proxy-type-select"]')
            await asyncio.sleep(0.5)
            await page.click('text="TLS Tunnel"')

        # Submit form
        await page.click('[data-testid="instance-submit-button"]')

        # Wait for redirect to dashboard
        await asyncio.sleep(2)
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', timeout=30000
        )

        # Wait for instance to be running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 2: Navigate to instance settings
        await navigate_to_settings(page, instance_name)

        # Step 3: Click "Patch OpenVPN Config" button (in Connection Info card)
        await page.wait_for_selector(
            '[data-testid="connection-info-openvpn-button"]', timeout=10000
        )
        await page.click('[data-testid="connection-info-openvpn-button"]')

        # Wait for dialog to appear
        await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

        # Step 5: Upload .ovpn file with remote directive in dialog
        ovpn_file_path = FIXTURES_DIR / "tls_tunnel_config.ovpn"
        assert ovpn_file_path.exists(), f"Test fixture not found: {ovpn_file_path}"

        file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(str(ovpn_file_path))

        await page.wait_for_selector("text=/tls_tunnel_config.ovpn/", timeout=10000)

        # Verify auth section NOT shown for TLS tunnel
        auth_toggle = await page.query_selector('[data-testid="openvpn-auth-toggle"]')
        assert auth_toggle is None, "Auth toggle should NOT appear for TLS tunnel instances"

        # Step 6: Click patch button in dialog
        patch_button = await page.query_selector('[data-testid="openvpn-patch-button"]')

        # Button text should say "Extract & Patch" for TLS tunnel
        button_text = await patch_button.inner_text()
        assert "Extract" in button_text, "Button should show 'Extract & Patch' for TLS tunnel"

        await patch_button.click()

        # Step 7: Wait for patched content in dialog
        await page.wait_for_selector('[data-testid="openvpn-preview"]', timeout=15000)

        preview = await page.query_selector('[data-testid="openvpn-preview"]')
        preview_content = await preview.input_value()

        # Verify remote directive was replaced with tunnel endpoint
        assert (
            "remote localhost" in preview_content or "remote 127.0.0.1" in preview_content
        ), "Patched content should have tunnel endpoint as remote"
        assert str(port) in preview_content, f"Patched content should contain tunnel port {port}"

        # Original VPN server should NOT be in the patched config
        assert (
            "vpn-server.example.org" not in preview_content
        ), "Original VPN server should be replaced"

        # Step 8: Verify instance forward_address updated via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            assert resp.status == 200
            data = await resp.json()
            instances = data.get("instances", [])
            tls_instance = next((i for i in instances if i["name"] == instance_name), None)
            assert tls_instance, f"Instance {instance_name} not found in API response"

            # Verify forward_address extracted from .ovpn
            forward_address = tls_instance.get("forward_address")
            assert (
                forward_address == "vpn-server.example.org:443"
            ), f"Expected forward_address to be 'vpn-server.example.org:443', got '{forward_address}'"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ovpn_with_auth_credentials(browser, unique_name, unique_port, api_session):
    """E2E test: Patch .ovpn with authentication credentials via dialog.

    User Flow:
    1. Create Squid instance with user
    2. Navigate to Test Connectivity tab
    3. Open OpenVPN dialog
    4. Upload .ovpn file
    5. Enable auth toggle (HASwitch)
    6. Enter username/password
    7. Patch config
    8. Verify auth block in patched content
    """
    instance_name = unique_name("ovpn-auth")
    port = unique_port(3500)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create Squid instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Add a user via API
        async with api_session.post(
            f"{ADDON_URL}/api/instances/{instance_name}/users",
            json={"username": "testuser", "password": "testpass"},
        ) as resp:
            assert resp.status == 200, "Failed to add user"

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 2: Navigate to instance settings
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', timeout=30000
        )
        await navigate_to_settings(page, instance_name)

        # Step 3: Open OpenVPN dialog (in Test Connectivity card)
        await page.wait_for_selector(
            '[data-testid="test-connectivity-openvpn-button"]', timeout=10000
        )
        await page.click('[data-testid="test-connectivity-openvpn-button"]')
        await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

        # Step 4: Upload file
        ovpn_file_path = FIXTURES_DIR / "basic_client.ovpn"
        file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(str(ovpn_file_path))
        await page.wait_for_selector("text=/basic_client.ovpn/", timeout=10000)

        # Step 5: Enable auth toggle (HASwitch)
        auth_toggle = await page.query_selector('[data-testid="openvpn-auth-toggle"]')
        assert auth_toggle, "Auth toggle should be visible for Squid instances"
        await auth_toggle.click()

        # Step 6: Enter credentials
        await page.wait_for_selector('[data-testid="openvpn-username-input"]', timeout=5000)

        # Verify user select dropdown appears (populated with instance users)
        user_select = await page.query_selector('[data-testid="openvpn-user-select"]')
        assert user_select, "User select dropdown should appear when auth enabled"

        # Fill username and password fields
        await page.fill('[data-testid="openvpn-username-input"] input', "testuser")
        await page.fill('[data-testid="openvpn-password-input"] input', "testpass")

        # Step 7: Patch config
        await page.click('[data-testid="openvpn-patch-button"]')
        await page.wait_for_selector('[data-testid="openvpn-preview"]', timeout=15000)

        # Step 8: Verify auth block in patched content
        preview = await page.query_selector('[data-testid="openvpn-preview"]')
        preview_content = await preview.input_value()

        assert (
            "<http-proxy-user-pass>" in preview_content
        ), "Patched content should contain auth block start"
        assert (
            "</http-proxy-user-pass>" in preview_content
        ), "Patched content should contain auth block end"
        assert "testuser" in preview_content, "Patched content should contain username"
        assert "testpass" in preview_content, "Patched content should contain password"

    finally:
        await page.close()
