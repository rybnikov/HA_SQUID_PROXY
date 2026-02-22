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
    create_instance_via_api,
    create_instance_via_ui,
    create_tls_tunnel_via_ui,
    fill_textfield_by_testid,
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

        # Enable request/response logging
        async def log_request(route, request):
            print(f"REQUEST: {request.method} {request.url}")
            await route.continue_()

        async def log_response(response):
            if "patch-ovpn" in response.url:
                print(f"RESPONSE: {response.status} {response.url}")
                try:
                    body = await response.text()
                    print(f"RESPONSE BODY: {body[:500]}")
                except Exception as e:
                    print(f"Could not read response body: {e}")

        await page.route("**/*", log_request)
        page.on("response", log_response)

        await patch_button.click()

        # Step 7: Wait for either preview or error message
        try:
            await page.wait_for_selector(
                '[data-testid="openvpn-preview"], [data-testid="error-card"]',
                timeout=15000,
            )
        except Exception:
            # If timeout, capture page content and console logs
            page_content = await page.content()
            console_logs = []
            page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
            raise AssertionError(
                f"Neither preview nor error appeared. Page HTML: {page_content[:1000]}"
            ) from None

        # Check if error appeared instead of preview
        error_card = await page.query_selector('[data-testid="error-card"]')
        if error_card:
            error_text = await error_card.inner_text()
            # Also capture what the actual API response was
            page_content = await page.content()
            raise AssertionError(
                f"API error occurred: {error_text}\n\nPage content sample: {page_content[:1000]}"
            )

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

        # Step 8: Verify download filename field and download button
        filename_input = await page.query_selector('[data-testid="openvpn-download-filename"]')
        assert filename_input, "Download filename input should appear after patch"

        download_button = await page.query_selector('[data-testid="openvpn-download"]')
        assert download_button, "Download button should appear after successful patch"

        is_disabled = await download_button.get_attribute("disabled")
        assert is_disabled is None, "Download button should be enabled"

        # Verify copy button is also enabled
        copy_button = await page.query_selector('[data-testid="openvpn-copy"]')
        assert copy_button, "Copy button should appear after successful patch"

        # Verify syntax highlighting overlay exists
        highlight_pre = await page.query_selector('[data-testid="openvpn-preview-highlight"]')
        assert highlight_pre, "Syntax highlighting pre overlay should exist"

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
    5. Fill external address in dialog
    6. Upload .ovpn file with remote directive in dialog
    7. Click patch button in dialog
    8. Verify patched content has tunnel endpoint and DPI settings
    9. Verify instance forward_address updated
    """
    instance_name = unique_name("ovpn-tls")
    port = unique_port(4500)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create TLS Tunnel instance using helper function
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="192.168.1.1:1194",  # Dummy VPN server for testing
            timeout=60000,
        )

        # Wait for instance to be running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 2: Navigate to instance settings
        await navigate_to_settings(page, instance_name)

        # Step 3: Click "Patch OpenVPN Config" button (in Connection Info card)
        patcher_button = page.locator('[data-testid="connection-info-openvpn-button"]')
        await patcher_button.scroll_into_view_if_needed()
        await patcher_button.wait_for(state="visible", timeout=10000)
        await patcher_button.click()

        # Wait for dialog to appear
        await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

        # Step 4: Fill external address in the dialog (required for TLS tunnel)
        await fill_textfield_by_testid(page, "openvpn-external-address-input", "tunnel.example.com")
        await asyncio.sleep(0.5)

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
        assert (
            "extract" in button_text.lower()
        ), "Button should show 'Extract & Patch' for TLS tunnel"

        await patch_button.click()

        # Step 7: Wait for patched content in dialog
        await page.wait_for_selector('[data-testid="openvpn-preview"]', timeout=15000)

        preview = await page.query_selector('[data-testid="openvpn-preview"]')
        preview_content = await preview.input_value()

        # Verify remote directive was replaced with tunnel endpoint
        assert (
            f"remote tunnel.example.com {port}" in preview_content
        ), f"Patched content should have 'remote tunnel.example.com {port}'"

        # Original VPN server should NOT be in the patched config
        assert (
            "vpn-server.example.org" not in preview_content
        ), "Original VPN server should be replaced"

        # Verify DPI evasion settings are present
        assert "proto tcp" in preview_content, "DPI: proto tcp should be present"
        assert "tun-mtu 1500" in preview_content, "DPI: tun-mtu should be present"
        assert "mssfix 1300" in preview_content, "DPI: mssfix should be present"
        assert "sndbuf 0" in preview_content, "DPI: sndbuf should be present"
        assert "rcvbuf 0" in preview_content, "DPI: rcvbuf should be present"
        assert (
            "connect-retry-max 100" in preview_content
        ), "DPI: connect-retry-max should be present"
        assert "float" in preview_content, "DPI: float should be present"

        # Verify DPI settings appear near the top (after remote, before verb)
        remote_idx = preview_content.index(f"remote tunnel.example.com {port}")
        dpi_comment_idx = preview_content.index("# DPI evasion settings")
        assert (
            dpi_comment_idx > remote_idx
        ), "DPI settings should appear right after remote directive"

        # Verify syntax highlighting overlay exists (embedded diff)
        highlight_pre = await page.query_selector('[data-testid="openvpn-preview-highlight"]')
        assert highlight_pre, "Syntax highlighting overlay should exist for diff display"

        # Verify download filename field exists
        filename_input = await page.query_selector('[data-testid="openvpn-download-filename"]')
        assert filename_input, "Download filename field should be present"

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
        # Step 1: Create Squid instance via API (faster — auth patching is the focus)
        await create_instance_via_api(api_session, instance_name, port, https_enabled=False)
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
        auth_toggle = await page.wait_for_selector(
            '[data-testid="openvpn-auth-toggle"]', timeout=5000
        )
        assert auth_toggle, "Auth toggle should be visible for Squid instances"
        await auth_toggle.click()

        # Step 6: Enter credentials
        await page.wait_for_selector('[data-testid="openvpn-username-input"]', timeout=5000)

        # Wait for user select dropdown (populated with instance users from async API fetch)
        user_select = await page.wait_for_selector(
            '[data-testid="openvpn-user-select"]', timeout=10000
        )
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


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ovpn_external_address_in_dialog(browser, unique_name, unique_port, api_session):
    """E2E test: External address is provided in the dialog, not in settings.

    Verifies:
    1. External address input exists in the patcher dialog
    2. For TLS tunnel, patch button is disabled without external address
    3. Filling external address enables the patch button
    4. External address is used in the patched config
    """
    instance_name = unique_name("ovpn-addr")
    port = unique_port(4600)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create TLS Tunnel instance
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="192.168.1.1:1194",
            timeout=60000,
        )
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings and open patcher dialog
        await navigate_to_settings(page, instance_name)
        patcher_button = page.locator('[data-testid="connection-info-openvpn-button"]')
        await patcher_button.scroll_into_view_if_needed()
        await patcher_button.wait_for(state="visible", timeout=10000)
        await patcher_button.click()
        await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

        # Verify external address input exists in dialog
        ext_input = await page.query_selector('[data-testid="openvpn-external-address-input"]')
        assert ext_input, "External address input should exist in the dialog"

        # Verify error card shows when external address is empty (TLS tunnel)
        error_card = await page.query_selector('[data-testid="openvpn-external-ip-error"]')
        assert error_card, "Error card should show when external address is empty for TLS tunnel"

        # Upload file first
        ovpn_file_path = FIXTURES_DIR / "tls_tunnel_config.ovpn"
        file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(str(ovpn_file_path))
        await page.wait_for_selector("text=/tls_tunnel_config.ovpn/", timeout=10000)

        # Verify patch button is DISABLED without external address
        patch_button = await page.query_selector('[data-testid="openvpn-patch-button"]')
        is_disabled = await patch_button.get_attribute("disabled")
        assert is_disabled is not None, "Patch button should be disabled without external address"

        # Fill external address with port
        await fill_textfield_by_testid(page, "openvpn-external-address-input", "myserver.com:4443")
        await asyncio.sleep(0.5)

        # Verify error card disappears
        error_card = await page.query_selector('[data-testid="openvpn-external-ip-error"]')
        assert error_card is None, "Error card should disappear after filling external address"

        # Verify patch button is now enabled
        patch_button = await page.query_selector('[data-testid="openvpn-patch-button"]')
        is_disabled = await patch_button.get_attribute("disabled")
        assert is_disabled is None, "Patch button should be enabled after filling external address"

        # Patch and verify the external address is used (with port parsing)
        await patch_button.click()
        await page.wait_for_selector('[data-testid="openvpn-preview"]', timeout=15000)

        preview = await page.query_selector('[data-testid="openvpn-preview"]')
        preview_content = await preview.input_value()
        assert (
            "remote myserver.com 4443" in preview_content
        ), "Patched config should use external address with parsed port"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ovpn_download_filename(browser, unique_name, unique_port, api_session):
    """E2E test: Download filename can be customized.

    Verifies:
    1. Download filename field exists after patching
    2. Default filename is {instanceName}_patched.ovpn
    3. Filename field is editable
    """
    instance_name = unique_name("ovpn-fname")
    port = unique_port(3600)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create Squid instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings and open patcher dialog
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', timeout=30000
        )
        await navigate_to_settings(page, instance_name)
        await page.wait_for_selector(
            '[data-testid="test-connectivity-openvpn-button"]', timeout=10000
        )
        await page.click('[data-testid="test-connectivity-openvpn-button"]')
        await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

        # Upload and patch
        ovpn_file_path = FIXTURES_DIR / "basic_client.ovpn"
        file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(str(ovpn_file_path))
        await page.wait_for_selector("text=/basic_client.ovpn/", timeout=10000)
        await page.click('[data-testid="openvpn-patch-button"]')
        await page.wait_for_selector('[data-testid="openvpn-preview"]', timeout=15000)

        # Verify filename input exists with default value
        filename_input = page.locator('[data-testid="openvpn-download-filename"] input')
        await filename_input.wait_for(state="visible", timeout=5000)
        default_value = await filename_input.input_value()
        assert (
            default_value == f"{instance_name}_patched.ovpn"
        ), f"Default filename should be '{instance_name}_patched.ovpn', got '{default_value}'"

        # Verify filename is editable
        await filename_input.fill("my_custom_config.ovpn")
        await asyncio.sleep(0.3)
        new_value = await filename_input.input_value()
        assert new_value == "my_custom_config.ovpn", "Filename should be editable"

    finally:
        await page.close()
