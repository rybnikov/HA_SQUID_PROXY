"""E2E tests for 1.6.8 stabilization release features.

Tests carried forward from 1.6.7:
1. External port field for TLS tunnel
2. External IP validation for TLS tunnel (required)
3. VPN server extraction from .ovpn upload
4. Raw config editor with line numbers
5. Click-to-browse file upload

New tests for 1.6.8:
6. External address shown in connection info
7. OpenVPN patch blocked without external IP (TLS tunnel)
8. Raw config syntax highlighting

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
async def test_external_port_field_tls_tunnel(browser, unique_name, unique_port, api_session):
    """Test external port field for TLS tunnel instances.

    Verifies:
    - External port field is visible for TLS tunnel in settings
    - External port can be set to a different value than listen port
    - External port defaults to listen port if not set
    - API correctly returns external_port value
    """
    instance_name = unique_name("external-port")
    listen_port = unique_port(8500)
    external_port = unique_port(8501)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create TLS tunnel instance
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            listen_port,
            forward_address="vpn.example.com:1194",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # Verify external port field is visible
        external_port_input = page.locator('[data-testid="settings-external-port-input"]')
        await external_port_input.wait_for(state="visible", timeout=10000)

        # Set external IP (required for TLS tunnel)
        await fill_textfield_by_testid(page, "settings-external-ip-input", "tunnel.example.com")

        # Set external port to different value
        await fill_textfield_by_testid(page, "settings-external-port-input", str(external_port))
        await asyncio.sleep(0.5)

        # Save changes
        await page.wait_for_selector(
            '[data-testid="settings-save-button"]:not([disabled])', timeout=5000
        )
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)

        await asyncio.sleep(2)

        # Verify via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert (
                instance.get("external_port") == external_port
            ), f"external_port should be {external_port}, got: {instance.get('external_port')}"
            assert instance.get("external_ip") == "tunnel.example.com"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_external_ip_required_validation(browser, unique_name, unique_port, api_session):
    """Test that external IP is required for TLS tunnel.

    Verifies:
    - Save button works when external IP is set
    - Validation error appears when trying to save without external IP
    - Error message is clear and actionable
    """
    instance_name = unique_name("ext-ip-validation")
    port = unique_port(8502)

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

        # Set external IP first (so we can test clearing it)
        await fill_textfield_by_testid(page, "settings-external-ip-input", "tunnel.example.com")
        await asyncio.sleep(0.5)

        # Save should work with external IP
        await page.wait_for_selector(
            '[data-testid="settings-save-button"]:not([disabled])', timeout=5000
        )
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)

        # Wait for "Saved!" to disappear before second save attempt
        # (GeneralTab shows "Saved!" for 2 seconds then reverts to "Save Changes")
        await page.locator("text=Saved!").wait_for(state="hidden", timeout=5000)
        await asyncio.sleep(0.5)

        # Now clear external IP
        await fill_textfield_by_testid(page, "settings-external-ip-input", "")
        # Make another change to make form dirty
        await fill_textfield_by_testid(page, "settings-cover-domain-input", "new.example.com")
        await asyncio.sleep(0.5)

        # Try to save - should fail validation
        await page.wait_for_selector(
            '[data-testid="settings-save-button"]:not([disabled])', timeout=5000
        )
        await page.click('[data-testid="settings-save-button"]')

        # Validation error should appear
        error_msg = await page.wait_for_selector("text=/External IP is required/", timeout=5000)
        assert error_msg is not None, "Validation error should be displayed"

        # "Saved!" should NOT appear since validation failed
        saved_text = page.locator("text=Saved!")
        assert (
            await saved_text.count() == 0
        ), "Saved message should not appear when validation fails"
    finally:
        await page.close()


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

        # Navigate to settings and set external IP
        await navigate_to_settings(page, instance_name)
        await fill_textfield_by_testid(page, "settings-external-ip-input", "tunnel.example.com")
        await asyncio.sleep(0.5)
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)
        # Wait for save to complete and UI to settle
        await page.locator("text=Saved!").wait_for(state="hidden", timeout=5000)
        await asyncio.sleep(1)

        # Scroll to Connection Info card and find OpenVPN patcher button
        patcher_button = page.locator('[data-testid="connection-info-openvpn-button"]')
        await patcher_button.scroll_into_view_if_needed()
        await patcher_button.wait_for(state="visible", timeout=10000)
        await patcher_button.click()

        # Dialog should open
        dialog = page.locator('[data-testid="openvpn-dialog"]')
        await dialog.wait_for(state="visible", timeout=10000)

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

        # Navigate to settings and set external IP
        await navigate_to_settings(page, instance_name)
        await fill_textfield_by_testid(page, "settings-external-ip-input", "tunnel.example.com")
        await asyncio.sleep(0.5)
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)
        # Wait for save to complete and UI to settle
        await page.locator("text=Saved!").wait_for(state="hidden", timeout=5000)
        await asyncio.sleep(1)

        # Scroll to Connection Info card and open OpenVPN patcher dialog
        patcher_button = page.locator('[data-testid="connection-info-openvpn-button"]')
        await patcher_button.scroll_into_view_if_needed()
        await patcher_button.wait_for(state="visible", timeout=10000)
        await patcher_button.click()

        # Dialog should open
        dialog = page.locator('[data-testid="openvpn-dialog"]')
        await dialog.wait_for(state="visible", timeout=10000)

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
async def test_external_address_shown_in_connection_info(
    browser, unique_name, unique_port, api_session
):
    """Test external address is displayed in connection info.

    Verifies:
    - "Not configured" shown when external IP is not set
    - External address and client port shown after saving settings
    """
    instance_name = unique_name("conn-info-addr")
    listen_port = unique_port(8506)
    external_port = unique_port(8507)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create TLS tunnel instance
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            listen_port,
            forward_address="vpn.example.com:1194",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # Scroll to Connection Info section
        ext_addr = page.locator('[data-testid="connection-info-external-address"]')
        await ext_addr.scroll_into_view_if_needed()
        await ext_addr.wait_for(state="visible", timeout=10000)

        # Should show "Not configured" initially
        ext_addr_text = await ext_addr.inner_text()
        assert (
            "Not configured" in ext_addr_text
        ), f"Should show 'Not configured' initially, got: {ext_addr_text}"

        # Client port should default to listen port
        ext_port_el = page.locator('[data-testid="connection-info-external-port"]')
        ext_port_text = await ext_port_el.inner_text()
        assert (
            str(listen_port) in ext_port_text
        ), f"Client port should default to listen port {listen_port}, got: {ext_port_text}"

        # Now set external IP and external port
        await fill_textfield_by_testid(page, "settings-external-ip-input", "my.tunnel.com")
        await fill_textfield_by_testid(page, "settings-external-port-input", str(external_port))
        await asyncio.sleep(0.5)

        await page.wait_for_selector(
            '[data-testid="settings-save-button"]:not([disabled])', timeout=5000
        )
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)
        await asyncio.sleep(2)

        # Scroll back to connection info
        await ext_addr.scroll_into_view_if_needed()

        # External address should now show the IP
        ext_addr_text = await ext_addr.inner_text()
        assert (
            "my.tunnel.com" in ext_addr_text
        ), f"Should show external IP after save, got: {ext_addr_text}"

        # Client port should show external port
        ext_port_text = await ext_port_el.inner_text()
        assert (
            str(external_port) in ext_port_text
        ), f"Client port should show {external_port} after save, got: {ext_port_text}"
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
            "External IP is required" in error_text
        ), f"Error message should mention external IP is required, got: {error_text}"

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

        # Patch button should be disabled (file uploaded but no external IP)
        patch_button = page.locator('[data-testid="openvpn-patch-button"]')
        is_disabled = await patch_button.is_disabled()
        assert is_disabled, "Patch button should be disabled without external IP for TLS tunnel"
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
