"""E2E tests for OpenVPN config patcher feature.

Tests the full user flow:
1. Create Squid instance
2. Navigate to OpenVPN tab
3. Upload .ovpn file
4. Patch config
5. Download patched config
"""

import asyncio
import os
from pathlib import Path

import pytest

from tests.e2e.utils import (
    create_instance_via_ui,
    navigate_to_dashboard,
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
    """E2E test: Upload and patch .ovpn file for Squid instance.

    User Flow:
    1. Create Squid instance
    2. Navigate to instance settings
    3. Click OpenVPN tab
    4. Upload .ovpn file
    5. Click patch button
    6. Verify patched content preview appears
    7. Verify download button enabled
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

        # Step 3: Click OpenVPN tab
        await page.wait_for_selector('[data-testid="tab-openvpn"]', timeout=10000)
        await page.click('[data-testid="tab-openvpn"]')

        # Wait for tab content to load
        await asyncio.sleep(1)

        # Verify file input is visible
        await page.wait_for_selector('[data-testid="openvpn-file-input"]', timeout=10000)

        # Step 4: Upload .ovpn file
        ovpn_file_path = FIXTURES_DIR / "basic_client.ovpn"
        assert ovpn_file_path.exists(), f"Test fixture not found: {ovpn_file_path}"

        file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(str(ovpn_file_path))

        # Wait for file name to appear
        await page.wait_for_selector('text=/Selected: basic_client.ovpn/', timeout=10000)

        # Step 5: Click patch button
        patch_button = await page.query_selector('[data-testid="openvpn-patch-button"]')
        assert patch_button, "Patch button not found"

        # Verify button is enabled
        is_disabled = await patch_button.get_attribute("disabled")
        assert is_disabled is None, "Patch button should be enabled after file upload"

        await patch_button.click()

        # Step 6: Wait for patched content preview to appear
        await page.wait_for_selector('[data-testid="openvpn-preview"]', timeout=15000)

        # Verify preview contains http-proxy directive
        preview = await page.query_selector('[data-testid="openvpn-preview"]')
        preview_content = await preview.input_value()
        assert "http-proxy" in preview_content, "Patched content should contain http-proxy directive"
        assert "localhost" in preview_content or "192.168" in preview_content, \
            "Patched content should contain proxy host"
        assert str(port) in preview_content, f"Patched content should contain port {port}"

        # Verify original content is preserved
        assert "client" in preview_content, "Original 'client' directive should be preserved"
        assert "dev tun" in preview_content, "Original 'dev tun' directive should be preserved"

        # Step 7: Verify download button is enabled
        download_button = await page.query_selector('[data-testid="openvpn-download"]')
        assert download_button, "Download button should appear after successful patch"

        is_disabled = await download_button.get_attribute("disabled")
        assert is_disabled is None, "Download button should be enabled"

        # Verify copy button is also enabled
        copy_button = await page.query_selector('[data-testid="openvpn-copy"]')
        assert copy_button, "Copy button should appear after successful patch"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_and_patch_ovpn_tls_tunnel(browser, unique_name, unique_port, api_session):
    """E2E test: Upload and patch .ovpn file for TLS Tunnel instance.

    User Flow:
    1. Create TLS Tunnel instance
    2. Navigate to instance settings
    3. Click OpenVPN tab
    4. Upload .ovpn file with remote directive
    5. Click patch button
    6. Verify patched content has tunnel endpoint
    7. Verify instance forward_address updated
    """
    instance_name = unique_name("ovpn-tls")
    port = unique_port(4500)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create TLS Tunnel instance
        await page.wait_for_selector('[data-testid="instance-create-button"]', timeout=30000)
        await page.click('[data-testid="instance-create-button"]')

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

        # Step 3: Click OpenVPN tab
        await page.wait_for_selector('[data-testid="tab-openvpn"]', timeout=10000)
        await page.click('[data-testid="tab-openvpn"]')
        await asyncio.sleep(1)

        # Step 4: Upload .ovpn file with remote directive
        ovpn_file_path = FIXTURES_DIR / "tls_tunnel_config.ovpn"
        assert ovpn_file_path.exists(), f"Test fixture not found: {ovpn_file_path}"

        file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(str(ovpn_file_path))

        await page.wait_for_selector('text=/Selected: tls_tunnel_config.ovpn/', timeout=10000)

        # Step 5: Click patch button
        patch_button = await page.query_selector('[data-testid="openvpn-patch-button"]')
        await patch_button.click()

        # Step 6: Wait for patched content
        await page.wait_for_selector('[data-testid="openvpn-preview"]', timeout=15000)

        preview = await page.query_selector('[data-testid="openvpn-preview"]')
        preview_content = await preview.input_value()

        # Verify remote directive was replaced with tunnel endpoint
        assert "remote localhost" in preview_content or "remote 127.0.0.1" in preview_content, \
            "Patched content should have tunnel endpoint as remote"
        assert str(port) in preview_content, f"Patched content should contain tunnel port {port}"

        # Original VPN server should NOT be in the patched config
        assert "vpn-server.example.org" not in preview_content, \
            "Original VPN server should be replaced"

        # Step 7: Verify instance forward_address updated via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            assert resp.status == 200
            data = await resp.json()
            instances = data.get("instances", [])
            tls_instance = next((i for i in instances if i["name"] == instance_name), None)
            assert tls_instance, f"Instance {instance_name} not found in API response"

            # Verify forward_address extracted from .ovpn
            forward_address = tls_instance.get("forward_address")
            assert forward_address == "vpn-server.example.org:443", \
                f"Expected forward_address to be 'vpn-server.example.org:443', got '{forward_address}'"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ovpn_with_auth_credentials(browser, unique_name, unique_port, api_session):
    """E2E test: Patch .ovpn with authentication credentials.

    User Flow:
    1. Create Squid instance with user
    2. Navigate to OpenVPN tab
    3. Upload .ovpn file
    4. Enable auth checkbox
    5. Enter username/password
    6. Patch config
    7. Verify auth block in patched content
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
            json={"username": "testuser", "password": "testpass"}
        ) as resp:
            assert resp.status == 200, "Failed to add user"

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 2: Navigate to OpenVPN tab
        await page.goto(ADDON_URL)
        await page.wait_for_selector(f'[data-testid="instance-card-{instance_name}"]', timeout=30000)
        await navigate_to_settings(page, instance_name)
        await page.click('[data-testid="tab-openvpn"]')
        await asyncio.sleep(1)

        # Step 3: Upload file
        ovpn_file_path = FIXTURES_DIR / "basic_client.ovpn"
        file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
        await file_input.set_input_files(str(ovpn_file_path))
        await page.wait_for_selector('text=/Selected: basic_client.ovpn/', timeout=10000)

        # Step 4: Enable auth checkbox
        auth_checkbox = await page.query_selector('[data-testid="openvpn-auth-checkbox"]')
        assert auth_checkbox, "Auth checkbox should be visible for Squid instances"
        await auth_checkbox.click()

        # Step 5: Enter credentials
        await page.wait_for_selector('[data-testid="openvpn-username-input"]', timeout=5000)
        await page.fill('[data-testid="openvpn-username-input"] input', 'testuser')
        await page.fill('[data-testid="openvpn-password-input"] input', 'testpass')

        # Step 6: Patch config
        await page.click('[data-testid="openvpn-patch-button"]')
        await page.wait_for_selector('[data-testid="openvpn-preview"]', timeout=15000)

        # Step 7: Verify auth block in patched content
        preview = await page.query_selector('[data-testid="openvpn-preview"]')
        preview_content = await preview.input_value()

        assert "<http-proxy-user-pass>" in preview_content, \
            "Patched content should contain auth block start"
        assert "</http-proxy-user-pass>" in preview_content, \
            "Patched content should contain auth block end"
        assert "testuser" in preview_content, "Patched content should contain username"
        assert "testpass" in preview_content, "Patched content should contain password"

    finally:
        await page.close()
