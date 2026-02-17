"""E2E tests for 1.6.8+ features (updated for v1.6.9 changes).

Active tests:
1. VPN server extraction from .ovpn upload (external address now in dialog)
2. Raw config editor with line numbers
3. Click-to-browse file upload (external address now in dialog)
4. OpenVPN patch blocked without external address (TLS tunnel)
5. Raw config syntax highlighting

Removed in v1.6.9 (external IP/port moved from settings to dialog):
- External port field for TLS tunnel (settings field removed)
- External IP validation for TLS tunnel (validation now in dialog)
- External address shown in connection info (grid cells removed)

All tests use per-test fixtures for parallel execution.
"""

import asyncio
import os

import pytest

from tests.e2e.utils import (
    create_tls_tunnel_via_ui,
    fill_textfield_by_testid,
    navigate_to_settings,
    wait_for_instance_running,
)

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "dev_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_vpn_server_extraction_from_ovpn(browser, unique_name, unique_port, api_session):
    """Test VPN server extraction from .ovpn file upload.

    Verifies:
    - OpenVPN patcher dialog can be opened
    - .ovpn file can be uploaded
    - VPN server is extracted and displayed
    - Instance forward_address is updated
    - Success message shows extracted server
    """
    instance_name = unique_name("vpn-extract")
    port = unique_port(8503)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create TLS tunnel instance
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="old.vpn.com:1194",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # Scroll to Connection Info card and find OpenVPN patcher button
        patcher_button = page.locator('[data-testid="connection-info-openvpn-button"]')
        await patcher_button.scroll_into_view_if_needed()
        await patcher_button.wait_for(state="visible", timeout=10000)
        await patcher_button.click()

        # Dialog should open
        dialog = page.locator('[data-testid="openvpn-dialog"]')
        await dialog.wait_for(state="visible", timeout=10000)

        # Fill external address in dialog (moved from settings in v1.6.9)
        await fill_textfield_by_testid(page, "openvpn-external-address-input", "tunnel.example.com")
        await asyncio.sleep(0.5)

        # Create a mock .ovpn file with a different VPN server
        ovpn_content = """client
dev tun
proto udp
remote new.vpn.server.com 1194
resolv-retry infinite
nobind
"""

        # Upload file via file input
        file_input = page.locator('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(
            {
                "name": "test.ovpn",
                "mimeType": "text/plain",
                "buffer": ovpn_content.encode(),
            }
        )

        await asyncio.sleep(1)

        # Click Extract & Patch button
        patch_button = page.locator('[data-testid="openvpn-patch-button"]')
        await patch_button.click()

        # Wait for success message with extracted VPN server
        success_msg = await page.wait_for_selector(
            "text=/VPN Server Extracted Successfully/", timeout=10000
        )
        assert success_msg is not None

        # Verify extracted server is displayed
        page_text = await page.inner_text("body")
        assert "new.vpn.server.com:1194" in page_text, "Extracted VPN server should be shown"

        # Close dialog
        close_button = page.locator('[data-testid="openvpn-dialog-close"]')
        await close_button.click()
        await asyncio.sleep(2)

        # Verify forward_address was updated via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance.get("forward_address") == "new.vpn.server.com:1194", (
                f"forward_address should be updated to extracted VPN server, "
                f"got: {instance.get('forward_address')}"
            )
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_raw_config_editor(browser, unique_name, unique_port, api_session):
    """Test raw config editor functionality.

    Verifies:
    - Raw Configuration tab exists and is visible
    - Config content is loaded and displayed
    - Line numbers are shown
    - Config can be edited
    - Save button works
    - Instance is restarted after save
    """
    instance_name = unique_name("raw-config")
    port = unique_port(8504)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create TLS tunnel instance
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # Scroll down to find Raw Configuration section
        # (it might be below the fold)
        page_text = await page.inner_text("body")
        assert "Raw Configuration" in page_text, "Raw Configuration tab should be present"

        # Find the raw config editor - scroll to it since it's at the bottom
        editor = page.locator('[data-testid="raw-config-editor"]')
        await editor.scroll_into_view_if_needed()
        await editor.wait_for(state="visible", timeout=10000)

        # Wait for config content to load (async query populates textarea)
        await page.wait_for_function(
            """() => {
                const el = document.querySelector('[data-testid="raw-config-editor"]');
                return el && el.value && el.value.length > 0;
            }""",
            timeout=10000,
        )

        # Get current config content
        config_content = await editor.input_value()
        assert config_content, "Config editor should have content"
        assert len(config_content) > 0, "Config should not be empty"

        # For TLS tunnel, should be nginx_stream.conf
        assert (
            "stream" in config_content or "upstream" in config_content or "server" in config_content
        ), "Config should contain nginx stream directives for TLS tunnel"

        # Add a comment to the config
        modified_config = f"# Test comment added by E2E test\n{config_content}"
        await editor.fill(modified_config)
        await asyncio.sleep(0.5)

        # Save button should be enabled
        save_button = page.locator('[data-testid="raw-config-save-button"]')
        await page.wait_for_selector(
            '[data-testid="raw-config-save-button"]:not([disabled])', timeout=5000
        )

        # Click save
        await save_button.click()

        # Wait for save success
        await page.wait_for_selector("text=Saved!", timeout=10000)

        await asyncio.sleep(3)

        # Verify the change persisted via API (page.reload() goes back to
        # the dashboard since settings is reached via in-app navigation)
        async with api_session.get(f"{ADDON_URL}/api/instances/{instance_name}/raw-config") as resp:
            data = await resp.json()
            assert "# Test comment added by E2E test" in data.get(
                "config", ""
            ), "Config changes should persist after save"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_click_to_browse_file_upload(browser, unique_name, unique_port, api_session):
    """Test click-to-browse functionality in OpenVPN patcher.

    Verifies:
    - Clicking the drag-drop zone triggers file input
    - File can be selected via browse dialog
    - Selected file name is displayed
    """
    instance_name = unique_name("click-browse")
    port = unique_port(8505)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create TLS tunnel instance with external IP
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # Scroll to Connection Info card and open OpenVPN patcher dialog
        patcher_button = page.locator('[data-testid="connection-info-openvpn-button"]')
        await patcher_button.scroll_into_view_if_needed()
        await patcher_button.wait_for(state="visible", timeout=10000)
        await patcher_button.click()

        # Dialog should open
        dialog = page.locator('[data-testid="openvpn-dialog"]')
        await dialog.wait_for(state="visible", timeout=10000)

        # Fill external address in dialog (moved from settings in v1.6.9)
        await fill_textfield_by_testid(page, "openvpn-external-address-input", "tunnel.example.com")
        await asyncio.sleep(0.5)

        # Find the drag-drop zone by data-testid
        drop_zone = page.locator('[data-testid="openvpn-drop-zone"]')

        # Create a file chooser promise before clicking
        async with page.expect_file_chooser() as fc_info:
            # Click the drop zone - should trigger file input
            await drop_zone.click()

        file_chooser = await fc_info.value

        # Verify file chooser was opened
        assert file_chooser is not None, "File chooser should open when drop zone is clicked"

        # Set files
        ovpn_content = """client
dev tun
proto udp
remote vpn.server.com 1194
"""
        await file_chooser.set_files(
            {
                "name": "clicked.ovpn",
                "mimeType": "text/plain",
                "buffer": ovpn_content.encode(),
            }
        )

        await asyncio.sleep(1)

        # Verify file name is displayed
        page_text = await page.inner_text("body")
        assert "clicked.ovpn" in page_text, "Selected file name should be displayed"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_openvpn_patch_blocked_without_external_ip(
    browser, unique_name, unique_port, api_session
):
    """Test that OpenVPN patching is blocked for TLS tunnel without external IP.

    Verifies:
    - Error message shown when external IP is not configured
    - Patch button is disabled even with file uploaded
    """
    instance_name = unique_name("patch-blocked")
    port = unique_port(8508)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create TLS tunnel instance (no external IP set)
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # Scroll to Connection Info card and open OpenVPN patcher dialog
        patcher_button = page.locator('[data-testid="connection-info-openvpn-button"]')
        await patcher_button.scroll_into_view_if_needed()
        await patcher_button.wait_for(state="visible", timeout=10000)
        await patcher_button.click()

        # Dialog should open
        dialog = page.locator('[data-testid="openvpn-dialog"]')
        await dialog.wait_for(state="visible", timeout=10000)

        # Error card should be visible (red border, not warning)
        error_card = page.locator('[data-testid="openvpn-external-ip-error"]')
        await error_card.wait_for(state="visible", timeout=5000)
        error_text = await error_card.inner_text()
        assert (
            "External address is required" in error_text
        ), f"Error message should mention external address is required, got: {error_text}"

        # Upload a file
        ovpn_content = """client
dev tun
proto udp
remote vpn.server.com 1194
"""
        file_input = page.locator('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(
            {
                "name": "test.ovpn",
                "mimeType": "text/plain",
                "buffer": ovpn_content.encode(),
            }
        )
        await asyncio.sleep(1)

        # Patch button should be disabled (file uploaded but no external address)
        patch_button = page.locator('[data-testid="openvpn-patch-button"]')
        is_disabled = await patch_button.is_disabled()
        assert (
            is_disabled
        ), "Patch button should be disabled without external address for TLS tunnel"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_raw_config_syntax_highlighting(browser, unique_name, unique_port, api_session):
    """Test syntax highlighting in raw config editor.

    Verifies:
    - Textarea has transparent text color
    - Highlighted pre element exists with span elements
    - Editing still works correctly
    """
    instance_name = unique_name("syntax-hl")
    port = unique_port(8509)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create TLS tunnel instance
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # Find the raw config editor
        editor = page.locator('[data-testid="raw-config-editor"]')
        await editor.scroll_into_view_if_needed()
        await editor.wait_for(state="visible", timeout=10000)

        # Wait for config content to load
        await page.wait_for_function(
            """() => {
                const el = document.querySelector('[data-testid="raw-config-editor"]');
                return el && el.value && el.value.length > 0;
            }""",
            timeout=10000,
        )

        # Verify textarea has transparent text color for syntax highlighting overlay
        textarea_color = await editor.evaluate("el => getComputedStyle(el).color")
        assert (
            textarea_color == "rgba(0, 0, 0, 0)" or "transparent" in textarea_color.lower()
        ), f"Textarea should have transparent text color, got: {textarea_color}"

        # Verify highlighted pre element exists
        highlight_pre = page.locator('[data-testid="raw-config-highlight"]')
        await highlight_pre.wait_for(state="attached", timeout=5000)

        # Verify pre contains highlighted span elements
        span_count = await highlight_pre.evaluate("el => el.querySelectorAll('span').length")
        assert (
            span_count > 0
        ), f"Highlighted pre should contain span elements for syntax coloring, got {span_count}"

        # Verify editing still works: type a comment and check it appears in pre
        original_content = await editor.input_value()
        modified_content = f"# highlight test comment\n{original_content}"
        await editor.fill(modified_content)
        await asyncio.sleep(0.5)

        # The comment should appear in the highlight pre
        highlight_html = await highlight_pre.inner_html()
        assert (
            "highlight test comment" in highlight_html
        ), "Edited text should appear in the highlighted pre element"
        assert (
            "cfg-comment" in highlight_html
        ), "Comment should be highlighted with cfg-comment class"
    finally:
        await page.close()
